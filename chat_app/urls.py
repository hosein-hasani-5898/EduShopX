from django.urls import path
from chat_app import views


urlpatterns = [
    path("chat/room/create/", views.ChatRoomUserCreateGenericView.as_view(), name="room-user"),
    path("management/chat/rooms/", views.ChatRoomUserListGenericView.as_view(), name="room-list"),
    path("chat/room/", views.ChatRoomUserGenericView.as_view(), name="my-room"),
    path("chat/room/user_messages/", views.MessageUserGenericView.as_view(), name="message-user"),
    path("management/chat/room/<int:room_pk>/admin_messages/", views.MessageAdminGenericView.as_view(), name="message-admin"),
]

