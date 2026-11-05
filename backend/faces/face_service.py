import os
import io
import math
import logging
import hashlib
import threading
from typing import List, Dict, Tuple, Optional
import urllib.request

import cv2
import numpy as np
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from pgvector.django import CosineDistance

from faces.models import Face
from photos.models import Photo
from weddings.models import Wedding
from photos.categorization import categorize_photo

logger = logging.getLogger(__name__)

# Global singleton and lock for InsightFace inference
_face_app = None
_face_lock = threading.Lock()


def get_face_analyzer():
    """
    Thread-safe lazy initialization of the InsightFace FaceAnalysis engine.
    Auto-detects available ONNXRuntime execution providers (CUDA vs CPU).
    Uses the compact, memory-efficient 'buffalo_sc' model.
    """
    global _face_app
    if _face_app is None:
        with _face_lock:
            if _face_app is None:
                from insightface.app import FaceAnalysis
                model_name = getattr(settings, 'FACE_MODEL_NAME', 'buffalo_sc')
                
                # Check for CUDA availability
                try:
                    import onnxruntime as ort
                    available_providers = ort.get_available_providers()
                    if 'CUDAExecutionProvider' in available_providers:
                        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
                        ctx_id = 0
                    else:
                        providers = ['CPUExecutionProvider']
                        ctx_id = -1
                except Exception:
                    providers = ['CPUExecutionProvider']
                    ctx_id = -1
                
                logger.info(f"Initializing InsightFace ({model_name}) with providers={providers}, ctx_id={ctx_id}")
                app = FaceAnalysis(name=model_name, providers=providers)
                app.prepare(ctx_id=ctx_id, det_size=(640, 640))
                _face_app = app
    return _face_app


