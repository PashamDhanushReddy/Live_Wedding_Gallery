from django.urls import path
from .views import WeddingListCreateView, WeddingDetailView, WeddingPhotosView, PhotoSyncView, FaceSearchView, PhotographerLoginView, SetReferenceFaceView

urlpatterns = [
    path('', WeddingListCreateView.as_view(), name='wedding-list-create'),
    path('<slug:slug>/', WeddingDetailView.as_view(), name='wedding-detail'),
    path('<slug:slug>/login/', PhotographerLoginView.as_view(), name='photographer-login'),
    path('<slug:slug>/photos/', WeddingPhotosView.as_view(), name='wedding-photos'),
    path('<slug:slug>/sync/', PhotoSyncView.as_view(), name='wedding-sync'),
    path('<slug:slug>/search/', FaceSearchView.as_view(), name='wedding-search'),
    path('<slug:slug>/set_reference/', SetReferenceFaceView.as_view(), name='wedding-set-reference'),
]
