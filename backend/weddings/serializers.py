from rest_framework import serializers
from .models import Wedding

class WeddingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wedding
        fields = ['slug', 'bride_name', 'groom_name', 'wedding_title', 'wedding_date', 'venue', 'description', 'cover_image', 'is_active']
