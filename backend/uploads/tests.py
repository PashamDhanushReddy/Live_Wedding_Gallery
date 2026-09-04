from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from weddings.models import Wedding
from accounts.models import CloudinaryAccount
import io
from PIL import Image

class PhotoUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.wedding = Wedding.objects.create(name="Test Wedding", date="2026-10-10")
        self.account = CloudinaryAccount.objects.create(
            name="Test Account",
            cloud_name="test",
            api_key="123",
            api_secret="abc",
            is_active=True,
            current_capacity_bytes=0
        )
        self.url = reverse('photo-upload', kwargs={'slug': self.wedding.slug})

    def generate_dummy_image(self):
        file = io.BytesIO()
        image = Image.new('RGB', (100, 100), color=(255, 0, 0))
        image.save(file, 'jpeg')
        file.name = 'test.jpg'
        file.seek(0)
        return file

    def test_upload_missing_photo(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Note: Full upload test would require mocking Cloudinary API
    # and FaceRecognitionService to avoid actual network/compute calls in unit tests.
