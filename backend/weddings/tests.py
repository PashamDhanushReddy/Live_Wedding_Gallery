"""
Unit, permission, pagination, and WebSocket tests for weddings app:
- Wedding models, active querying, and serializers
- Photographer authentication and permissions
- GalleryCursorPagination: page limits (25 default, 50 max), deterministic (-created_at, -id) ordering
- Multi-dimensional filters: folder, date, device, photographer, and search
- Photo deletion authorization boundaries
- WebSocket consumers and subscription isolation
"""

import os
import json
from unittest.mock import patch, MagicMock

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory
from rest_framework import status

from weddings.models import Wedding
from weddings.serializers import WeddingSerializer
from photos.models import Photo
from photos.serializers import GalleryPhotoSerializer
from weddings.views import (
    WeddingDetailView,
    WeddingPhotosView,
    PhotographerLoginView,
    GalleryCursorPagination,
)


class WeddingModelAndSerializerTests(SimpleTestCase):
    """Tests Wedding model attributes and serialization."""

    def test_wedding_serializer_fields(self):
        wedding = Wedding(
            id=10,
            slug="priya-rahul",
            wedding_title="Priya & Rahul's Wedding",
            bride_name="Priya",
            groom_name="Rahul",
            wedding_date=timezone.now().date(),
            venue="Grand Palace",
            is_active=True
        )
        serializer = WeddingSerializer(wedding)
        data = serializer.data
        self.assertEqual(data['slug'], "priya-rahul")
        self.assertEqual(data['bride_name'], "Priya")
        self.assertEqual(data['groom_name'], "Rahul")
        self.assertEqual(data['venue'], "Grand Palace")
        self.assertTrue(data['is_active'])

    def test_wedding_string_representation(self):
        wedding = Wedding(bride_name="Priya", groom_name="Rahul")
        self.assertEqual(str(wedding), "Priya & Rahul")


class GalleryCursorPaginationTests(SimpleTestCase):
    """Verifies cursor pagination boundaries and sorting contracts."""

    def test_pagination_bounds(self):
        paginator = GalleryCursorPagination()
        self.assertEqual(paginator.page_size, 25)
        self.assertEqual(paginator.max_page_size, 50)
        self.assertEqual(paginator.ordering, ('-created_at', '-id'))
        self.assertEqual(paginator.cursor_query_param, 'cursor')

    def test_pagination_response_structure(self):
        paginator = GalleryCursorPagination()
        paginator.page_size = 25
        paginator.total_count = 120

        # Simulate get_paginated_response
        with patch.object(paginator, 'get_next_link', return_value="http://test/?cursor=next123"), \
             patch.object(paginator, 'get_previous_link', return_value=None):
            
            resp = paginator.get_paginated_response([{"id": 1}, {"id": 2}])
            self.assertEqual(resp.data['count'], 120)
            self.assertEqual(resp.data['page_size'], 25)
            self.assertEqual(resp.data['next'], "http://test/?cursor=next123")
            self.assertIsNone(resp.data['previous'])
            self.assertEqual(len(resp.data['results']), 2)


