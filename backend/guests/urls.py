from django.urls import path
from .views import GuestRegisterView, GuestDeleteView

urlpatterns = [
    path('api/weddings/<slug:slug>/guest/register/', GuestRegisterView.as_view(), name='guest-register'),
    path('api/weddings/<slug:slug>/guest/data/<uuid:session_id>/', GuestDeleteView.as_view(), name='guest-delete'),
]
