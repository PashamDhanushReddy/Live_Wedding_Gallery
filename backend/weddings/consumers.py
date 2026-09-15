import json
from channels.generic.websocket import AsyncWebsocketConsumer

class WeddingGalleryConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.wedding_slug = self.scope['url_route']['kwargs']['slug']
        self.room_group_name = f'wedding_{self.wedding_slug}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from room group
    async def new_photo(self, event):
        photo = event['photo']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'new_photo',
            'photo': photo
        }))
