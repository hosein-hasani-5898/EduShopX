from django.db import models
from account_app.models import User

class ChatRoom(models.Model):
    """
    Represents a chat room for a single user.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="user_chats")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat with {self.user.username}"
    
    class Meta:
        verbose_name = "ChatRoom"
        verbose_name_plural = "ChatRooms"


class Message(models.Model):
    """
    Represents a message sent within a chat room.
    """
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message in room id: {self.room.id}"

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
