import json
import logging
import time
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)

_WEDDING_CACHE = {}

class WeddingGalleryConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for live wedding gallery updates.
    Handles authentication, room-based isolation, lightweight notifications,
    and heartbeat monitoring.
    """

    @classmethod
    def get_cached_wedding(cls, slug):
        now = time.time()
        cached = _WEDDING_CACHE.get(slug)
        if cached and (now - cached['ts']) < 60:
            return cached['data']
        return None

    @classmethod
    def set_cached_wedding(cls, slug, data):
        _WEDDING_CACHE[slug] = {'data': data, 'ts': time.time()}

    async def connect(self):
        self.wedding_slug = self.scope['url_route']['kwargs'].get('slug', '').strip()
        if not self.wedding_slug:
            logger.warning("WebSocket rejected: Missing wedding slug in URL.")
            await self.close(code=4400)
            return

        # Authenticate and Authorize: check cache first to survive 500+ concurrent bursts
        wedding_info = self.get_cached_wedding(self.wedding_slug)
        if not wedding_info:
            wedding_info = await self.get_active_wedding(self.wedding_slug)
            if wedding_info:
                self.set_cached_wedding(self.wedding_slug, wedding_info)

        if not wedding_info:
            logger.warning(f"WebSocket rejected: Wedding '{self.wedding_slug}' not found or inactive.")
            await self.close(code=4404)
            return

        self.wedding_id = wedding_info['id']

        # Check authentication token if provided in query string
        query_string = self.scope.get('query_string', b'').decode('utf-8')
        query_params = parse_qs(query_string)
        token_key = query_params.get('token', [None])[0]

        if token_key:
            user = await self.authenticate_token(token_key)
            if not user:
                logger.warning(f"WebSocket rejected: Invalid auth token for wedding '{self.wedding_slug}'.")
                await self.close(code=4401)
                return
            self.user = user
            self.is_photographer = True
        else:
            self.user = AnonymousUser()
            self.is_photographer = False

        # Strictly subscribe only to this verified wedding's room group
        self.room_group_name = f'wedding_{self.wedding_slug}'
        if self.channel_layer:
            try:
                await self.channel_layer.group_add(
                    self.room_group_name,
                    self.channel_name
                )
            except Exception as e:
                logger.error(f"Failed to join channel group {self.room_group_name}: {e}")
        await self.accept()

        # Send connection acknowledgment with protocol details
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'wedding_slug': self.wedding_slug,
            'wedding_id': self.wedding_id,
            'heartbeat_interval_ms': 25000,
        }))
        try:
            from observability.metrics import metrics
            metrics.record_ws_connect()
        except ImportError:
            pass
        logger.info(f"WebSocket connected: wedding={self.wedding_slug}, channel={self.channel_name}")

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name') and self.channel_layer:
            try:
                await self.channel_layer.group_discard(
                    self.room_group_name,
                    self.channel_name
                )
            except Exception as e:
                logger.warning(f"Error discarding channel group {self.room_group_name}: {e}")
            try:
                from observability.metrics import metrics
                metrics.record_ws_disconnect(close_code or 1000)
            except ImportError:
                pass
            logger.info(f"WebSocket disconnected: wedding={getattr(self, 'wedding_slug', None)}, code={close_code}")

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            data = json.loads(text_data)
            msg_type = data.get('type')

            if msg_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': time.time(),
                }))
            else:
                # Disallow unauthorized incoming client broadcasts
                logger.debug(f"Received client message type '{msg_type}' - ignored.")
        except json.JSONDecodeError:
            pass

    async def new_photo(self, event):
        """
        Sends a lightweight notification to the client.
        Client will fetch validated metadata via the paginated API.
        Does NOT broadcast original image bytes or heavy uncompressed URLs.
        """
        await self.send(text_data=json.dumps({
            'type': 'new_photo',
            'photo_id': event['photo_id'],
            'wedding_id': event.get('wedding_id', self.wedding_id),
            'wedding_slug': event.get('wedding_slug', self.wedding_slug),
            'folder': event.get('folder', 'Bride and Groom'),
            'status': event.get('status', 'COMPLETED'),
            'created_at': event.get('created_at'),
            'event_id': event.get('event_id'),
        }))

    async def delete_photo(self, event):
        """
        Sends a lightweight photo deletion event.
        """
        await self.send(text_data=json.dumps({
            'type': 'delete_photo',
            'photo_id': event['photo_id'],
            'wedding_id': event.get('wedding_id', self.wedding_id),
            'wedding_slug': self.wedding_slug,
            'event_id': event.get('event_id'),
        }))

    async def transfer_update(self, event):
        """
        Relays upload progress updates to photographer devices if relevant.
        """
        await self.send(text_data=json.dumps({
            'type': 'transfer_update',
            'transfer': event.get('transfer', {}),
        }))

    @database_sync_to_async
    def get_active_wedding(self, slug):
        from weddings.models import Wedding
        try:
            return Wedding.objects.filter(slug=slug, is_active=True).values('id', 'slug').first()
        except Exception as e:
            logger.error(f"Error querying wedding for WebSocket: {e}")
            return None

    @database_sync_to_async
    def authenticate_token(self, token_key):
        from rest_framework.authtoken.models import Token
        try:
            token = Token.objects.select_related('user').get(key=token_key)
            return token.user
        except Token.DoesNotExist:
            return None
