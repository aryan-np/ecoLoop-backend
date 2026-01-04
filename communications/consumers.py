import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db.models import Q

from .models import Thread, Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.thread_id = self.scope["url_route"]["kwargs"]["thread_id"]
        self.user = self.scope["user"]

        # Must be logged in
        if not self.user or self.user.is_anonymous:
            await self.close(code=4401)  # unauthorized
            return

        # Must belong to the thread
        allowed = await self._user_in_thread(self.user.id, self.thread_id)
        if not allowed:
            await self.close(code=4403)  # forbidden
            return

        self.group_name = f"thread_{self.thread_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """
        {"type":"message","body":"hello"}
        """
        try:
            payload = json.loads(text_data or "{}")
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
            return

        if payload.get("type") != "message":
            await self.send_error("Invalid message type")
            return

        body = (payload.get("body") or "").strip()
        if not body:
            await self.send_error("Message body cannot be empty")
            return

        try:
            msg_dict = await self._create_message(self.thread_id, self.user.id, body)

            # broadcast to everyone in the thread room
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "chat.message", "message": msg_dict},
            )
        except Exception as e:
            await self.send_error(f"Error creating message: {str(e)}")

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["message"]))

    async def send_error(self, error_message):
        await self.send(
            text_data=json.dumps({"type": "error", "message": error_message})
        )

    @database_sync_to_async
    def _user_in_thread(self, user_id, thread_id):
        return (
            Thread.objects.filter(id=thread_id)
            .filter(Q(user1_id=user_id) | Q(user2_id=user_id))
            .exists()
        )

    @database_sync_to_async
    def _create_message(self, thread_id, sender_id, body):
        thread = Thread.objects.get(id=thread_id)
        msg = Message.objects.create(thread=thread, sender_id=sender_id, content=body)
        thread.save(update_fields=["updated_at"])
        return {
            "type": "message",
            "id": str(msg.id),
            "thread": str(thread_id),
            "sender": str(sender_id),
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
        }
