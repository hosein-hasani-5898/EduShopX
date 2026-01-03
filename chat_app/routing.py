from django.urls import re_path
from chat_app import consumers

websocket_urlpatterns = [
    re_path(r"ws/support/(?P<room_id>\w+)/$", consumers.SupportChatConsumer.as_asgi()),
]

