import json
from channels.generic.websocket import AsyncWebsocketConsumer

class PhotoConsumer(AsyncWebsocketConsumer):
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
    async def photo_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps(event))

class GuestConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.room_group_name = f'guest_{self.session_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def photo_message(self, event):
        await self.send(text_data=json.dumps(event))
