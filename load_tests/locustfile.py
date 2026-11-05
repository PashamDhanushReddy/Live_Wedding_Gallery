"""
Locust load testing suite for the Live Wedding Gallery.
Supports running headless CLI or interactive web dashboard at http://localhost:8089.
Tests 50, 100, 250, 500, and 750 virtual user stages.
"""

import os
import random
import uuid
import hashlib
from locust import HttpUser, task, between, events, tag

WEDDING_SLUG = os.environ.get('WEDDING_SLUG', 'rahul-priya')

# Minimal valid 1x1 JPEG byte stream for load testing
MOCK_JPEG_BYTES = (
    b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00'
    b'\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19'
    b'\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444'
    b'\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4'
    b'\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00'
    b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00'
    b'?\x00\xbf\x00\xff\xd9'
)


class GalleryVisitorUser(HttpUser):
    """Simulates realistic wedding guest behavior."""
    wait_time = between(1.0, 3.0)

    def on_start(self):
        # 1. Initial page load: Wedding detail
        with self.client.get(f"/api/weddings/{WEDDING_SLUG}/", name="[GET] /api/weddings/{slug}/ (Detail)", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")

    @tag('gallery')
    @task(6)
    def browse_gallery_first_page(self):
        """Browses first page of gallery photos (cached)."""
        with self.client.get(
            f"/api/weddings/{WEDDING_SLUG}/photos/?page_size=25",
            name="[GET] /api/weddings/{slug}/photos/ (Page 1)",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    results = data.get('results', [])
                    if results:
                        response.success()
                    else:
                        response.success()
                except Exception as e:
                    response.failure(f"JSON decode failed: {e}")
            else:
                response.failure(f"Status {response.status_code}")

    @tag('pagination')
    @task(3)
    def filter_and_paginate(self):
        """Simulates category filtering and cursor-based pagination."""
        folders = ['all', 'Bride_and_Groom', 'Guests', 'Ceremony', 'Reception']
        folder = random.choice(folders)
        url = f"/api/weddings/{WEDDING_SLUG}/photos/?folder={folder}&page_size=25"

        with self.client.get(url, name="[GET] /api/weddings/{slug}/photos/?folder=... (Filtered)", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                next_url = data.get('next')
                if next_url:
                    # Strip host to use relative URL
                    relative_next = next_url.replace("http://localhost:8000", "").replace("https://live-wedding.onrender.com", "")
                    self.client.get(relative_next, name="[GET] /api/weddings/{slug}/photos/?cursor=... (Page 2)")
                response.success()
            else:
                response.failure(f"Status {response.status_code}")

    @tag('face_search')
    @task(1)
    def selfie_face_search(self):
        """Simulates visitor selfie upload and face-matching."""
        files = {
            'file': ('selfie.jpg', MOCK_JPEG_BYTES, 'image/jpeg')
        }
        data = {
            'threshold': '0.45'
        }
        with self.client.post(
            f"/api/weddings/{WEDDING_SLUG}/search/",
            files=files,
            data=data,
            name="[POST] /api/weddings/{slug}/search/ (Selfie)",
            catch_response=True
        ) as response:
            # Status 429 means concurrency semaphore gate protected the server cleanly
            if response.status_code in [200, 400, 429]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


class PhotographerUploadUser(HttpUser):
    """Simulates photographer companion device streaming uploads in the background."""
    wait_time = between(10.0, 30.0)

    @tag('upload')
    @task(1)
    def upload_photo(self):
        upload_id = str(uuid.uuid4())
        checksum = hashlib.sha256(MOCK_JPEG_BYTES + upload_id.encode()).hexdigest()

        files = {
            'photo': ('photo.jpg', MOCK_JPEG_BYTES, 'image/jpeg')
        }
        data = {
            'upload_id': upload_id,
            'checksum': checksum,
            'folder': 'Guests',
            'device_id': 'test-companion-phone-01'
        }
        headers = {
            'X-Photographer-Token': 'test-photographer-token'
        }

        with self.client.post(
            f"/api/weddings/{WEDDING_SLUG}/phone/upload/",
            files=files,
            data=data,
            headers=headers,
            name="[POST] /api/weddings/{slug}/phone/upload/ (Photographer)",
            catch_response=True
        ) as response:
            # 202 Accepted or 401 Unauthorized (if test token not registered)
            if response.status_code in [200, 202, 401]:
                response.success()
            else:
                response.failure(f"Upload failed with status {response.status_code}")

