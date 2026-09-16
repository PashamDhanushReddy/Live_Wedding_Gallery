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
    file_size = models.BigIntegerField(null=True, blank=True)
    captured_at = models.DateTimeField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processing_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    upload_status = models.CharField(max_length=20, default='PENDING')
    thumbnail_url = models.URLField(max_length=500, blank=True, null=True)
    folder = models.CharField(max_length=100, default='Uncategorized')
    checksum = models.CharField(max_length=64, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Photo {self.id} for {self.wedding.slug}"

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
