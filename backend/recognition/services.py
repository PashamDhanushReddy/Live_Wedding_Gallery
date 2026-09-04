import os
import requests
import tempfile
import numpy as np
from deepface import DeepFace
from guests.models import Guest, PhotoFace
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)

class FaceRecognitionService:
    @staticmethod
    def get_embedding(image_path):
        try:
            objs = DeepFace.represent(img_path=image_path, model_name="Facenet", enforce_detection=True)
            if objs:
                return objs[0]["embedding"]
        except Exception as e:
            logger.error(f"Error extracting embedding: {e}")
        return None

    @staticmethod
    def get_all_embeddings(image_path):
        try:
            objs = DeepFace.represent(img_path=image_path, model_name="Facenet", enforce_detection=False)
            return [obj["embedding"] for obj in objs]
        except Exception as e:
            logger.error(f"Error extracting embeddings: {e}")
        return []

    @staticmethod
    def cosine_similarity(a, b):
        a = np.array(a)
        b = np.array(b)
        # Avoid division by zero
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    @staticmethod
    def process_photo(photo):
        # 1. Download image to temporary file
        url = photo.display_url or photo.cloudinary_url
        if not url:
            return
            
        try:
            response = requests.get(url, stream=True, timeout=30)
            if response.status_code == 200:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                    for chunk in response.iter_content(1024):
                        tmp_file.write(chunk)
                    tmp_path = tmp_file.name
            else:
                logger.error(f"Could not download photo {photo.id}")
                return
        except Exception as e:
            logger.error(f"Error downloading photo {photo.id}: {e}")
            return

        # 2. Extract faces
        try:
            embeddings = FaceRecognitionService.get_all_embeddings(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        if not embeddings:
            return

        # 3. Match against registered guests
        threshold = float(getattr(settings, 'FACE_MATCH_THRESHOLD', 0.55))
        guests = Guest.objects.filter(wedding=photo.wedding)
        
        matches_found = []
        channel_layer = get_channel_layer()
        
        for guest in guests:
            if not guest.face_embedding:
                continue
            
            best_similarity = 0.0
            for emb in embeddings:
                sim = FaceRecognitionService.cosine_similarity(guest.face_embedding, emb)
                if sim > best_similarity:
                    best_similarity = sim
                    
            if best_similarity >= threshold:
                pf, created = PhotoFace.objects.get_or_create(
                    photo=photo,
                    guest=guest,
                    defaults={'confidence': best_similarity}
                )
                if created:
                    # Notify specific guest session via WebSockets
                    async_to_sync(channel_layer.group_send)(
                        f"guest_{guest.session_id}",
                        {
                            "type": "photo_message",
                            "event_type": "photo.matched",
                            "photo": {
                                "id": photo.id,
                                "url": photo.thumbnail_url,
                                "display_url": photo.display_url,
                                "confidence": best_similarity
                            }
                        }
                    )
