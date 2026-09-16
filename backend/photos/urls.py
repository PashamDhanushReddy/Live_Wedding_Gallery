from django.urls import path
from .views import CameraConnectView, CameraDisconnectView, CameraFolderView, TransferListView, PhotographerStatsView, ManualUploadView, PhoneAuthView, PhoneSyncView, PhoneUploadView

urlpatterns = [
    path('camera/connect/', CameraConnectView.as_view(), name='camera-connect'),
    path('camera/disconnect/', CameraDisconnectView.as_view(), name='camera-disconnect'),
    path('camera/folder/', CameraFolderView.as_view(), name='camera-folder'),
    path('upload/', ManualUploadView.as_view(), name='manual-upload'),
    path('transfers/', TransferListView.as_view(), name='transfer-list'),
    path('stats/', PhotographerStatsView.as_view(), name='photographer-stats'),
    path('phone/auth/', PhoneAuthView.as_view(), name='phone-auth'),
    path('phone/sync/', PhoneSyncView.as_view(), name='phone-sync'),
    path('phone/upload/', PhoneUploadView.as_view(), name='phone-upload'),
]
