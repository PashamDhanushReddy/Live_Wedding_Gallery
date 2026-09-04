from django.db import models
from weddings.models import Wedding
from photos.models import Photo
import uuid
from django.utils import timezone
from datetime import timedelta

def default_expiration():
    return timezone.now() + timedelta(days=30)

class Guest(models.Model):
    wedding = models.ForeignKey(Wedding, on_delete=models.CASCADE, related_name='guests')
    session_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    consent_given = models.BooleanField(default=False)
    consent_timestamp = models.DateTimeField(null=True, blank=True)
    
    # Store embedding as JSON array of floats
    face_embedding = models.JSONField(null=True, blank=True) 
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_expiration)

    def __str__(self):
        return f"Guest {str(self.session_id)[:8]} ({self.wedding.name})"

class PhotoFace(models.Model):
    photo = models.ForeignKey(Photo, on_delete=models.CASCADE, related_name='faces')
    guest = models.ForeignKey(Guest, on_delete=models.CASCADE, related_name='matched_photos')
    confidence = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (('photo', 'guest'),)
        indexes = [
            models.Index(fields=['guest', 'confidence']),
        ]

    def __str__(self):
        return f"Match: {self.photo.id} - Guest {str(self.guest.session_id)[:8]} ({self.confidence:.2f})"
