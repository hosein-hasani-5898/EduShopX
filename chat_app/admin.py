from django.contrib import admin
from chat_app.models import ChatRoom, Message


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['id' ,'user', 'active', 'created_at']
    list_per_page =15


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id' ,'room', 'sender', 'timestamp']
    list_per_page =5


