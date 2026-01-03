from rest_framework import serializers
from chat_app.models import ChatRoom, Message


class MessageUserListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing messages in a chat room.
    """
    sender = serializers.CharField(source='sender.username', read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'content', 'timestamp', 'sender']


class MessageUserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new message in a chat room.
    """

    class Meta:
        model = Message
        fields = ['content']


class ChatRoomCreateUserSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a chat room for a user.
    """
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = ChatRoom
        fields = ['id', 'user', 'active', 'created_at']
        read_only_fields = ['created_at']

