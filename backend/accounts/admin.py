from django.contrib import admin
from .models import CloudinaryAccount

@admin.register(CloudinaryAccount)
class CloudinaryAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'cloud_name', 'is_active', 'priority', 'used_bytes', 'capacity_bytes', 'last_health_check')
    list_filter = ('is_active',)
    search_fields = ('name', 'cloud_name')
