from django.db import models

class Wedding(models.Model):
    slug = models.SlugField(unique=True, max_length=100)
    bride_name = models.CharField(max_length=100)
    groom_name = models.CharField(max_length=100)
    wedding_title = models.CharField(max_length=200, blank=True)
    wedding_date = models.DateField()
    venue = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    cover_image = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.bride_name} & {self.groom_name}"
