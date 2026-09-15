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
    checksum = models.CharField(max_length=64, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Photo {self.id} for {self.wedding.slug}"
