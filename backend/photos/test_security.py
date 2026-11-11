import os
import io
import unittest
from PIL import Image

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from django.core.files.uploadedfile import SimpleUploadedFile

from weddings.models import Wedding
from photos.models import Photo, PhoneDevice
from photos.security import validate_image_file_bytes, sanitize_audit_text


def generate_minimal_jpeg() -> bytes:
    """Generates valid in-memory JPEG bytes (>1KB)."""
    img = Image.new('RGB', (150, 150), color=(255, 0, 0))
    for x in range(0, 150, 4):
        for y in range(0, 150, 4):
            img.putpixel((x, y), (x % 255, y % 255, 128))
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=95)
    return buf.getvalue()


def generate_minimal_png() -> bytes:
    """Generates valid in-memory PNG bytes (>1KB)."""
    img = Image.new('RGB', (120, 120), color=(100, 150, 200))
    # Draw some varied pixels so PNG compression doesn't collapse it below 1KB
    for x in range(0, 120, 2):
        for y in range(0, 120, 2):
            img.putpixel((x, y), (x * 2 % 255, y * 2 % 255, (x + y) % 255))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


class ImageSecurityValidationTests(unittest.TestCase):
    def test_valid_jpeg_passes(self):
        data = generate_minimal_jpeg()
        fmt = validate_image_file_bytes(data)
        self.assertEqual(fmt, 'jpeg')

    def test_valid_png_passes(self):
        data = generate_minimal_png()
        fmt = validate_image_file_bytes(data)
        self.assertEqual(fmt, 'png')

    def test_file_too_small_rejected(self):
        tiny_data = b'\xff\xd8\xff'  # 3 bytes only
        with self.assertRaises(ValueError) as ctx:
            validate_image_file_bytes(tiny_data, min_size=1024)
        self.assertIn("too small", str(ctx.exception))

    def test_file_too_large_rejected(self):
        dummy_large = b'\xff\xd8\xff' + (b'0' * 5000)
        with self.assertRaises(ValueError) as ctx:
            validate_image_file_bytes(dummy_large, max_size=4000)
        self.assertIn("exceeds maximum limit", str(ctx.exception))

    def test_fake_magic_bytes_rejected(self):
        # Starts with valid JPEG bytes but is corrupted data
        fake_data = b'\xff\xd8\xff' + b'MALICIOUS_EXEC_SCRIPT_DATA_HERE' * 50
        with self.assertRaises(ValueError) as ctx:
            validate_image_file_bytes(fake_data)
        self.assertIn("Malformed or corrupted image", str(ctx.exception))


class AuditLogSanitizationTests(unittest.TestCase):
    def test_redacts_sensitive_keys(self):
        raw = "User login failed with password=SecretPassword123 and token=9944b09199c62bcf9ef2"
        clean = sanitize_audit_text(raw)
        self.assertNotIn("SecretPassword123", clean)
        self.assertNotIn("9944b09199c62bcf9ef2", clean)
        self.assertIn("password=[REDACTED]", clean)
        self.assertIn("token=[REDACTED]", clean)

    def test_redacts_biometric_embedding_floats(self):
        # 512-dim embedding float vector
        raw = "Generated face vector: [0.12345, -0.98765, 0.44321, 0.11223, -0.66554, 0.88776]"
        clean = sanitize_audit_text(raw)
        self.assertNotIn("0.12345", clean)
        self.assertIn("[BIOMETRIC_VECTOR_REDACTED]", clean)


class EndpointSecurityContractTests(unittest.TestCase):
    def test_auth_helper_denies_anonymous_request(self):
        from unittest.mock import MagicMock
        from photos.views import authenticate_photographer_or_device

        request = MagicMock()
        request.user.is_authenticated = False
        request.headers = {}
        request.data = {}
        wedding = MagicMock(slug='test-slug')

        is_auth, device, err = authenticate_photographer_or_device(request, wedding)
        self.assertFalse(is_auth)
        self.assertIn("Unauthorized", err)

    def test_auth_helper_allows_active_authenticated_user(self):
        from unittest.mock import MagicMock
        from photos.views import authenticate_photographer_or_device

        request = MagicMock()
        request.user.is_authenticated = True
        request.user.is_active = True
        wedding = MagicMock(slug='test-slug')

        is_auth, device, err = authenticate_photographer_or_device(request, wedding)
        self.assertTrue(is_auth)
        self.assertIsNone(err)

    def test_auth_helper_disallows_device_when_allow_device_is_false(self):
        from unittest.mock import MagicMock
        from photos.views import authenticate_photographer_or_device

        request = MagicMock()
        request.user.is_authenticated = False
        request.headers = {'X-Device-Id': 'phone_01'}
        request.data = {}
        wedding = MagicMock(slug='test-slug')

        is_auth, device, err = authenticate_photographer_or_device(request, wedding, allow_device=False)
        self.assertFalse(is_auth)
        self.assertIn("Unauthorized", err)

    def test_wedding_list_create_view_permissions(self):
        from unittest.mock import MagicMock
        from rest_framework.permissions import IsAdminUser, AllowAny
        from weddings.views import WeddingListCreateView

        view = WeddingListCreateView()
        view.request = MagicMock(method='POST')
        perms = view.get_permissions()
        self.assertTrue(any(isinstance(p, IsAdminUser) for p in perms), "POST must require IsAdminUser")

        view.request = MagicMock(method='GET')
        perms = view.get_permissions()
        self.assertTrue(any(isinstance(p, AllowAny) for p in perms), "GET must allow public viewing")

    def test_rate_limiting_scopes_configured(self):
        from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle
        from weddings.views import FaceSearchView, PhotographerLoginView
        from photos.views import PhoneUploadView, ManualUploadView, PhoneAuthView

        self.assertEqual(getattr(FaceSearchView, 'throttle_scope', None), 'face_search')
        self.assertEqual(getattr(PhotographerLoginView, 'throttle_scope', None), 'photographer_login')
        self.assertEqual(getattr(PhoneUploadView, 'throttle_scope', None), 'photo_upload')
        self.assertEqual(getattr(ManualUploadView, 'throttle_scope', None), 'photo_upload')
        self.assertEqual(getattr(PhoneAuthView, 'throttle_scope', None), 'photographer_login')
        # Batch upload endpoints authenticate via device key / photographer token (not DRF session user),
        # so they must isolate throttling to ScopedRateThrottle instead of sharing AnonRateThrottle with guests.
        self.assertEqual(getattr(PhoneUploadView, 'throttle_classes', None), [ScopedRateThrottle])
        self.assertEqual(getattr(ManualUploadView, 'throttle_classes', None), [ScopedRateThrottle])
        self.assertFalse(any(isinstance(t, AnonRateThrottle) for t in PhoneUploadView().get_throttles()))



