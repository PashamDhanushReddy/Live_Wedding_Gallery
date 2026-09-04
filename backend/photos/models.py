from django.db import models
from weddings.models import Wedding
from accounts.models import CloudinaryAccount

class Photo(models.Model):
    STATUS_CHOICES = (
        ('PROCESSING', 'Processing'),
        ('READY', 'Ready'),
        ('HIDDEN', 'Hidden'),
        ('FAILED', 'Failed'),
    )

    wedding = models.ForeignKey(Wedding, on_delete=models.CASCADE, related_name='photos')
    sha256 = models.CharField(max_length=64, db_index=True)
    original_filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    
    # Link to CloudinaryAccount model
    cloudinary_account = models.ForeignKey(CloudinaryAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='photos')
    cloudinary_public_id = models.CharField(max_length=255, null=True, blank=True)
    cloudinary_url = models.URLField(max_length=1000, null=True, blank=True)
    thumbnail_url = models.URLField(max_length=1000, null=True, blank=True)
    display_url = models.URLField(max_length=1000, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PROCESSING')
    is_published = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['wedding']),
            models.Index(fields=['sha256']),
            models.Index(fields=['created_at']),
            models.Index(fields=['cloudinary_account']),
        ]
        unique_together = (('wedding', 'sha256'),)

    def __str__(self):
        return f"{self.wedding.name} - {self.original_filename}"
