from django.urls import path
from .views import CameraConnectView, CameraDisconnectView, CameraFolderView, TransferListView, PhotographerStatsView, ManualUploadView

urlpatterns = [
    path('camera/connect/', CameraConnectView.as_view(), name='camera-connect'),
    path('camera/disconnect/', CameraDisconnectView.as_view(), name='camera-disconnect'),
    path('camera/folder/', CameraFolderView.as_view(), name='camera-folder'),
    path('photographer/upload/', ManualUploadView.as_view(), name='manual-upload'),
    path('transfers/', TransferListView.as_view(), name='transfer-list'),
    path('stats/', PhotographerStatsView.as_view(), name='photographer-stats'),
]
