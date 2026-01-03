from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from chat_app.models import ChatRoom, Message
from chat_app.permission import user_can_join
from chat_app.serializers import MessageUserCreateSerializer
import logging


logger = logging.getLogger(__name__)


class SupportChatConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for support chat rooms.

    Handles connecting users, receiving messages, and broadcasting
    messages to the room group. Supports closing the chat and
    saving messages to the database.
    """

    async def connect(self):
        """
        Accepts the connection if the user is authenticated and
        allowed to join the room. Adds the user to the channel layer group.
        """
        user = self.scope["user"]

        if not user.is_authenticated:
            await self.close()
            return

        self.room_name = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"chat_{self.room_name}"

        if not await user_can_join(self.room_name, user):
            await self.close()
            return

        try:
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
        except Exception:
            logger.exception("WS connect infra error")
            await self.close()

    async def disconnect(self, close_code):
        """
        Remove the user from the channel layer group when the connection closes.
        """
        if hasattr(self, 'room_group_name') and hasattr(self, 'channel_name') and self.channel_layer:
            try:
                await self.channel_layer.group_discard(
                    self.room_group_name,
                    self.channel_name
                )
            except Exception:
                logger.exception("WS disconnect error")

    async def receive_json(self, content, **kwargs):
        """
        Handle incoming JSON messages from the WebSocket.
        """
        try:
            action = content.get("action")

            if action == "message":
                text = content.get("message")
                if not text:
                    await self.send_json({"error": "bad_payload"})
                    return

                try:
                    message_data = await self.save_message(text)
                except ChatRoom.DoesNotExist:
                    await self.send_json({"error": "permission_denied"})
                    return
                except Exception:
                    logger.exception("DB error while saving message")
                    await self.send_json({"error": "server_error"})
                    return

                try:
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            "type": "chat.message",
                            "message": message_data,
                        }
                    )
                except Exception:
                    logger.exception("Redis / channel layer error")

            elif action == "close_chat":
                try:
                    await self.close_chat()
                except ChatRoom.DoesNotExist:
                    pass
                await self.close()

            else:
                await self.send_json({"error": "invalid_action"})

        except Exception:
            logger.exception("WS receive_json fatal error")
            await self.send_json({"error": "server_error"})

    async def chat_message(self, event):
        """
        Receive a chat message event from the group and forward it to the WebSocket.
        """
        await self.send_json(event["message"])

    @database_sync_to_async
    def save_message(self, text):
        """
        Save a message to the database for the current chat room.
        """
        user = self.scope["user"]

        if user.is_staff:
            room = ChatRoom.objects.get(id=self.room_name, active=True)
        else:
            room = ChatRoom.objects.get(id=self.room_name, active=True, user=user)

        msg = Message.objects.create(room=room, sender=user, content=text)
        return MessageUserCreateSerializer(msg).data

    @database_sync_to_async
    def close_chat(self):
        """
        Deactivate the current chat room.
        """
        room = ChatRoom.objects.get(id=self.room_name)
        room.active = False
        room.save()