class WeddingViewAuthorizationAndFilteringTests(SimpleTestCase):
    """Tests authorization boundaries and query filtering logic."""

    def setUp(self):
        self.factory = APIRequestFactory()

    @patch('weddings.views.authenticate')
    @patch('weddings.views.get_object_or_404')
    def test_photographer_login_invalid_credentials(self, mock_get_wedding, mock_auth):
        mock_wedding = MagicMock(slug='test-slug', is_active=True)
        mock_get_wedding.return_value = mock_wedding
        mock_auth.return_value = None  # Failed auth

        req = self.factory.post('/api/weddings/test-slug/login/', {
            'username': 'photographer',
            'password': 'WrongPassword!'
        })
        view = PhotographerLoginView.as_view()
        resp = view(req, slug='test-slug')

        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(resp.data['status'], 'error')

    @patch('photos.views.delete_photo')
    @patch('photos.realtime.broadcast_delete_photo')
    @patch('photos.views.get_object_or_404')
    def test_photo_delete_unauthorized_guest(self, mock_get_obj, mock_broadcast, mock_cld_delete):
        """Guests cannot delete photos; requires photographer or staff token."""
        from photos.views import PhotoDeleteView
        mock_wedding = MagicMock(slug='test-slug', is_active=True)
        mock_photo = MagicMock(id=99, original_filename='photo99.jpg', wedding=mock_wedding)
        mock_get_obj.side_effect = [mock_wedding, mock_photo]

        req = self.factory.delete('/api/weddings/test-slug/photos/99/')
        view = PhotoDeleteView.as_view()
        resp = view(req, slug='test-slug', pk=99)

        # Anonymous request without token must be rejected with 401
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        mock_photo.delete.assert_not_called()
        mock_cld_delete.assert_not_called()

    @patch('weddings.views.get_object_or_404')
    def test_wedding_photos_view_unauthorized_guest_rejected(self, mock_get_wedding):
        """Unauthenticated guests cannot view all photos; must be 403 Forbidden for privacy."""
        mock_wedding = MagicMock(slug='test-slug', is_active=True)
        mock_get_wedding.return_value = mock_wedding

        req = self.factory.get('/api/weddings/test-slug/photos/')
        view = WeddingPhotosView.as_view()
        resp = view(req, slug='test-slug')

        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(resp.data['code'], 'GALLERY_PRIVACY_RESTRICTED')

    @patch('photos.views.authenticate_photographer_or_device')
    @patch('weddings.views.get_object_or_404')
    def test_wedding_photos_view_authorized_photographer_allowed(self, mock_get_wedding, mock_auth):
        """Authenticated photographers can view all photos."""
        mock_wedding = MagicMock(slug='test-slug', is_active=True)
        mock_get_wedding.return_value = mock_wedding
        mock_auth.return_value = (True, None, None)

        req = self.factory.get('/api/weddings/test-slug/photos/', HTTP_X_PHOTOGRAPHER_TOKEN='test-token-123')
        view = WeddingPhotosView.as_view()
        with patch.object(WeddingPhotosView, 'get_queryset') as mock_get_qs:
            mock_qs = MagicMock()
            mock_qs.count.return_value = 0
            mock_qs.order_by.return_value = []
            mock_get_qs.return_value = mock_qs
            resp = view(req, slug='test-slug')
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
            self.assertEqual(resp['Cache-Control'], 'private, no-cache')
            self.assertIn('Authorization', resp['Vary'])

    def test_cors_allows_photographer_headers(self):
        """CORS preflight must allow custom photographer/device headers."""
        from django.conf import settings
        self.assertIn('x-photographer-token', settings.CORS_ALLOW_HEADERS)
        self.assertIn('x-device-id', settings.CORS_ALLOW_HEADERS)


class WebSocketConsumerProtocolTests(SimpleTestCase):
    """Tests WebSocket event payloads and subscription isolation."""

    def test_new_photo_broadcast_payload_structure(self):
        from photos.realtime import broadcast_new_photo

        mock_photo = MagicMock()
        mock_photo.id = 501
        mock_photo.processing_status = 'COMPLETED'
        mock_photo.wedding.slug = 'alice-bob'
        mock_photo.wedding.id = 12
        mock_photo.folder = 'Ceremony'
        mock_photo.created_at = timezone.now()

        with patch('photos.realtime.get_channel_layer') as mock_layer_getter, \
             patch('photos.realtime.async_to_sync') as mock_async_to_sync, \
             patch('photos.realtime.invalidate_gallery_cache') as mock_inval:

            mock_layer = MagicMock()
            mock_layer_getter.return_value = mock_layer
            mock_send = MagicMock()
            mock_async_to_sync.return_value = mock_send

            success = broadcast_new_photo(mock_photo)
            self.assertTrue(success)

            # Assert targeted to correct wedding room only
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0]
            self.assertEqual(call_args[0], 'wedding_alice-bob')
            event = call_args[1]
            self.assertEqual(event['type'], 'new_photo')
            self.assertEqual(event['photo_id'], 501)
            self.assertEqual(event['folder'], 'Ceremony')
            self.assertEqual(event['status'], 'COMPLETED')
            mock_inval.assert_called_once_with(12, 'alice-bob')

    def test_uncompleted_photo_never_broadcasts_to_guests(self):
        """Photographs still in PROCESSING or FAILED must NEVER be broadcast to guests."""
        from photos.realtime import broadcast_new_photo

        mock_photo = MagicMock()
        mock_photo.id = 502
        mock_photo.processing_status = 'PROCESSING'
        mock_photo.wedding.slug = 'alice-bob'

        with patch('photos.realtime.get_channel_layer') as mock_layer_getter:
            success = broadcast_new_photo(mock_photo)
            self.assertFalse(success)
            mock_layer_getter.assert_not_called()


