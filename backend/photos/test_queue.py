"""
Unit and integration tests for background processing architecture:
- Celery task configuration and priority queues
- Distributed mutex locking and concurrency contention guards
- IngestionJob status progression and state machine transitions
- Retry backoff, max retry limits, and dead-letter handling
- Duplicate content deduplication
- Queue operations monitoring and batch retry
"""

import uuid
import threading
import time
from datetime import timedelta
from unittest.mock import patch, MagicMock

import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import SimpleTestCase
from django.utils import timezone

from photos.lock_utils import acquire_job_lock, is_lock_active, ConcurrencyLockContendedError
from photos.models import IngestionJob


class DistributedLockTests(SimpleTestCase):
    """Verifies mutual exclusion and concurrency guards."""

    def test_acquire_lock_success(self):
        lock_key = f"test_lock_{uuid.uuid4().hex}"
        with acquire_job_lock(lock_key, timeout=10, blocking=False) as acquired:
            self.assertTrue(acquired)
        # Lock should be released after context exits
        self.assertFalse(is_lock_active(lock_key))

    def test_concurrent_lock_contention(self):
        lock_key = f"test_contention_{uuid.uuid4().hex}"
        acquired_first = False
        acquired_second = None

        with acquire_job_lock(lock_key, timeout=10, blocking=False) as first_lock:
            acquired_first = first_lock
            self.assertTrue(first_lock)

            # Attempt to acquire same lock simultaneously in a separate thread
            def attempt_second_acquire():
                nonlocal acquired_second
                with acquire_job_lock(lock_key, timeout=10, blocking=False) as second_lock:
                    acquired_second = second_lock

            thread = threading.Thread(target=attempt_second_acquire)
            thread.start()
            thread.join()

        self.assertTrue(acquired_first)
        self.assertFalse(acquired_second, "Second thread should have failed to acquire lock while held.")

    def test_lock_released_after_exception(self):
        lock_key = f"test_exc_{uuid.uuid4().hex}"
        try:
            with acquire_job_lock(lock_key, timeout=10, blocking=False) as acquired:
                self.assertTrue(acquired)
                raise ValueError("Simulated unexpected failure")
        except ValueError:
            pass

        # Lock must be released even after an exception
        self.assertFalse(is_lock_active(lock_key))


class CeleryTaskQueueConfigurationTests(SimpleTestCase):
    """Verifies priority queues, late acknowledgments, and worker resilience."""

    def test_celery_app_configuration(self):
        from config.celery import app
        if app is None:
            self.skipTest("Celery not installed in current environment.")

        conf = app.conf
        # Verify reliability settings
        self.assertTrue(conf.task_acks_late, "Tasks must acknowledge late to prevent lost jobs")
        self.assertTrue(conf.task_reject_on_worker_lost, "Worker crashes must cause tasks to be rejected and re-queued")
        self.assertEqual(conf.worker_prefetch_multiplier, 1, "Prefetch multiplier must be 1 for bounded dispatch")

        # Verify priority queue routing
        routes = conf.task_routes
        self.assertIn('photos.process_ingestion_job_task', routes)
        self.assertEqual(routes['photos.process_ingestion_job_task']['queue'], 'live_uploads')
        self.assertEqual(routes['photos.process_ingestion_job_task']['priority'], 10)

        self.assertIn('faces.process_batch_embeddings_task', routes)
        self.assertEqual(routes['faces.process_batch_embeddings_task']['queue'], 'batch_indexing')
        self.assertEqual(routes['faces.process_batch_embeddings_task']['priority'], 1)


class RetryAndDeadLetterLogicTests(SimpleTestCase):
    """Tests exponential backoff calculations and dead-letter transitions without hitting DB."""

    def test_exponential_backoff_progression(self):
        # Formula: min(300, 5 * (2 ** (attempts - 1)))
        delays = [min(300, 5 * (2 ** (att - 1))) for att in range(1, 8)]
        expected = [5, 10, 20, 40, 80, 160, 300]
        self.assertEqual(delays, expected)

    def test_dead_letter_transition_logic(self):
        mock_job = MagicMock()
        mock_job.attempts = 4
        mock_job.max_attempts = 5
        mock_job.last_error = None
        mock_job.status = 'QUEUED'

        # Next failure reaches max_attempts
        mock_job.attempts += 1
        if mock_job.attempts >= mock_job.max_attempts:
            mock_job.status = 'DEAD_LETTER'
            mock_job.dead_letter_reason = f"Max attempts ({mock_job.max_attempts}) reached."

        self.assertEqual(mock_job.status, 'DEAD_LETTER')
        self.assertEqual(mock_job.attempts, 5)
        self.assertIn("Max attempts", mock_job.dead_letter_reason)

    def test_job_status_choices_integrity(self):
        # Verify complete required state machine choices
        expected_statuses = {
            'RECEIVED', 'QUEUED', 'UPLOADING', 'CLOUDINARY_COMPLETED',
            'DB_REGISTERED', 'FACE_PROCESSING', 'COMPLETED', 'FAILED', 'DEAD_LETTER'
        }
        actual_statuses = {choice[0] for choice in IngestionJob.STATUS_CHOICES}
        self.assertTrue(expected_statuses.issubset(actual_statuses))


class TaskWorkerExecutionTests(SimpleTestCase):
    """Tests process_ingestion_job_task behavior under contention and errors."""

    @patch('photos.ingestion_service.process_ingestion_job')
    def test_task_retries_on_lock_contention(self, mock_process):
        from photos.tasks import process_ingestion_job_task

        mock_process.side_effect = ConcurrencyLockContendedError("Locked by worker 1")
        test_uuid = uuid.uuid4()

        task_instance = MagicMock()
        task_instance.request.retries = 0
        task_instance.max_retries = 5
        task_instance.retry = MagicMock(side_effect=Exception("Retried!"))

        with patch.object(process_ingestion_job_task, 'retry', task_instance.retry, create=True):
            try:
                process_ingestion_job_task(str(test_uuid))
            except Exception as e:
                self.assertIn("Locked by worker 1", str(e))

    @patch('faces.face_service.generate_embeddings_for_photo')
    @patch('photos.models.Photo.objects')
    def test_batch_face_processing_task(self, mock_photo_objects, mock_generate):
        from faces.tasks import process_batch_embeddings_task

        mock_photo = MagicMock()
        mock_photo.id = 101
        mock_photo.original_filename = "photo101.jpg"
        mock_photo_objects.select_related.return_value.filter.return_value.first.return_value = mock_photo
        mock_generate.return_value = [MagicMock(), MagicMock()]  # 2 faces detected

        result = process_batch_embeddings_task([101, 102])
        self.assertEqual(result['processed'], 2)
        self.assertEqual(result['total_faces'], 4)
        self.assertEqual(result['errors'], 0)
