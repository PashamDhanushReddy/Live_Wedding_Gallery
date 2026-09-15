from rest_framework import serializers
from .models import Photo

class PhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photo
        fields = ['id', 'wedding', 'cloudinary_url', 'secure_url', 'width', 'height', 'thumbnail_url', 'processing_status', 'captured_at', 'created_at']