class FolderPreservationTests(SimpleTestCase):
    """Tests folder preservation and correction across manual upload and AI categorization."""

    def test_categorize_photo_preserves_event_and_explicit_portrait_folders(self):
        from photos.categorization import categorize_photo

        mock_wedding = MagicMock(bride_embedding=[1.0, 0.0], groom_embedding=[0.0, 1.0])

        # Event folder must never be overwritten even if faces match Bride
        event_photo = MagicMock(
            wedding=mock_wedding,
            folder='Wedding Day',
            ai_category=None,
        )
        event_photo.faces.all.return_value = [MagicMock(width=200, height=200, embedding=[1.0, 0.0])]
        self.assertTrue(categorize_photo(event_photo))
        self.assertEqual(event_photo.folder, 'Wedding Day')
        self.assertEqual(event_photo.ai_category, 'Bride')

        # Explicit portrait folder must not be downgraded to Uncategorized on miss
        portrait_photo = MagicMock(
            wedding=mock_wedding,
            folder='Bride',
            ai_category=None,
        )
        portrait_photo.faces.all.return_value = []
        self.assertFalse(categorize_photo(portrait_photo))
        self.assertEqual(portrait_photo.folder, 'Bride')

    @patch('photos.realtime.invalidate_gallery_cache')
    @patch('photos.views.stage_uploaded_file')
    @patch('photos.views.Photo.objects')
    @patch('photos.views.IngestionJob.objects')
    @patch('photos.views.authenticate_photographer_or_device')
    @patch('photos.views.get_object_or_404')
    def test_manual_upload_updates_folder_for_duplicate_photo(
        self, mock_get_wedding, mock_auth, mock_job_mgr, mock_photo_mgr, mock_stage, mock_inval
    ):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from photos.views import ManualUploadView

        mock_wedding = MagicMock(id=7, slug='test-slug', is_active=True)
        mock_get_wedding.return_value = mock_wedding
        mock_auth.return_value = (True, None, None)

        mock_job = MagicMock(job_id='job-123', staging_path=None)
        mock_job_mgr.create.return_value = mock_job
        mock_stage.return_value = {
            'staging_path': None,
            'checksum': 'abc123',
            'file_size': 1024,
            'mime_type': 'image/jpeg',
            'original_filename': 'shot.jpg',
        }

        existing_photo = MagicMock(folder='Ceremony')
        mock_photo_mgr.filter.return_value.first.return_value = existing_photo

        req = APIRequestFactory().post(
            '/api/weddings/test-slug/photographer/upload/',
            data={
                'folder': 'Wedding Day',
                'photos': SimpleUploadedFile('shot.jpg', b'fake-jpeg', content_type='image/jpeg'),
            },
            format='multipart',
        )
        resp = ManualUploadView.as_view()(req, slug='test-slug')

        self.assertEqual(resp.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(existing_photo.folder, 'Wedding Day')
        existing_photo.save.assert_called_with(update_fields=['folder'])
        mock_inval.assert_any_call(7, 'test-slug', 'Ceremony')
        mock_inval.assert_any_call(7, 'test-slug', 'Wedding Day')
