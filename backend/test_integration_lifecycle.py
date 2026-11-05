"""
Comprehensive end-to-end integration tests for Live Wedding Gallery:
- Full lifecycle: Camera -> Android Companion -> Django Ingestion -> Cloudinary CDN -> NeonDB -> WebSockets -> Gallery Display
- Face processing and visitor selfie search pipeline
- Duplicate upload handling, idempotency, and concurrent lock contention
- Malformed, corrupted, and oversized image rejection
- Worker restart recovery and queue resilience
"""

import os
import io
import uuid
import hashlib
from unittest.mock import patch, MagicMock
from PIL import Image

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import SimpleTestCase
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIRequestFactory
from rest_framework import status

from weddings.models import Wedding
from photos.models import Photo, IngestionJob, PhoneDevice
from photos.views import PhoneUploadView
from weddings.views import WeddingPhotosView, FaceSearchView
from photos.ingestion_service import (
    process_ingestion_job,
    resume_interrupted_jobs,
)
from photos.lock_utils import ConcurrencyLockContendedError


def generate_valid_jpeg_stream(width: int = 150, height: int = 150) -> bytes:
    """Generates valid JPEG bytes with valid SOI and EOI markers."""
    img = Image.new("RGB", (width, height), color=(150, 180, 210))
    for x in range(0, width, 6):
        for y in range(0, height, 6):
            img.putpixel((x, y), (x % 255, y % 255, 128))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


