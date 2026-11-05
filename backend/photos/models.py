import uuid
from django.db import models
from weddings.models import Wedding

class Photo(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    wedding = models.ForeignKey(Wedding, on_delete=models.CASCADE, related_name='photos')
    original_filename = models.CharField(max_length=255)
    cloudinary_public_id = models.CharField(max_length=255, blank=True, null=True)
    cloudinary_url = models.URLField(max_length=500, blank=True, null=True)
    secure_url = models.URLField(max_length=500, blank=True, null=True)
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)  # in bytes
    format = models.CharField(max_length=20, blank=True, null=True)
    resource_type = models.CharField(max_length=20, default='image')
    captured_at = models.DateTimeField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processing_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    upload_status = models.CharField(max_length=20, default='PENDING')
    thumbnail_url = models.URLField(max_length=500, blank=True, null=True)
    folder = models.CharField(max_length=100, default='Uncategorized')
    ai_category = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    checksum = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['wedding', 'checksum']),
            models.Index(fields=['wedding', 'processing_status']),
            models.Index(fields=['wedding', 'processing_status', '-created_at', '-id']),
            models.Index(fields=['wedding', 'folder', 'processing_status', '-created_at', '-id']),
            models.Index(fields=['wedding', 'ai_category', 'processing_status', '-created_at', '-id']),
            models.Index(fields=['wedding', 'ai_category', '-created_at']),
            models.Index(fields=['wedding', '-created_at', '-id']),
            models.Index(fields=['wedding', 'processing_status', '-created_at']),
            models.Index(fields=['wedding', 'folder', '-created_at']),
            models.Index(fields=['wedding', '-created_at']),
            models.Index(fields=['wedding', '-uploaded_at']),
        ]

    def __str__(self):
        return f"Photo {self.id} for {self.wedding.slug}"

    @property
    def preview_url(self):
        """Dynamic 1200px limit preview delivered straight from Cloudinary CDN."""
        if self.cloudinary_public_id:
            from .cloudinary_service import get_preview_url
            return get_preview_url(self.cloudinary_public_id, self.format)
        return self.secure_url or self.cloudinary_url

    @property
    def large_preview_url(self):
        """Dynamic 2000px limit large preview delivered straight from Cloudinary CDN."""
        if self.cloudinary_public_id:
            from .cloudinary_service import get_large_preview_url
            return get_large_preview_url(self.cloudinary_public_id, self.format)
        return self.secure_url or self.cloudinary_url

    @property
    def download_url(self):
        """Direct original-quality download from Cloudinary CDN with attachment filename."""
        if self.cloudinary_public_id:
            from .cloudinary_service import get_download_url
            return get_download_url(self.cloudinary_public_id, self.format, self.original_filename)
        return self.secure_url or self.cloudinary_url

class CameraConnection(models.Model):
    STATUS_CHOICES = [
        ('CONNECTED', 'Connected'),
        ('CONNECTING', 'Connecting'),
        ('DISCONNECTED', 'Disconnected'),
    ]

    wedding = models.ForeignKey(Wedding, on_delete=models.CASCADE, related_name='camera_connections')
    host = models.CharField(max_length=255)
    port = models.IntegerField(default=21)
    username = models.CharField(max_length=100)
    remote_directory = models.CharField(max_length=255, default='/DCIM/')
    active_folder = models.CharField(max_length=100, default='Uncategorized')
    connection_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DISCONNECTED')
    last_connected = models.DateTimeField(null=True, blank=True)
    last_photo_received = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Camera {self.username} for {self.wedding.slug} - {self.connection_status}"

class Transfer(models.Model):
    STATUS_CHOICES = [
        ('UPLOADING', 'Uploading'),
        ('UPLOADED', 'Uploaded'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    camera = models.ForeignKey(CameraConnection, on_delete=models.CASCADE, related_name='transfers')
    photo = models.ForeignKey(Photo, on_delete=models.SET_NULL, null=True, blank=True, related_name='transfers')
    filename = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UPLOADING')
    progress = models.IntegerField(default=0) # 0 to 100
    error_message = models.TextField(blank=True, null=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"Transfer {self.filename} - {self.status}"

class PhoneDevice(models.Model):
    STATUS_CHOICES = [
        ('RUNNING', 'Running'),
        ('STOPPED', 'Stopped'),
    ]

    wedding = models.ForeignKey(Wedding, on_delete=models.CASCADE, related_name='phone_devices')
    device_id = models.CharField(max_length=255)
    local_ip = models.CharField(max_length=100, blank=True, null=True)
    storage_usage_mb = models.FloatField(default=0.0)
    ftp_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='STOPPED')
    queue_waiting = models.IntegerField(default=0)
    queue_failed = models.IntegerField(default=0)
    last_seen = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('wedding', 'device_id')

    def __str__(self):
        return f"Phone {self.device_id} for {self.wedding.slug} - {self.ftp_status}"

class IngestionJob(models.Model):
    STATUS_CHOICES = [
        ('RECEIVED', 'Received'),
        ('QUEUED', 'Queued'),
        ('UPLOADING', 'Uploading'),
        ('CLOUDINARY_COMPLETED', 'Cloudinary Completed'),
        ('DB_REGISTERED', 'DB Registered'),
        ('FACE_PROCESSING', 'Face Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('DEAD_LETTER', 'Dead Letter'),
    ]

    job_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    upload_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    wedding = models.ForeignKey(Wedding, on_delete=models.CASCADE, related_name='ingestion_jobs')
    device = models.ForeignKey(PhoneDevice, on_delete=models.SET_NULL, null=True, blank=True, related_name='ingestion_jobs')
    photo = models.ForeignKey(Photo, on_delete=models.SET_NULL, null=True, blank=True, related_name='ingestion_jobs')
    
    original_filename = models.CharField(max_length=255)
    staging_path = models.CharField(max_length=500, blank=True, null=True)
    folder = models.CharField(max_length=100, default='Uncategorized')
    checksum = models.CharField(max_length=64, db_index=True)
    file_size = models.BigIntegerField(default=0)
    mime_type = models.CharField(max_length=100, default='image/jpeg')
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='RECEIVED', db_index=True)
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=5)
    
    # Checkpoint recovery data across crashes or network retries
    cloudinary_public_id = models.CharField(max_length=255, blank=True, null=True)
    cloudinary_url = models.URLField(max_length=500, blank=True, null=True)
    secure_url = models.URLField(max_length=500, blank=True, null=True)
    image_width = models.IntegerField(null=True, blank=True)
    image_height = models.IntegerField(null=True, blank=True)
    format = models.CharField(max_length=20, blank=True, null=True)
    resource_type = models.CharField(max_length=20, default='image')
    
    last_error = models.TextField(blank=True, null=True)
    dead_letter_reason = models.TextField(blank=True, null=True)
    
    received_at = models.DateTimeField(auto_now_add=True)
    queued_at = models.DateTimeField(null=True, blank=True)
    uploading_at = models.DateTimeField(null=True, blank=True)
    cloudinary_completed_at = models.DateTimeField(null=True, blank=True)
    db_registered_at = models.DateTimeField(null=True, blank=True)
    face_processing_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-received_at']
        indexes = [
            models.Index(fields=['wedding', 'status']),
            models.Index(fields=['wedding', 'checksum']),
            models.Index(fields=['status', 'next_retry_at']),
            models.Index(fields=['wedding', 'upload_id']),
            models.Index(fields=['wedding', '-received_at']),
        ]

    def __str__(self):
        return f"IngestionJob {self.job_id} ({self.original_filename}) - {self.status}"
