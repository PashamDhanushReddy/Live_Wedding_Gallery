from django.db import models
from pgvector.django import VectorField, HnswIndex
from photos.models import Photo

class Face(models.Model):
    photo = models.ForeignKey(Photo, on_delete=models.CASCADE, related_name='faces')
    embedding = VectorField(dimensions=512) # 512-dim embedding for InsightFace ArcFace
    x = models.FloatField()
    y = models.FloatField()
    width = models.FloatField()
    height = models.FloatField()
    detection_confidence = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            HnswIndex(
                name='faces_face_emb_hnsw_idx',
                fields=['embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_cosine_ops']
            ),
            models.Index(fields=['photo', 'detection_confidence']),
            models.Index(fields=['photo', '-created_at']),
        ]

    def __str__(self):
        return f"Face {self.id} for Photo {self.photo.id}"
