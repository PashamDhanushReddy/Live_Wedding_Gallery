from django.urls import path
from .views import (
    WeddingListCreateView,
    WeddingDetailView,
    WeddingPhotosView,
    PhotoSyncView,
    FaceSearchView,
    PhotographerLoginView,
    SetReferenceFaceView
)
from photos.views import PhotoDownloadView

urlpatterns = [
    path('', WeddingListCreateView.as_view(), name='wedding-list-create'),
    path('<slug:slug>/', WeddingDetailView.as_view(), name='wedding-detail'),
    path('<slug:slug>/login/', PhotographerLoginView.as_view(), name='photographer-login'),
    path('<slug:slug>/photos/', WeddingPhotosView.as_view(), name='wedding-photos'),
    path('<slug:slug>/photos/<int:pk>/download/', PhotoDownloadView.as_view(), name='wedding-photo-download'),
    path('<slug:slug>/sync/', PhotoSyncView.as_view(), name='wedding-sync'),
    path('<slug:slug>/search/', FaceSearchView.as_view(), name='wedding-search'),
    path('<slug:slug>/set_reference/', SetReferenceFaceView.as_view(), name='wedding-set-reference'),
]
