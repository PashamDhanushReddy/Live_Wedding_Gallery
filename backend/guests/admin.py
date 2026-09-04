from django.contrib import admin
from .models import Guest, PhotoFace

@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'wedding', 'consent_given', 'created_at')
    list_filter = ('wedding', 'consent_given')
    readonly_fields = ('session_id',)

@admin.register(PhotoFace)
class PhotoFaceAdmin(admin.ModelAdmin):
    list_display = ('id', 'photo', 'guest', 'confidence', 'created_at')
    list_filter = ('guest__wedding',)
    readonly_fields = ('photo', 'guest', 'confidence')