class EndpointSecurityAccessControlTests(TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from django.db import connection
            connection.ensure_connection()
        except Exception as e:
            raise unittest.SkipTest(f"Database not reachable for live access control tests: {e}")
        super().setUpClass()

    def setUp(self):
        self.client = APIClient()
        self.wedding = Wedding.objects.create(
            slug="test-wedding",
            bride_name="Sarah",
            groom_name="David",
            wedding_date="2026-11-20",
            is_active=True
        )
        self.inactive_wedding = Wedding.objects.create(
            slug="inactive-wedding",
            bride_name="Eve",
            groom_name="Frank",
            wedding_date="2026-12-01",
            is_active=False
        )

        self.photographer_user = User.objects.create_user(
            username="test_photographer",
            password="SecurePassword456!"
        )
        self.token = Token.objects.create(user=self.photographer_user)

    def test_unauthenticated_wedding_creation_denied(self):
        """Anonymous callers cannot create new weddings."""
        res = self.client.post('/api/weddings/', {
            'slug': 'unauthorized-wedding',
            'bride_name': 'Hacker',
            'groom_name': 'Bot',
            'wedding_date': '2026-11-20'
        })
        self.assertIn(res.status_code, [401, 403])

    def test_inactive_wedding_hidden_from_public(self):
        """Inactive weddings are not returned in public directory."""
        res = self.client.get('/api/weddings/')
        self.assertEqual(res.status_code, 200)
        slugs = [w['slug'] for w in res.data]
        self.assertIn('test-wedding', slugs)
        self.assertNotIn('inactive-wedding', slugs)

    def test_unauthenticated_photo_sync_denied(self):
        """Unauthenticated photo sync must return 401."""
        res = self.client.post(f'/api/weddings/{self.wedding.slug}/sync/', {
            'checksum': 'abc123',
            'original_filename': 'test.jpg'
        })
        self.assertEqual(res.status_code, 401)

    def test_unauthenticated_device_registration_denied(self):
        """Unauthenticated caller cannot register PhoneDevice."""
        res = self.client.post(f'/api/weddings/{self.wedding.slug}/photographer/phone/auth/', {
            'device_id': 'malicious_phone'
        })
        self.assertEqual(res.status_code, 401)
        self.assertFalse(PhoneDevice.objects.filter(device_id='malicious_phone').exists())

    def test_authenticated_device_registration_succeeds(self):
        """Photographer credentials or token allows device registration."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        res = self.client.post(f'/api/weddings/{self.wedding.slug}/photographer/phone/auth/', {
            'device_id': 'valid_phone_01'
        })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(PhoneDevice.objects.filter(wedding=self.wedding, device_id='valid_phone_01').exists())

    def test_camera_connect_requires_auth(self):
        """Unauthenticated camera connect returns 401."""
        res = self.client.post(f'/api/weddings/{self.wedding.slug}/photographer/camera/connect/', {
            'host': '192.168.1.50',
            'port': 2121
        })
        self.assertEqual(res.status_code, 401)

    def test_photographer_stats_requires_auth(self):
        """Unauthenticated photographer stats returns 401."""
        res = self.client.get(f'/api/weddings/{self.wedding.slug}/photographer/stats/')
        self.assertEqual(res.status_code, 401)

    def test_photo_delete_idor_protection(self):
        """
        Photographer cannot delete a photo that belongs to a different wedding.
        """
        other_wedding = Wedding.objects.create(
            slug="other-wedding",
            bride_name="OtherBride",
            groom_name="OtherGroom",
            wedding_date="2026-11-20"
        )
        other_photo = Photo.objects.create(
            wedding=other_wedding,
            original_filename="secret.jpg",
            processing_status="COMPLETED"
        )

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        # Attempting to delete other_wedding's photo via self.wedding slug
        res = self.client.delete(f'/api/weddings/{self.wedding.slug}/photographer/{other_photo.id}/')
        self.assertEqual(res.status_code, 404)
        # Ensure photo was not deleted
        self.assertTrue(Photo.objects.filter(id=other_photo.id).exists())

    def test_face_search_rejects_corrupted_file(self):
        """Face search endpoint rejects non-image or corrupted files."""
        fake_file = SimpleUploadedFile("selfie.jpg", b"NOT_AN_IMAGE_CONTENT" * 100, content_type="image/jpeg")
        res = self.client.post(f'/api/weddings/{self.wedding.slug}/search/', {'file': fake_file}, format='multipart')
        self.assertEqual(res.status_code, 400)
        self.assertIn("INVALID_IMAGE", str(res.data))
