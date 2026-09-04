from django.contrib import admin
from .models import Wedding

@admin.register(Wedding)
class WeddingAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'event_date', 'status', 'created_at')
    search_fields = ('name', 'location')
    list_filter = ('status', 'event_date')
    prepopulated_fields = {'slug': ('name',)}
