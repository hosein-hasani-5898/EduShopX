from django.shortcuts import get_object_or_404
from django.core.cache import cache
from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from chat_app.models import ChatRoom, Message
from chat_app import serializers



class ChatRoomUserCreateGenericView(generics.CreateAPIView):
    """
    Create a chat room for the authenticated user.

    Each user is allowed only one chat room.
    """
    queryset = ChatRoom.objects.all()
    serializer_class = serializers.ChatRoomCreateUserSerializer
    permission_classes = [permissions.IsAuthenticated, ~permissions.IsAdminUser]

    @swagger_auto_schema(responses={201: serializers.ChatRoomCreateUserSerializer})
    def perform_create(self, serializer):
        """
        Ensure the user does not already have a chat room before saving.
        """
        if ChatRoom.objects.filter(user=self.request.user).exists():
            raise ValidationError('There is already a room for this user.')
        serializer.save()


class ChatRoomUserListGenericView(generics.ListAPIView):
    """
    Admin view to list all chat rooms.
    """
    queryset = ChatRoom.objects.all()
    serializer_class = serializers.ChatRoomCreateUserSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    @swagger_auto_schema(responses={200: serializers.ChatRoomCreateUserSerializer(many=True)})
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ChatRoomUserGenericView(generics.ListAPIView):
    """
    List chat rooms belonging to the current authenticated user.
    """
    serializer_class = serializers.ChatRoomCreateUserSerializer
    permission_classes = [permissions.IsAuthenticated, ~permissions.IsAdminUser]

    def get_queryset(self):

        user = self.request.user
        return ChatRoom.objects.filter(user=user)

    def list(self, request, *args, **kwargs):
        user = request.user
        cache_key = f"chat:rooms:user:{user.id}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

   
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        cache.set(cache_key, data, 120)
        return Response(data)


class MessageUserGenericView(generics.ListCreateAPIView):
    """
    List messages for a user's chat room or create a new message.
    """
    permission_classes = [permissions.IsAuthenticated, ~permissions.IsAdminUser]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return serializers.MessageUserCreateSerializer
        return serializers.MessageUserListSerializer
    
    def get_room(self):
        return get_object_or_404(ChatRoom, user=self.request.user)

    def get_queryset(self):
        room = self.get_room()
        return Message.objects.filter(room=room).select_related('sender')

    def list(self, request, *args, **kwargs):
        user = request.user
        room = self.get_room()

        cache_key = f"messages:room:{room.id}:user:{user.id}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        serializer = self.get_serializer(self.get_queryset(), many=True)
        data = serializer.data

        cache.set(cache_key, data, 120)
        return Response(data)

    @swagger_auto_schema(responses={201: serializers.MessageUserListSerializer})
    def perform_create(self, serializer):
        user = self.request.user
        room = self.get_room()

        instance = serializer.save(room=room, sender=user)

        cache.delete(f"messages:room:{room.id}:user:{user.id}")
        cache.delete(f"chat:rooms:user:{user.id}")

        return instance


class MessageAdminGenericView(generics.ListCreateAPIView):
    """
    Admin view to list messages in any chat room or post messages as admin.
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get_queryset(self):
        room_id = self.kwargs['room_pk']
        return Message.objects.filter(room_id=room_id).select_related('sender')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return serializers.MessageUserCreateSerializer
        return serializers.MessageUserListSerializer

    def list(self, request, *args, **kwargs):
        room_id = self.kwargs['room_pk']
        user = request.user
        cache_key = f"messages:room:{room_id}:user:{user.id}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        cache.set(cache_key, data, 120)
        return Response(data)

    @swagger_auto_schema(responses={201: serializers.MessageUserListSerializer})
    def perform_create(self, serializer):
        room_id = self.kwargs['room_pk']
        room = get_object_or_404(ChatRoom, id=room_id)
        user = self.request.user
        instance = serializer.save(room_id=room_id, sender=user)
        cache.delete(f"messages:room:{room_id}:user:{user.id}")
        cache.delete(f"chat:rooms:user:{user.id}")

        return instance

