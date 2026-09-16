from rest_framework import serializers
from .models import Photo

class PhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photo
        fields = ['id', 'wedding', 'cloudinary_url', 'secure_url', 'width', 'height', 'thumbnail_url', 'folder', 'processing_status', 'captured_at', 'created_at']

from .models import CameraConnection, Transfer

class CameraConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CameraConnection
        fields = '__all__'

class TransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transfer
        fields = '__all__'
