from rest_framework import serializers
from .models import Photo, CameraConnection, Transfer, IngestionJob
from .cloudinary_service import get_thumbnail_url, get_preview_url, get_large_preview_url, get_download_url

class PhotoSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()
    preview_url = serializers.SerializerMethodField()
    large_preview_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Photo
        fields = [
            'id', 'wedding', 'original_filename',
            'cloudinary_public_id', 'cloudinary_url', 'secure_url',
            'thumbnail_url', 'preview_url', 'large_preview_url', 'download_url',
            'width', 'height', 'file_size', 'format', 'resource_type',
            'folder', 'checksum', 'processing_status', 'captured_at', 'created_at'
        ]

    def get_thumbnail_url(self, obj):
        if obj.cloudinary_public_id:
            return get_thumbnail_url(obj.cloudinary_public_id, obj.format)
        return obj.thumbnail_url or obj.secure_url or obj.cloudinary_url

    def get_preview_url(self, obj):
        if obj.cloudinary_public_id:
            return get_preview_url(obj.cloudinary_public_id, obj.format)
        return obj.secure_url or obj.cloudinary_url

    def get_large_preview_url(self, obj):
        if obj.cloudinary_public_id:
            return get_large_preview_url(obj.cloudinary_public_id, obj.format)
        return obj.secure_url or obj.cloudinary_url

    def get_download_url(self, obj):
        if obj.cloudinary_public_id:
            return get_download_url(obj.cloudinary_public_id, obj.format, obj.original_filename)
        return obj.secure_url or obj.cloudinary_url

class GalleryPhotoSerializer(serializers.ModelSerializer):
    """
    High-performance, minimal payload serializer for public gallery display.
    Excludes internal checksums, staging paths, and uncompressed master URLs.
    Includes only responsive dimensions, folder/category, and Cloudinary CDN URLs.
    """
    thumbnail_url = serializers.SerializerMethodField()
    preview_url = serializers.SerializerMethodField()
    large_preview_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Photo
        fields = [
            'id',
            'thumbnail_url',
            'preview_url',
            'large_preview_url',
            'download_url',
            'width',
            'height',
            'folder',
            'captured_at',
            'created_at'
        ]

    def get_thumbnail_url(self, obj):
        if obj.cloudinary_public_id:
            return get_thumbnail_url(obj.cloudinary_public_id, obj.format)
        return obj.thumbnail_url or obj.secure_url

    def get_preview_url(self, obj):
        if obj.cloudinary_public_id:
            return get_preview_url(obj.cloudinary_public_id, obj.format)
        return obj.secure_url or obj.cloudinary_url

    def get_large_preview_url(self, obj):
        if obj.cloudinary_public_id:
            return get_large_preview_url(obj.cloudinary_public_id, obj.format)
        return obj.secure_url or obj.cloudinary_url

    def get_download_url(self, obj):
        if obj.cloudinary_public_id:
            return get_download_url(obj.cloudinary_public_id, obj.format, obj.original_filename)
        return obj.secure_url or obj.cloudinary_url

class CameraConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CameraConnection
        fields = '__all__'

class TransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transfer
        fields = '__all__'

class IngestionJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = IngestionJob
        fields = [
            'job_id', 'upload_id', 'wedding', 'device', 'photo',
            'original_filename', 'folder', 'checksum', 'file_size', 'mime_type',
            'status', 'attempts', 'max_attempts',
            'cloudinary_public_id', 'secure_url', 'image_width', 'image_height',
            'format', 'resource_type',
            'last_error', 'dead_letter_reason',
            'received_at', 'queued_at', 'uploading_at', 'cloudinary_completed_at',
            'db_registered_at', 'face_processing_at', 'completed_at', 'failed_at',
            'next_retry_at', 'updated_at'
        ]
        read_only_fields = fields
