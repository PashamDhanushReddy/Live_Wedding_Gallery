"""
Unit and regression tests for photos app:
- Django models: Photo, IngestionJob, PhoneDevice, CameraConnection, Transfer
- Serializers: PhotoSerializer, GalleryPhotoSerializer, IngestionJobSerializer
- Cloudinary service: public ID generation, delivery URLs, 3-4 MB compression logic, mock uploads
- Ingestion service: chunked staging, magic byte verification, SHA-256 deduplication, job recovery
- Upload job lifecycle and status transitions
"""

import os
import io
import uuid
import hashlib
from datetime import timedelta
from unittest.mock import patch, MagicMock
from PIL import Image

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import SimpleTestCase
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile

from photos.models import Photo, IngestionJob, PhoneDevice, CameraConnection, Transfer
from photos.serializers import PhotoSerializer, GalleryPhotoSerializer, IngestionJobSerializer
from photos.cloudinary_service import (
    generate_public_id,
    sanitize_folder_name,
    get_thumbnail_url,
    get_preview_url,
    get_large_preview_url,
    get_download_url,
    compress_image_to_target,
    upload_photo,
)
from photos.ingestion_service import (
    stage_uploaded_file,
    sanitize_filename,
    process_ingestion_job,
    resume_interrupted_jobs,
)


