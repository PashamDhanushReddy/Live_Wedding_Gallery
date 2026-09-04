from django.contrib import admin
from .models import Photo

@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ('id', 'wedding', 'original_filename', 'status', 'is_published', 'cloudinary_account', 'created_at')
    search_fields = ('original_filename', 'sha256')
    list_filter = ('status', 'is_published', 'cloudinary_account', 'wedding')
    readonly_fields = ('sha256', 'file_size', 'width', 'height', 'cloudinary_url', 'thumbnail_url', 'display_url')
