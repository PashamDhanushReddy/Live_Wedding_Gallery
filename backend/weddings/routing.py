from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/weddings/(?P<slug>[\w-]+)/$', consumers.WeddingGalleryConsumer.as_asgi()),
]