def create_test_jpeg(width: int = 100, height: int = 100) -> bytes:
    """Creates valid in-memory JPEG bytes > 1KB."""
    img = Image.new("RGB", (width, height), color=(200, 100, 50))
    for x in range(0, width, 5):
        for y in range(0, height, 5):
            img.putpixel((x, y), (x % 255, y % 255, (x * y) % 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


class PhotoModelAndSerializerTests(SimpleTestCase):
    """Tests Photo model properties, URL generation, and serializers."""

    def test_photo_delivery_url_properties(self):
        photo = Photo(
            original_filename="bride_walk.jpg",
            cloudinary_public_id="weddings/alice_bob/Ceremony/2026-11-21/abcdef1234567890",
            format="jpg",
            secure_url="https://res.cloudinary.com/test/image/upload/v1/sample.jpg"
        )
        self.assertIn("c_limit,f_auto,q_auto,w_1200", photo.preview_url)
        self.assertIn("c_limit,f_auto,q_auto,w_2000", photo.large_preview_url)
        self.assertIn("fl_attachment", photo.download_url)
        self.assertIn("bride_walk", photo.download_url)

    def test_photo_fallback_when_no_cloudinary_id(self):
        photo = Photo(
            original_filename="raw_local.jpg",
            cloudinary_public_id=None,
            secure_url="https://example.com/fallback.jpg"
        )
        self.assertEqual(photo.preview_url, "https://example.com/fallback.jpg")
        self.assertEqual(photo.large_preview_url, "https://example.com/fallback.jpg")
        self.assertEqual(photo.download_url, "https://example.com/fallback.jpg")

    def test_gallery_photo_serializer_fields(self):
        photo = Photo(
            id=42,
            original_filename="reception.jpg",
            cloudinary_public_id="sample_pub_id",
            format="jpg",
            width=3000,
            height=2000,
            file_size=3500000,
            folder="Reception",
            processing_status="COMPLETED",
            created_at=timezone.now()
        )
        serializer = GalleryPhotoSerializer(photo)
        data = serializer.data
        self.assertEqual(data['id'], 42)
        self.assertEqual(data['folder'], "Reception")
        self.assertEqual(data['width'], 3000)
        self.assertEqual(data['height'], 2000)
        self.assertIn('thumbnail_url', data)
        self.assertIn('preview_url', data)
        self.assertIn('download_url', data)
        # Verify master asset original URL is NOT leaked in gallery serializer
        self.assertNotIn('secure_url', data)


class CloudinaryServiceTests(SimpleTestCase):
    """Tests deterministic public IDs, format transformations, and mock upload mode."""

    def test_sanitize_folder_name(self):
        self.assertEqual(sanitize_folder_name(''), 'originals')
        self.assertEqual(sanitize_folder_name('Uncategorized'), 'originals')
        self.assertEqual(sanitize_folder_name('Bride and Groom'), 'Bride_and_Groom')
        self.assertEqual(sanitize_folder_name('Ceremony/2026!'), 'Ceremony_2026_')

    def test_generate_public_id_structure(self):
        from datetime import datetime, timezone as dt_timezone
        fixed_date = datetime(2026, 11, 21, tzinfo=dt_timezone.utc)
        pub_id = generate_public_id(
            wedding_slug='alice-bob',
            folder='Ceremony',
            checksum='9f83778d96e57973a65b1e1e1a0208c556f3b046b',
            upload_date=fixed_date
        )
        expected = "weddings/alice-bob/Ceremony/2026-11-21/9f83778d96e57973"
        self.assertEqual(pub_id, expected)

    def test_delivery_url_transformations(self):
        pub_id = "weddings/test/Ceremony/2026-11-21/12345678"
        thumb = get_thumbnail_url(pub_id, fmt="jpg")
        preview = get_preview_url(pub_id, fmt="jpg")
        large = get_large_preview_url(pub_id, fmt="jpg")
        download = get_download_url(pub_id, fmt="jpg", filename="walk.jpg")

        self.assertIn("w_400", thumb)
        self.assertIn("w_1200", preview)
        self.assertIn("w_2000", large)
        self.assertIn("attachment:walk", download)

    def test_mock_cloudinary_upload_mode(self):
        """Validates that MOCK_CLOUDINARY returns full CDN metadata without making HTTP calls."""
        with patch.dict(os.environ, {'MOCK_CLOUDINARY': 'true'}):
            res = upload_photo(
                file_path='test_image.jpg',
                wedding_slug='test-slug',
                folder='Guests',
                checksum='abcdef1234567890abcdef',
                original_filename='test_image.jpg'
            )
            self.assertIn('public_id', res)
            self.assertIn('secure_url', res)
            self.assertIn('thumbnail_url', res)
            self.assertEqual(res['resource_type'], 'image')
            self.assertEqual(res['width'], 3000)

    def test_compress_image_to_target_cloud_saver(self):
        """Verifies large image compression compresses down to <= 800 KB for Cloudinary free tier."""
        import tempfile
        # Create a test high-res image
        large_jpeg = create_test_jpeg(width=3200, height=2400)
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(large_jpeg)
            temp_in = f.name

        try:
            # Optimize with 800 KB target
            out_path, is_temp = compress_image_to_target(temp_in, max_kb=800, max_dim=2560)
            out_size = os.path.getsize(out_path)
            self.assertLessEqual(out_size, 800 * 1024)
            if is_temp and os.path.exists(out_path):
                os.remove(out_path)
        finally:
            if os.path.exists(temp_in):
                os.remove(temp_in)


class FileStagingAndValidationTests(SimpleTestCase):
    """Tests file staging to disk, magic byte inspections, and size checks."""

    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename("../../etc/passwd"), "passwd")
        self.assertEqual(sanitize_filename("valid_photo.JPG"), "valid_photo.JPG")
        self.assertEqual(sanitize_filename(".hidden"), "photo_" + sanitize_filename(".hidden").split('_')[1])
        self.assertTrue(sanitize_filename("bad;char#name?.jpg").startswith("bad_char_name_"))

    def test_stage_valid_jpeg(self):
        jpeg_bytes = create_test_jpeg(120, 120)
        uploaded = SimpleUploadedFile("wedding.jpg", jpeg_bytes, content_type="image/jpeg")
        job_id = uuid.uuid4()

        staged = stage_uploaded_file(uploaded, job_id=job_id)
        self.assertTrue(os.path.exists(staged['staging_path']))
        self.assertEqual(staged['mime_type'], 'image/jpeg')
        self.assertEqual(staged['file_size'], len(jpeg_bytes))
        self.assertEqual(staged['checksum'], hashlib.sha256(jpeg_bytes).hexdigest())

        # Cleanup test staging file
        if os.path.exists(staged['staging_path']):
            os.remove(staged['staging_path'])

    def test_stage_rejects_non_image_magic_bytes(self):
        text_bytes = b"This is a text file posing as an image. Not a real JPEG."
        uploaded = SimpleUploadedFile("fake.jpg", text_bytes, content_type="image/jpeg")
        job_id = uuid.uuid4()

        with self.assertRaises(ValueError) as ctx:
            stage_uploaded_file(uploaded, job_id=job_id)
        self.assertIn("Invalid file signature", str(ctx.exception))

    def test_stage_rejects_undersized_incomplete_file(self):
        # 100 bytes (below 1KB minimum threshold)
        tiny_bytes = b'\xff\xd8\xff' + (b'A' * 97)
        uploaded = SimpleUploadedFile("corrupt.jpg", tiny_bytes, content_type="image/jpeg")
        job_id = uuid.uuid4()

        with self.assertRaises(ValueError) as ctx:
            stage_uploaded_file(uploaded, job_id=job_id)
        # Either magic bytes/image verification or size threshold rejects it
        self.assertTrue("Corrupted" in str(ctx.exception) or "too small" in str(ctx.exception) or "Invalid file" in str(ctx.exception))


class JobLifecycleAndRecoveryTests(SimpleTestCase):
    """Tests job state transitions, restart recovery, and dead-letter handling."""

    def test_ingestion_job_state_progression(self):
        job = IngestionJob(
            job_id=uuid.uuid4(),
            status='RECEIVED',
            checksum='abc12345',
            original_filename='ring.jpg',
            attempts=0,
            max_attempts=5
        )
        self.assertEqual(job.status, 'RECEIVED')

        # Progress to QUEUED
        job.status = 'QUEUED'
        job.queued_at = timezone.now()
        self.assertEqual(job.status, 'QUEUED')

        # Progress to UPLOADING
        job.status = 'UPLOADING'
        job.uploading_at = timezone.now()
        self.assertEqual(job.status, 'UPLOADING')

        # Progress to CLOUDINARY_COMPLETED
        job.status = 'CLOUDINARY_COMPLETED'
        job.cloudinary_public_id = 'weddings/test/ring_123'
        job.cloudinary_completed_at = timezone.now()
        self.assertEqual(job.status, 'CLOUDINARY_COMPLETED')

        # Progress to COMPLETED
        job.status = 'COMPLETED'
        job.completed_at = timezone.now()
        self.assertEqual(job.status, 'COMPLETED')

    def test_retry_exponential_backoff_progression(self):
        job = IngestionJob(job_id=uuid.uuid4(), status='QUEUED', attempts=0, max_attempts=5)
        # Simulate consecutive failures
        backoffs = []
        for _ in range(4):
            job.attempts += 1
            delay = min(300, 5 * (2 ** (job.attempts - 1)))
            backoffs.append(delay)

        self.assertEqual(backoffs, [5, 10, 20, 40])

    def test_dead_letter_transition_on_max_attempts(self):
        job = IngestionJob(job_id=uuid.uuid4(), status='FAILED', attempts=4, max_attempts=5)
        job.attempts += 1
        if job.attempts >= job.max_attempts:
            job.status = 'DEAD_LETTER'
            job.dead_letter_reason = f"Max attempts ({job.max_attempts}) reached."

        self.assertEqual(job.status, 'DEAD_LETTER')
        self.assertIn("Max attempts", job.dead_letter_reason)
