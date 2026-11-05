import os
import re
import uuid
import time
import logging
import hashlib
import concurrent.futures
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from django.db import transaction, close_old_connections, models
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from PIL import Image
import cv2
import numpy as np

from .models import Photo, IngestionJob, PhoneDevice
from .serializers import PhotoSerializer
from .categorization import categorize_photo
from .cloudinary_service import upload_photo
from .lock_utils import acquire_job_lock, ConcurrencyLockContendedError
from weddings.models import Wedding
from faces.models import Face

logger = logging.getLogger(__name__)

# High-concurrency background worker thread pool for local dev and direct ingestion
_ingestion_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

# Global lock for InsightFace inference
_face_app = None
import threading
_face_lock = threading.Lock()

def get_face_app():
    global _face_app
    if _face_app is None:
        with _face_lock:
            if _face_app is None:
                from insightface.app import FaceAnalysis
                _face_app = FaceAnalysis(name='buffalo_sc')
                _face_app.prepare(ctx_id=0, det_size=(640, 640))
    return _face_app


# Magic byte definitions for image verification
MAGIC_BYTES = {
    'jpeg': b'\xff\xd8\xff',
    'png': b'\x89PNG\r\n\x1a\n',
    'webp': b'RIFF', # Bytes 8-12 must be b'WEBP'
}

def sanitize_filename(filename: str) -> str:
    """Strip directory traversal, null bytes, and non-whitelisted characters."""
    clean = os.path.basename(filename or 'photo.jpg')
    clean = re.sub(r'[^a-zA-Z0-9_.-]', '_', clean)
    if not clean or clean.startswith('.'):
        clean = f"photo_{int(time.time())}.jpg"
    return clean[:200]


def stage_uploaded_file(uploaded_file, job_id: uuid.UUID) -> dict:
    """
    Streams an incoming uploaded file chunk-by-chunk to disk at MEDIA_ROOT/staging.
    Never loads the entire file into RAM.
    Validates magic bytes, file size bounds, checksum, and PIL image integrity.
    """
    staging_dir = Path(settings.MEDIA_ROOT) / 'staging'
    staging_dir.mkdir(parents=True, exist_ok=True)

    safe_name = sanitize_filename(uploaded_file.name)
    staging_filename = f"{job_id}_{safe_name}"
    staging_path = staging_dir / staging_filename

    hasher = hashlib.sha256()
    total_bytes = 0
    first_chunk = True
    detected_mime = 'image/jpeg'

    min_size = 1024 # 1 KB
    max_size = 100 * 1024 * 1024 # 100 MB

    try:
        with open(staging_path, 'wb') as dst:
            for chunk in uploaded_file.chunks(chunk_size=64 * 1024):
                if first_chunk:
                    first_chunk = False
                    # Inspect magic bytes
                    if chunk.startswith(MAGIC_BYTES['jpeg']):
                        detected_mime = 'image/jpeg'
                    elif chunk.startswith(MAGIC_BYTES['png']):
                        detected_mime = 'image/png'
                    elif chunk.startswith(MAGIC_BYTES['webp']) and len(chunk) >= 12 and chunk[8:12] == b'WEBP':
                        detected_mime = 'image/webp'
                    else:
                        raise ValueError(f"Invalid file signature. File '{safe_name}' does not match supported image types (JPEG, PNG, WEBP).")

                hasher.update(chunk)
                total_bytes += len(chunk)

                if total_bytes > max_size:
                    raise ValueError(f"File size exceeds maximum allowed limit of {max_size // (1024 * 1024)} MB.")
                
                dst.write(chunk)

        if total_bytes < min_size:
            raise ValueError(f"File is too small ({total_bytes} bytes). Corrupt or incomplete transfer.")

        # Validate image integrity with PIL verify() (does not decode raster into RAM)
        try:
            with Image.open(staging_path) as img:
                img.verify()
                format_name = (img.format or '').lower()
                if format_name not in ['jpeg', 'png', 'webp', 'mpo']:
                    raise ValueError(f"Unrecognized image format: {format_name}")
        except Exception as e:
            raise ValueError(f"Corrupted or malformed image: {e}")

        checksum = hasher.hexdigest()

        return {
            'staging_path': str(staging_path),
            'checksum': checksum,
            'file_size': total_bytes,
            'mime_type': detected_mime,
            'original_filename': safe_name
        }

    except Exception:
        # Clean up partial staging file if validation fails
        if staging_path.exists():
            try:
                staging_path.unlink()
            except OSError:
                pass
        raise


