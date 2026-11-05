"""
Asynchronous background tasks for face detection, 512-dim embedding generation,
and historical photo batch processing.
Routed to the low-priority 'batch_indexing' Celery queue so interactive live uploads
are never delayed or starved by historical scans.
"""

import logging
from typing import List
from django.db import close_old_connections

logger = logging.getLogger(__name__)

try:
    from celery import shared_task
except ImportError:
    def shared_task(*dec_args, **dec_kwargs):
        is_bound = dec_kwargs.get('bind', False)
        def decorator(func):
            class DummyTask:
                request = type('Request', (), {'retries': 0})()
                max_retries = dec_kwargs.get('max_retries', 3)
                def retry(self, exc=None, **kw):
                    raise exc or Exception("Retry requested")
            def wrapper(*a, **kw):
                if is_bound:
                    return func(DummyTask(), *a, **kw)
                return func(*a, **kw)
            wrapper.delay = lambda *a, **kw: wrapper(*a, **kw)
            wrapper.apply_async = lambda *a, **kw: wrapper(*(kw.get('args', a)), **(kw.get('kwargs', {})))
            return wrapper
        return decorator


@shared_task(
    bind=True,
    name='faces.process_single_historical_photo_task',
    max_retries=3,
    default_retry_delay=15,
    acks_late=True,
)
def process_single_historical_photo_task(self, photo_id: int, force: bool = False):
    """Processes face embeddings for an individual historical photo."""
    from photos.models import Photo
    from faces.face_service import generate_embeddings_for_photo
    close_old_connections()
    try:
        photo = Photo.objects.select_related('wedding').filter(id=photo_id).first()
        if not photo:
            logger.warning(f"Photo {photo_id} not found for face embedding task.")
            return

        logger.info(f"[Celery Batch Worker] Generating embeddings for Photo {photo_id} ({photo.original_filename})...")
        faces = generate_embeddings_for_photo(photo=photo, force=force)
        logger.info(f"[Celery Batch Worker] Completed Photo {photo_id}: extracted {len(faces)} face(s).")
    except Exception as exc:
        logger.error(f"[Celery Batch Worker] Failed on photo {photo_id}: {exc}", exc_info=True)
        if hasattr(self, 'retry'):
            raise self.retry(exc=exc)
        raise
    finally:
        close_old_connections()


@shared_task(
    bind=True,
    name='faces.process_batch_embeddings_task',
    max_retries=3,
    default_retry_delay=20,
    acks_late=True,
)
def process_batch_embeddings_task(self, photo_ids: List[int], force: bool = False):
    """
    Processes a chunk of historical photos sequentially within one worker task.
    Reduces Celery task dispatch overhead for large historical collections (10k-20k photos).
    """
    from photos.models import Photo
    from faces.face_service import generate_embeddings_for_photo
    close_old_connections()
    logger.info(f"[Celery Batch Worker] Starting batch embedding generation for {len(photo_ids)} photos...")
    processed_count = 0
    total_faces = 0
    errors = 0

    try:
        # Fetch photos one-by-one or chunked to keep memory bounded
        for pid in photo_ids:
            try:
                photo = Photo.objects.select_related('wedding').filter(id=pid).first()
                if not photo:
                    continue
                faces = generate_embeddings_for_photo(photo=photo, force=force)
                total_faces += len(faces)
                processed_count += 1
            except Exception as e:
                errors += 1
                logger.warning(f"[Celery Batch Worker] Error processing photo {pid}: {e}")

        logger.info(
            f"[Celery Batch Worker] Finished batch: {processed_count}/{len(photo_ids)} photos processed, "
            f"{total_faces} faces extracted, {errors} errors."
        )
        return {
            'processed': processed_count,
            'total_faces': total_faces,
            'errors': errors
        }
    except Exception as exc:
        logger.error(f"[Celery Batch Worker] Critical failure in batch {photo_ids[:5]}...: {exc}", exc_info=True)
        if hasattr(self, 'retry'):
            raise self.retry(exc=exc)
        raise
    finally:
        close_old_connections()
