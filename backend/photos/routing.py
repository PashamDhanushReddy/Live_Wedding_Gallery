from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/weddings/(?P<slug>[^/]+)/$', consumers.PhotoConsumer.as_asgi()),
    re_path(r'ws/guest_(?P<session_id>[^/]+)/$', consumers.GuestConsumer.as_asgi()),
]
