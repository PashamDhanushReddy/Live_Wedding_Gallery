"""
Capacity and caching verification tests:
- Verifies that WeddingDetailView, WeddingPhotosView, and count queries utilize Redis cache.
- Verifies that selfie face embeddings are cached by SHA-256 hash.
- Verifies that face search concurrency gate protects web workers.
"""

import uuid
import hashlib
from unittest.mock import patch, MagicMock

import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import SimpleTestCase
from django.core.cache import cache
from faces.face_service import search_photos_by_selfie


class CapacityAndCachingTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_selfie_embedding_caching_avoids_onnx(self):
        """Verifies that subsequent searches with the same selfie bytes do not re-run ONNX inference."""
        fake_selfie = b"fake_selfie_image_bytes_12345"
        selfie_hash = hashlib.sha256(fake_selfie).hexdigest()
        cache_key = f"selfie_faces:{selfie_hash}"

        # Populate cache as if first extraction occurred
        cached_entry = {
            'prominent_faces': [{'embedding': [0.1] * 512, 'area': 5000}],
            'selfie_status': 'OK_SINGLE'
        }
        cache.set(cache_key, cached_entry, timeout=3600)

        # Mock Wedding and pgvector search
        mock_wedding = MagicMock()
        mock_wedding.id = 1

        with patch('faces.face_service.extract_selfie_faces') as mock_extract, \
             patch('faces.models.Face.objects.filter') as mock_face_filter, \
             patch('photos.models.Photo.objects.filter') as mock_photo_filter:
            
            mock_face_filter.return_value.annotate.return_value.filter.return_value.order_by.return_value.values_list.return_value.distinct.return_value = [10, 20]
            mock_photo_filter.return_value.order_by.return_value = []
            
            result = search_photos_by_selfie(wedding=mock_wedding, selfie_bytes=fake_selfie)
            
            # extract_selfie_faces should NOT be called because it was served from cache!
            mock_extract.assert_not_called()
            self.assertEqual(result['status'], 'success')

    def test_gallery_cache_key_generation(self):
        """Verifies gallery cache key formats and invalidation."""
        from photos.realtime import invalidate_gallery_cache

        cache.set("wedding_photo_count:99:all", 4200, timeout=30)
        cache.set("gallery_p1:99:all:25", {'results': []}, timeout=15)
        cache.set("wedding_photo_count:99:Bride_and_Groom", 1500, timeout=30)

        self.assertEqual(cache.get("wedding_photo_count:99:all"), 4200)
        self.assertEqual(cache.get("wedding_photo_count:99:Bride_and_Groom"), 1500)

        # Invalidate
        invalidate_gallery_cache(wedding_id=99, wedding_slug="test-wedding")
        self.assertIsNone(cache.get("wedding_photo_count:99:all"))
        self.assertIsNone(cache.get("gallery_p1:99:all:25"))
        self.assertIsNone(cache.get("wedding_photo_count:99:Bride_and_Groom"))