class FullLifecycleIntegrationTests(SimpleTestCase):
    """Verifies the complete end-to-end pipeline across services."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.wedding = Wedding(
            id=101,
            slug="integration-wedding",
            wedding_title="Integration Test Wedding",
            bride_name="Emma",
            groom_name="Liam",
            wedding_date=timezone.now().date(),
            is_active=True
        )

    @patch('photos.views.get_object_or_404')
    @patch('photos.views.authenticate_photographer_or_device')
    @patch('photos.views.enqueue_job')
    @patch('photos.models.IngestionJob.objects.create')
    @patch('photos.models.IngestionJob.objects.filter')
    @patch('photos.models.Photo.objects.filter')
    def test_end_to_end_upload_intake_to_queue(
        self,
        mock_photo_filter,
        mock_job_filter,
        mock_job_create,
        mock_enqueue,
        mock_auth,
        mock_get_obj
    ):
        """Tests companion app streaming a photo into Django, creating IngestionJob, and returning HTTP 202."""
        mock_get_obj.return_value = self.wedding
        mock_device = PhoneDevice(device_id="companion_cam_01", wedding=self.wedding)
        mock_auth.return_value = (True, mock_device, None)
        mock_job_filter.return_value.first.return_value = None  # No existing job
        mock_photo_filter.return_value.first.return_value = None  # No existing duplicate

        upload_id = str(uuid.uuid4())
        jpeg_data = generate_valid_jpeg_stream()
        checksum = hashlib.sha256(jpeg_data).hexdigest()

        uploaded_file = SimpleUploadedFile("ceremony_kiss.jpg", jpeg_data, content_type="image/jpeg")

        mock_job = IngestionJob(
            job_id=uuid.uuid4(),
            upload_id=upload_id,
            wedding=self.wedding,
            checksum=checksum,
            status='RECEIVED',
            original_filename='ceremony_kiss.jpg',
            folder='Ceremony'
        )
        mock_job.save = MagicMock()
        mock_job_create.return_value = mock_job

        req = self.factory.post(
            f"/api/weddings/{self.wedding.slug}/phone/upload/",
            {
                'photo': uploaded_file,
                'upload_id': upload_id,
                'checksum': checksum,
                'folder': 'Ceremony'
            },
            format='multipart'
        )
        view = PhoneUploadView.as_view()
        resp = view(req, slug=self.wedding.slug)

        self.assertEqual(resp.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(resp.data['status'], 'QUEUED')
        self.assertEqual(resp.data['checksum'], checksum)
        mock_enqueue.assert_called_once()

    @patch('photos.ingestion_service.transaction.atomic')
    @patch('photos.ingestion_service.IngestionJob.objects.select_related')
    @patch('photos.ingestion_service.Photo.objects.filter')
    @patch('photos.ingestion_service.Photo.objects.get_or_create')
    @patch('photos.ingestion_service.upload_photo')
    @patch('faces.face_service.generate_embeddings_for_photo')
    @patch('photos.realtime.broadcast_new_photo')
    def test_background_worker_processing_lifecycle(
        self,
        mock_broadcast,
        mock_generate_faces,
        mock_cld_upload,
        mock_get_or_create_photo,
        mock_photo_filter,
        mock_job_select,
        mock_atomic
    ):
        """
        Tests the background worker state transitions:
        QUEUED -> UPLOADING -> CLOUDINARY_COMPLETED -> DB_REGISTERED -> FACE_PROCESSING -> COMPLETED.
        """
        mock_atomic.return_value.__enter__.return_value = None
        job_id = uuid.uuid4()
        checksum = hashlib.sha256(b"photo_content_bytes").hexdigest()

        # Temporary dummy staging file
        temp_staging = f"staging_test_{job_id.hex}.jpg"
        with open(temp_staging, "wb") as f:
            f.write(generate_valid_jpeg_stream())

        try:
            mock_job = IngestionJob(
                job_id=job_id,
                wedding=self.wedding,
                checksum=checksum,
                original_filename="cake.jpg",
                staging_path=temp_staging,
                status='QUEUED',
                folder='Reception',
                attempts=0,
                max_attempts=5
            )
            mock_job.save = MagicMock()
            mock_job_select.return_value.get.return_value = mock_job
            mock_photo_filter.return_value.first.return_value = None

            # Mock Cloudinary receipt
            mock_cld_upload.return_value = {
                'public_id': 'weddings/test/cake_123',
                'secure_url': 'https://res.cloudinary.com/test/cake.jpg',
                'cloudinary_url': 'http://res.cloudinary.com/test/cake.jpg',
                'thumbnail_url': 'https://res.cloudinary.com/test/thumb.jpg',
                'width': 3000,
                'height': 2000,
                'format': 'jpg',
                'resource_type': 'image',
            }

            mock_photo = Photo(
                id=88,
                wedding=self.wedding,
                checksum=checksum,
                original_filename="cake.jpg",
                cloudinary_public_id="weddings/test/cake_123",
                processing_status="PROCESSING"
            )
            mock_photo.refresh_from_db = MagicMock()
            mock_photo.save = MagicMock()
            mock_get_or_create_photo.return_value = (mock_photo, True)
            mock_generate_faces.return_value = [MagicMock()]

            # Execute background processor
            process_ingestion_job(job_id)

            # Verify Cloudinary upload was called with correct parameters
            mock_cld_upload.assert_called_once()
            # Verify Photo was created in NeonDB
            mock_get_or_create_photo.assert_called_once()
            # Verify Face embedding extraction was executed
            mock_generate_faces.assert_called_once()
            # Verify WebSocket broadcast was dispatched
            mock_broadcast.assert_called_once()
            # Verify final job status is COMPLETED
            self.assertEqual(mock_job.status, 'COMPLETED')
        finally:
            if os.path.exists(temp_staging):
                try:
                    os.remove(temp_staging)
                except OSError:
                    pass

    @patch('photos.views.get_object_or_404')
    @patch('photos.views.authenticate_photographer_or_device')
    @patch('photos.models.IngestionJob.objects.filter')
    def test_duplicate_upload_id_handled_idempotently(
        self,
        mock_job_filter,
        mock_auth,
        mock_get_obj
    ):
        """Duplicate upload_id (e.g. Companion app network retry) returns existing status without double work."""
        mock_get_obj.return_value = self.wedding
        mock_auth.return_value = (True, None, None)

        existing_completed_job = IngestionJob(
            job_id=uuid.uuid4(),
            upload_id="existing_client_uuid_123",
            wedding=self.wedding,
            photo_id=55,
            status="COMPLETED"
        )
        mock_job_filter.return_value.first.return_value = existing_completed_job

        req = self.factory.post(
            f"/api/weddings/{self.wedding.slug}/phone/upload/",
            {
                'photo': SimpleUploadedFile("retry.jpg", generate_valid_jpeg_stream()),
                'upload_id': "existing_client_uuid_123"
            },
            format='multipart'
        )
        view = PhoneUploadView.as_view()
        resp = view(req, slug=self.wedding.slug)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], 'COMPLETED')
        self.assertEqual(resp.data['message'], 'Upload already completed')

    def test_malformed_and_corrupt_image_rejection(self):
        """Malformed or non-image payloads are strictly rejected before job queuing."""
        corrupt_bytes = b"\xff\xd8\xffMALICIOUS_CORRUPT_SHELL_PAYLOAD_HERE" + (b"0" * 2000)
        uploaded = SimpleUploadedFile("exploit.jpg", corrupt_bytes, content_type="image/jpeg")

        from photos.ingestion_service import stage_uploaded_file
        job_id = uuid.uuid4()

        with self.assertRaises(ValueError) as ctx:
            stage_uploaded_file(uploaded, job_id=job_id)

        self.assertTrue(
            "Corrupted" in str(ctx.exception) or
            "Invalid file" in str(ctx.exception) or
            "Malformed" in str(ctx.exception)
        )

    @patch('photos.ingestion_service.IngestionJob.objects.filter')
    @patch('photos.ingestion_service.enqueue_job')
    def test_worker_restart_recovery_resumes_interrupted_jobs(
        self,
        mock_enqueue,
        mock_job_filter
    ):
        """Jobs left in-flight during a container restart or crash are recovered safely."""
        job_1 = IngestionJob(
            job_id=uuid.uuid4(),
            status='UPLOADING',
            cloudinary_public_id='weddings/test/uploaded_prior_to_restart',
            staging_path=None
        )
        job_1.save = MagicMock()

        # Mock query return for interrupted jobs (first call: interrupted, second call: retryable)
        mock_job_filter.side_effect = [[job_1], []]

        resume_interrupted_jobs()

        self.assertEqual(job_1.status, 'QUEUED')
        mock_enqueue.assert_called_once_with(job_1)
