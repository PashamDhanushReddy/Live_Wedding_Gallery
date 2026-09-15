from django.db import models
from pgvector.django import VectorField
from photos.models import Photo

class Face(models.Model):
    photo = models.ForeignKey(Photo, on_delete=models.CASCADE, related_name='faces')
    embedding = VectorField(dimensions=512) # Assuming 512-dim embedding for InsightFace
    x = models.FloatField()
    y = models.FloatField()
    width = models.FloatField()
    height = models.FloatField()
    detection_confidence = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Face {self.id} for Photo {self.photo.id}"
