from django.db import models

class CloudinaryAccount(models.Model):
    name = models.CharField(max_length=255, unique=True)
    cloud_name = models.CharField(max_length=255)
    api_key = models.CharField(max_length=255)
    api_secret = models.CharField(max_length=255)
    capacity_bytes = models.BigIntegerField(default=26843545600)  # 25 GB default
    used_bytes = models.BigIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_health_check = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-priority', 'id']

    def __str__(self):
        return f"{self.name} ({self.cloud_name})"
