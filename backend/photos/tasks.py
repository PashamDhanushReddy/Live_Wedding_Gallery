import uuid
import logging
from django.db import close_old_connections

logger = logging.getLogger(__name__)

try:
    from celery import shared_task
except ImportError:
    # Graceful fallback decorator if celery is not installed in local environment
    def shared_task(*dec_args, **dec_kwargs):
        is_bound = dec_kwargs.get('bind', False)
        def decorator(func):
            class DummyTask:
                request = type('Request', (), {'retries': 0})()
                max_retries = dec_kwargs.get('max_retries', 5)
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
    name='photos.process_ingestion_job_task',
    max_retries=5,
    default_retry_delay=10,
    acks_late=True,
)
def process_ingestion_job_task(self, job_id_str: str):
    """
    Asynchronous Celery worker task for durable photo ingestion:
    - Streams to Cloudinary CDN
    - Registers transactional NeonDB record
    - Executes InsightFace neural inference on worker node
    - Broadcasts lightweight WebSocket event to Channels
    Decouples web requests completely from background processing.
    """
    from .ingestion_service import process_ingestion_job
    from .lock_utils import ConcurrencyLockContendedError
    from .models import IngestionJob

    close_old_connections()
    try:
        from observability.context import set_correlation_id
        set_correlation_id(job_id_str)
    except ImportError:
        pass

    try:
        job_id = uuid.UUID(job_id_str)
        logger.info(f"[Celery Worker] Starting processing for job {job_id}...")
        process_ingestion_job(job_id)
        logger.info(f"[Celery Worker] Successfully completed job {job_id}.")
    except ConcurrencyLockContendedError as lock_err:
        logger.info(f"[Celery Worker] Lock contended for job {job_id_str}: {lock_err}. Retrying in 5 seconds...")
        if hasattr(self, 'retry'):
            raise self.retry(exc=lock_err, countdown=5, max_retries=10)
    except Exception as exc:
        logger.error(f"[Celery Worker] Job {job_id_str} encountered exception: {exc}", exc_info=True)
        if hasattr(self, 'retry') and getattr(self, 'request', None) and getattr(self.request, 'retries', 0) < getattr(self, 'max_retries', 5):
            countdown = min(300, 5 * (2 ** self.request.retries))
            raise self.retry(exc=exc, countdown=countdown)
        else:
            # Retries exhausted - ensure IngestionJob is marked DEAD_LETTER in database
            try:
                job = IngestionJob.objects.filter(job_id=uuid.UUID(job_id_str)).first()
                if job and job.status != 'COMPLETED':
                    job.status = 'DEAD_LETTER'
                    job.dead_letter_reason = f"Celery task retries exhausted ({getattr(self, 'max_retries', 5)}). Last error: {exc}"
                    job.save(update_fields=['status', 'dead_letter_reason', 'updated_at'])
            except Exception as db_err:
                logger.error(f"Failed to record dead-letter status in database: {db_err}")
            raise
    finally:
        close_old_connections()


@shared_task(
    name='photos.periodic_cleanup_task',
    ignore_result=True,
)
def periodic_cleanup_task():
    """Periodic maintenance task: purges stale temporary files, old job logs, and resumes interrupted jobs."""
    from django.core.management import call_command
    from .ingestion_service import resume_interrupted_jobs

    close_old_connections()
    try:
        logger.info("[Celery Worker] Running scheduled database and storage cleanup...")
        call_command('cleanup_stale_data')
        logger.info("[Celery Worker] Scanning for interrupted or retryable jobs...")
        resume_interrupted_jobs()
    except Exception as e:
        logger.error(f"[Celery Worker] Error during scheduled maintenance: {e}")
    finally:
        close_old_connections()