def process_ingestion_job(job_id: uuid.UUID):
    """
    Idempotent, transactional background processor for IngestionJob with distributed locking.
    Statuses traversed:
      QUEUED -> UPLOADING -> CLOUDINARY_COMPLETED -> DB_REGISTERED -> FACE_PROCESSING -> COMPLETED
    On failure:
      FAILED (retryable) or DEAD_LETTER (attempts >= max_attempts).
    The original staging file is NEVER deleted until COMPLETED is safely committed.
    """
    close_old_connections()
    try:
        job = IngestionJob.objects.select_related('wedding').get(job_id=job_id)
    except IngestionJob.DoesNotExist:
        logger.error(f"IngestionJob {job_id} not found in database.")
        return

    # Check if job was already completed
    if job.status == 'COMPLETED':
        logger.info(f"Job {job_id} is already COMPLETED. Skipping.")
        return

    wedding = job.wedding

    try:
        from observability.context import set_correlation_id, set_upload_id, set_wedding_slug
        set_correlation_id(job.upload_id or str(job.job_id))
        set_upload_id(job.upload_id)
        set_wedding_slug(wedding.slug)
    except ImportError:
        pass

    try:
        # Checkpoint 0: Fast pre-lock Content deduplication
        existing_photo = Photo.objects.filter(wedding=wedding, checksum=job.checksum).first()
        if existing_photo:
            logger.info(f"Photo with checksum {job.checksum[:8]} already exists in wedding {wedding.slug}. Marking job {job_id} COMPLETED.")
            job.photo = existing_photo
            job.status = 'COMPLETED'
            job.completed_at = timezone.now()
            job.save(update_fields=['photo', 'status', 'completed_at', 'updated_at'])
            # Safely clean staging file
            if job.staging_path and os.path.exists(job.staging_path):
                try:
                    os.remove(job.staging_path)
                    job.staging_path = None
                    job.save(update_fields=['staging_path'])
                except OSError:
                    pass
            return

        # Acquire distributed mutex lock per (wedding, checksum) to avoid concurrent processing
        lock_key = f"photo:{wedding.id}:{job.checksum}"
        with acquire_job_lock(lock_key, timeout=180, blocking=False) as acquired:
            if not acquired:
                logger.warning(f"Lock contention on checksum {job.checksum[:8]} for wedding {wedding.slug}. Rescheduling job {job_id}.")
                raise ConcurrencyLockContendedError(f"Another worker is actively processing checksum {job.checksum[:8]}")

            # Inside lock: re-verify if another worker finished the image while we were acquiring the lock
            existing_photo = Photo.objects.filter(wedding=wedding, checksum=job.checksum).first()
            if existing_photo:
                logger.info(f"Photo with checksum {job.checksum[:8]} registered by another worker. Marking job {job_id} COMPLETED.")
                job.photo = existing_photo
                job.status = 'COMPLETED'
                job.completed_at = timezone.now()
                job.save(update_fields=['photo', 'status', 'completed_at', 'updated_at'])
                if job.staging_path and os.path.exists(job.staging_path):
                    try:
                        os.remove(job.staging_path)
                        job.staging_path = None
                        job.save(update_fields=['staging_path'])
                    except OSError:
                        pass
                return

            # Checkpoint 1: Cloudinary Upload (Routed through centralized Cloudinary service)
            if not job.cloudinary_public_id:
                # Ensure staging file exists before uploading
                if not job.staging_path or not os.path.exists(job.staging_path):
                    raise FileNotFoundError(f"Staging file not found on disk at {job.staging_path}. Ephemeral file may have been cleared during container restart.")

                job.status = 'UPLOADING'
                job.uploading_at = timezone.now()
                job.save(update_fields=['status', 'uploading_at', 'updated_at'])

                cld_start = time.perf_counter()
                try:
                    upload_res = upload_photo(
                        file_path=job.staging_path,
                        wedding_slug=wedding.slug,
                        folder=job.folder,
                        checksum=job.checksum,
                        original_filename=job.original_filename
                    )
                    cld_dur = (time.perf_counter() - cld_start) * 1000.0
                    try:
                        from observability.metrics import metrics
                        metrics.record_cloudinary_upload(success=True, duration_ms=cld_dur)
                    except ImportError:
                        pass
                except Exception as cld_err:
                    cld_dur = (time.perf_counter() - cld_start) * 1000.0
                    try:
                        from observability.metrics import metrics
                        metrics.record_cloudinary_upload(success=False, duration_ms=cld_dur, error=str(cld_err))
                    except ImportError:
                        pass
                    raise

                job.cloudinary_public_id = upload_res['public_id']
                job.secure_url = upload_res['secure_url']
                job.cloudinary_url = upload_res.get('cloudinary_url', upload_res['secure_url'])
                job.image_width = upload_res.get('width')
                job.image_height = upload_res.get('height')
                job.format = upload_res.get('format', '')
                job.resource_type = upload_res.get('resource_type', 'image')
                job.status = 'CLOUDINARY_COMPLETED'
                job.cloudinary_completed_at = timezone.now()
                job.save(update_fields=[
                    'cloudinary_public_id', 'secure_url', 'cloudinary_url',
                    'image_width', 'image_height', 'format', 'resource_type',
                    'status', 'cloudinary_completed_at', 'updated_at'
                ])

            # Checkpoint 2: NeonDB Registration (Transactional)
            with transaction.atomic():
                photo, created = Photo.objects.get_or_create(
                    wedding=wedding,
                    checksum=job.checksum,
                    defaults={
                        'original_filename': job.original_filename,
                        'cloudinary_public_id': job.cloudinary_public_id,
                        'secure_url': job.secure_url,
                        'cloudinary_url': job.cloudinary_url,
                        'thumbnail_url': upload_res.get('thumbnail_url') if 'upload_res' in locals() else None,
                        'width': job.image_width,
                        'height': job.image_height,
                        'file_size': job.file_size,
                        'format': job.format,
                        'resource_type': job.resource_type,
                        'folder': job.folder,
                        'processing_status': 'PROCESSING',
                        'upload_status': 'COMPLETED',
                        'captured_at': timezone.now(),
                    }
                )

                if not created:
                    photo.cloudinary_public_id = job.cloudinary_public_id
                    photo.secure_url = job.secure_url
                    photo.cloudinary_url = job.cloudinary_url
                    photo.width = job.image_width
                    photo.height = job.image_height
                    photo.format = job.format
                    photo.resource_type = job.resource_type
                    if 'upload_res' in locals():
                        photo.thumbnail_url = upload_res.get('thumbnail_url', photo.thumbnail_url)
                    photo.save()

                job.photo = photo
                job.status = 'DB_REGISTERED'
                job.db_registered_at = timezone.now()
                job.save(update_fields=['photo', 'status', 'db_registered_at', 'updated_at'])

            # Checkpoint 3: Face Processing (InsightFace with pgvector embeddings)
            job.status = 'FACE_PROCESSING'
            job.face_processing_at = timezone.now()
            job.save(update_fields=['status', 'face_processing_at', 'updated_at'])

            face_start = time.perf_counter()
            try:
                from faces.face_service import generate_embeddings_for_photo
                faces_res = generate_embeddings_for_photo(
                    photo=job.photo,
                    force=False,
                    staging_path=job.staging_path
                )
                face_dur = (time.perf_counter() - face_start) * 1000.0
                try:
                    from observability.metrics import metrics
                    metrics.record_face_extraction(success=True, duration_ms=face_dur, faces_count=len(faces_res or []))
                except ImportError:
                    pass
            except Exception as face_err:
                face_dur = (time.perf_counter() - face_start) * 1000.0
                try:
                    from observability.metrics import metrics
                    metrics.record_face_extraction(success=False, duration_ms=face_dur)
                except ImportError:
                    pass
                logger.error(f"Face extraction failed for job {job_id}: {face_err}")
                job.last_error = f"Face extraction warning: {face_err}"
                job.save(update_fields=['last_error', 'updated_at'])

            job.photo.refresh_from_db()
            job.photo.processing_status = 'COMPLETED'
            job.photo.save(update_fields=['processing_status'])

            # Checkpoint 4: Mark Job COMPLETED
            job.status = 'COMPLETED'
            job.completed_at = timezone.now()
            job.save(update_fields=['status', 'completed_at', 'updated_at'])

            # Checkpoint 5: Broadcast lightweight event to WebSockets
            from photos.realtime import broadcast_new_photo
            broadcast_new_photo(job.photo)

            # Final step: Safe staging file removal ONLY after successful completion commit
            if job.staging_path and os.path.exists(job.staging_path):
                try:
                    os.remove(job.staging_path)
                    job.staging_path = None
                    job.save(update_fields=['staging_path'])
                    logger.info(f"Staging file removed for completed job {job_id}.")
                except OSError as e:
                    logger.warning(f"Failed to remove staging file {job.staging_path}: {e}")

    except ConcurrencyLockContendedError:
        # Re-raise lock contention so Celery task can retry with countdown without counting as failure attempt
        raise
    except Exception as e:
        logger.error(f"Processing failed for IngestionJob {job_id}: {e}", exc_info=True)
        job.attempts += 1
        job.last_error = f"{type(e).__name__}: {str(e)}"
        
        if job.attempts >= job.max_attempts:
            job.status = 'DEAD_LETTER'
            job.dead_letter_reason = f"Max attempts ({job.max_attempts}) reached. Last error: {job.last_error}"
            job.failed_at = timezone.now()
            logger.critical(f"IngestionJob {job_id} moved to DEAD_LETTER: {job.dead_letter_reason}")
        else:
            job.status = 'FAILED'
            job.failed_at = timezone.now()
            backoff_seconds = min(300, 5 * (2 ** (job.attempts - 1)))
            job.next_retry_at = timezone.now() + timedelta(seconds=backoff_seconds)
            logger.warning(f"IngestionJob {job_id} marked FAILED (attempt {job.attempts}/{job.max_attempts}). Retrying in {backoff_seconds}s.")

        job.save()
    finally:
        close_old_connections()