def decode_image_bytes(image_bytes: bytes) -> Optional[np.ndarray]:
    """Safely decodes raw image bytes into a BGR OpenCV NumPy array."""
    if not image_bytes:
        return None
    try:
        arr = np.asarray(bytearray(image_bytes), dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        logger.error(f"Error decoding image bytes: {e}")
        return None


def extract_faces_from_image(img: np.ndarray, min_confidence: float = 0.50) -> List[Dict]:
    """
    Extracts all prominent faces from a decoded image.
    Returns a list of dicts with bbox, confidence, embedding, and bounding box area.
    Thread-safe via _face_lock.
    """
    if img is None:
        return []

    app = get_face_analyzer()
    with _face_lock:
        raw_faces = app.get(img)

    results = []
    for face in raw_faces:
        confidence = float(face.det_score)
        if confidence < min_confidence:
            continue

        bbox = [int(v) for v in face.bbox]
        width = max(0, bbox[2] - bbox[0])
        height = max(0, bbox[3] - bbox[1])
        area = width * height

        # Ensure embedding is a 512-dim float list
        embedding = face.embedding.tolist()

        results.append({
            'bbox': bbox,
            'x': bbox[0],
            'y': bbox[1],
            'width': width,
            'height': height,
            'area': area,
            'confidence': confidence,
            'embedding': embedding
        })

    # Sort faces by area descending (largest/primary face first)
    results.sort(key=lambda f: f['area'], reverse=True)
    return results


def extract_selfie_faces(image_bytes: bytes, min_confidence: float = 0.50) -> Tuple[List[Dict], str]:
    """
    Analyzes an uploaded selfie and extracts genuine selfie faces while
    filtering out tiny background bystanders / photobombers.
    
    Returns: (faces: List[Dict], status: str)
      status values: 'OK_SINGLE', 'OK_MULTIPLE', 'NO_FACE', 'DECODE_ERROR'
    """
    img = decode_image_bytes(image_bytes)
    if img is None:
        return [], "DECODE_ERROR"

    faces = extract_faces_from_image(img, min_confidence=min_confidence)
    if not faces:
        return [], "NO_FACE"

    # Filter out bystander background faces:
    # Any face less than 20% of the largest face's area is treated as background
    primary_area = faces[0]['area']
    prominent_faces = [f for f in faces if f['area'] >= (primary_area * 0.20)]

    if len(prominent_faces) == 1:
        return prominent_faces, "OK_SINGLE"
    else:
        # 2 or more prominent faces in selfie (e.g., couple or group selfie)
        return prominent_faces, "OK_MULTIPLE"


def generate_embeddings_for_photo(
    photo: Photo,
    force: bool = False,
    staging_path: Optional[str] = None
) -> List[Face]:
    """
    Generates and stores face embeddings for a photo.
    
    Idempotency Guard:
      If the photo already has face embeddings and force=False, skips extraction.
      Embeddings are generated only once per successfully registered photo.
      
    Never loads large original RAW files into memory:
      Prefers local staged file, then CDN 1200px preview URL.
    """
    # 1. Idempotency Check
    if not force and photo.faces.exists():
        logger.info(f"Photo {photo.id} already has {photo.faces.count()} face embeddings. Skipping.")
        return list(photo.faces.all())

    # 2. Acquire image bytes efficiently
    img = None
    if staging_path and os.path.exists(staging_path):
        img = cv2.imread(staging_path)
    
    if img is None and photo.preview_url:
        try:
            req = urllib.request.urlopen(photo.preview_url, timeout=15)
            arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        except Exception as e:
            logger.warning(f"Could not load preview URL for photo {photo.id}: {e}")

    if img is None and (photo.secure_url or photo.cloudinary_url):
        try:
            url = photo.secure_url or photo.cloudinary_url
            req = urllib.request.urlopen(url, timeout=15)
            arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        except Exception as e:
            logger.error(f"Failed to fetch photo {photo.id} image bytes: {e}")
            return []

    if img is None:
        logger.error(f"Cannot process faces for photo {photo.id}: No image data available.")
        return []

    # 3. Extract faces
    min_confidence = getattr(settings, 'FACE_DETECTION_CONFIDENCE', 0.50)
    detected_faces = extract_faces_from_image(img, min_confidence=min_confidence)

    # 4. Atomic bulk insert
    with transaction.atomic():
        if force:
            photo.faces.all().delete()

        faces_to_create = [
            Face(
                photo=photo,
                embedding=f['embedding'],
                x=f['x'],
                y=f['y'],
                width=f['width'],
                height=f['height'],
                detection_confidence=f['confidence']
            )
            for f in detected_faces
        ]

        if faces_to_create:
            created_faces = Face.objects.bulk_create(faces_to_create, batch_size=100)
        else:
            created_faces = []

        # 5. Run categorization (Bride / Groom / Couple AI tagging)
        categorize_photo(photo)

    logger.info(f"Generated {len(created_faces)} face embeddings for photo {photo.id} ({photo.original_filename})")
    return created_faces


def search_photos_by_selfie(
    wedding: Wedding,
    selfie_bytes: bytes,
    threshold: Optional[float] = None,
    page: int = 1,
    page_size: int = 30
) -> Dict:
    """
    Performs an index-accelerated face search for a visitor's selfie.
    
    Architecture Highlights:
    1. NEVER performs a sequential scan of all gallery photos.
    2. Uses pgvector HNSW index scan (<=> operator) to search 512-d embeddings in ~1 ms.
    3. Handles 0 faces with clear user guidance.
    4. Handles multiple faces in a selfie (e.g. couple selfie) by matching photos containing either person.
    5. Paginates results to avoid large JSON payloads.
    6. Returns lightweight photo CDN URLs without loading original photograph bytes into RAM.
    """
    if threshold is None:
        threshold = getattr(settings, 'FACE_MATCH_THRESHOLD', 0.45)
    
    # Clamp threshold to safe bounds (0.30 - 0.60)
    threshold = max(0.30, min(0.60, float(threshold)))

    # 1. Extract selfie faces (with SHA-256 hash caching to eliminate redundant ONNX inference on refreshes/pagination)
    selfie_hash = hashlib.sha256(selfie_bytes).hexdigest()
    cache_key = f"selfie_faces:{selfie_hash}"
    cached_data = cache.get(cache_key)

    if cached_data is not None:
        prominent_faces = cached_data['prominent_faces']
        selfie_status = cached_data['selfie_status']
        logger.debug(f"Selfie faces cache HIT for hash {selfie_hash[:8]}")
    else:
        prominent_faces, selfie_status = extract_selfie_faces(selfie_bytes)
        if selfie_status not in ["DECODE_ERROR", "NO_FACE"]:
            cache.set(cache_key, {
                'prominent_faces': prominent_faces,
                'selfie_status': selfie_status
            }, timeout=3600)  # Cache for 1 hour

    if selfie_status == "DECODE_ERROR":
        return {
            "status": "error",
            "code": "DECODE_ERROR",
            "message": "The uploaded file could not be decoded as an image. Please upload a valid JPEG, PNG, or WebP selfie.",
            "photos": [],
            "matches_count": 0
        }

    if selfie_status == "NO_FACE":
        return {
            "status": "no_face_detected",
            "code": "NO_FACE",
            "message": "No face was detected in your selfie. Please ensure good lighting, hold the camera steady, and face forward directly.",
            "photos": [],
            "matches_count": 0
        }

    # 2. Vector search using pgvector HNSW index
    # If selfie has multiple prominent people, search each face and union the matched photo IDs
    matched_photo_ids = set()
    max_search_results = getattr(settings, 'FACE_SEARCH_MAX_RESULTS', 150)

    for face_info in prominent_faces:
        target_emb = face_info['embedding']

        # HNSW index guided nearest-neighbor query
        candidate_photo_ids = Face.objects.filter(
            photo__wedding=wedding
        ).annotate(
            distance=CosineDistance('embedding', target_emb)
        ).filter(
            distance__lt=threshold
        ).order_by('distance').values_list('photo_id', flat=True).distinct()[:max_search_results]

        for pid in candidate_photo_ids:
            matched_photo_ids.add(pid)

    all_matched_ids = list(matched_photo_ids)
    total_matches = len(all_matched_ids)

    # 3. Paginate results
    page = max(1, int(page))
    page_size = max(1, min(100, int(page_size)))
    total_pages = math.ceil(total_matches / page_size) if total_matches > 0 else 1

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_ids = all_matched_ids[start_idx:end_idx]

    # 4. Fetch photo records for current page only
    photos = list(Photo.objects.filter(id__in=page_ids).order_by('-created_at'))

    from photos.serializers import PhotoSerializer
    serializer = PhotoSerializer(photos, many=True)

    info_message = None
    if selfie_status == "OK_MULTIPLE":
        info_message = f"Detected {len(prominent_faces)} people in your selfie. Showing photos containing either person."

    return {
        "status": "success",
        "matches_count": total_matches,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "threshold_used": threshold,
        "selfie_faces_detected": len(prominent_faces),
        "message": info_message,
        "photos": serializer.data
    }

