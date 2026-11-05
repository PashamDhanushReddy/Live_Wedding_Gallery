import os
import logging

logger = logging.getLogger(__name__)

try:
    from celery import Celery
    from kombu import Queue, Exchange

    # Set default Django settings module for 'celery' program
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

    app = Celery('config')

    # Using a string here means the worker doesn't have to serialize
    # the configuration object to child processes.
    app.config_from_object('django.conf:settings', namespace='CELERY')

    # Load task modules from all registered Django app configs.
    app.autodiscover_tasks()

    default_exchange = Exchange('live_wedding', type='direct')

    # Celery production reliability, priority queues, and resilience configuration
    app.conf.update(
        task_acks_late=True,                # Only acknowledge task after successful completion
        task_reject_on_worker_lost=True,    # Re-queue task if worker process crashes (OOM/restart)
        worker_prefetch_multiplier=1,       # Do not hoard tasks; fetch 1 at a time for fair dispatch
        task_track_started=True,            # Record when a task transitions to STARTED state
        broker_connection_retry_on_startup=True,  # Safe reconnection on container restart
        result_expires=3600,                # Clean up result records after 1 hour
        task_queues=[
            Queue('live_uploads', default_exchange, routing_key='live_uploads', queue_arguments={'x-max-priority': 10}),
            Queue('batch_indexing', default_exchange, routing_key='batch_indexing', queue_arguments={'x-max-priority': 1}),
            Queue('maintenance', default_exchange, routing_key='maintenance'),
            Queue('celery', default_exchange, routing_key='celery'),
        ],
        task_default_queue='live_uploads',
        task_routes={
            'photos.process_ingestion_job_task': {'queue': 'live_uploads', 'priority': 10},
            'faces.process_batch_embeddings_task': {'queue': 'batch_indexing', 'priority': 1},
            'faces.process_single_historical_photo_task': {'queue': 'batch_indexing', 'priority': 1},
            'photos.periodic_cleanup_task': {'queue': 'maintenance'},
        },
    )

    @app.task(bind=True, ignore_result=True)
    def debug_task(self):
        print(f'Celery debug task: {self.request!r}')

except ImportError:
    logger.info("Celery library not installed in current environment; worker features disabled.")
    app = None
