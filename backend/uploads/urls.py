from django.urls import path
from .views import PhotoUploadView

urlpatterns = [
    path('api/weddings/<slug:slug>/photos/upload/', PhotoUploadView.as_view(), name='photo-upload'),
]