def enqueue_job(job: IngestionJob, priority: int = 10):
    """
    Submits a job ID to the background worker pool.
    In production with Celery/Redis: dispatches to distributed Celery queue 'live_uploads' with priority.
    Fallback (development or single-service): dispatches to in-process ThreadPoolExecutor.
    """
    is_local_redis = any(h in (os.environ.get('REDIS_URL') or '').lower() for h in ('localhost', '127.0.0.1', '::1'))
    use_celery = bool(os.environ.get('REDIS_URL')) and not (not settings.DEBUG and is_local_redis) and not getattr(settings, 'USE_LOCAL_THREAD_WORKER', False)
    if use_celery:
        try:
            from .tasks import process_ingestion_job_task
            process_ingestion_job_task.apply_async(
                args=[str(job.job_id)],
                queue='live_uploads',
                priority=priority
            )
            logger.info(f"IngestionJob {job.job_id} dispatched to Celery 'live_uploads' queue (priority={priority}).")
            return
        except Exception as exc:
            logger.warning(f"Failed to dispatch to Celery ({exc}). Falling back to in-process executor.")

    _ingestion_executor.submit(process_ingestion_job, job.job_id)


def resume_interrupted_jobs():
    """
    Scans for interrupted jobs (application restart recovery) and retryable failed jobs.
    Runs on startup and periodically.
    """
    close_old_connections()
    try:
        now = timezone.now()
        # 1. Recover in-flight jobs interrupted by app restart
        interrupted_jobs = IngestionJob.objects.filter(
            status__in=['RECEIVED', 'QUEUED', 'UPLOADING', 'DB_REGISTERED', 'FACE_PROCESSING']
        )
        count_interrupted = 0
        for job in interrupted_jobs:
            # If job has no cloudinary_public_id and staging file is missing, disk was wiped during container restart
            if not job.cloudinary_public_id and (not job.staging_path or not os.path.exists(job.staging_path)):
                job.status = 'FAILED'
                job.last_error = "Ephemeral staging file lost prior to Cloudinary upload during container restart. Resend required."
                job.failed_at = now
                job.save(update_fields=['status', 'last_error', 'failed_at', 'updated_at'])
                logger.warning(f"Job {job.job_id} marked FAILED: staging file lost during restart.")
                continue

            logger.info(f"Resuming interrupted job {job.job_id} (previous status: {job.status})...")
            job.status = 'QUEUED'
            job.save(update_fields=['status', 'updated_at'])
            enqueue_job(job)
            count_interrupted += 1

        # 2. Recover retryable failed jobs whose backoff window has elapsed
        retryable_jobs = IngestionJob.objects.filter(
            status='FAILED',
            next_retry_at__lte=now,
            attempts__lt=models.F('max_attempts')
        )
        count_retried = 0
        for job in retryable_jobs:
            if not job.cloudinary_public_id and (not job.staging_path or not os.path.exists(job.staging_path)):
                job.status = 'DEAD_LETTER'
                job.dead_letter_reason = "Staging file missing on disk; cannot retry without source image."
                job.save(update_fields=['status', 'dead_letter_reason', 'updated_at'])
                continue

            logger.info(f"Retrying scheduled failed job {job.job_id} (attempt {job.attempts + 1})...")
            job.status = 'QUEUED'
            job.save(update_fields=['status', 'updated_at'])
            enqueue_job(job)
            count_retried += 1

        if count_interrupted or count_retried:
            logger.info(f"Job recovery summary: {count_interrupted} interrupted jobs resumed, {count_retried} failed jobs re-enqueued.")

    except Exception as e:
        logger.error(f"Error in resume_interrupted_jobs: {e}")
    finally:
        close_old_connections()
