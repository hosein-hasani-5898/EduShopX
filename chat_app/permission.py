from channels.db import database_sync_to_async
from chat_app.models import ChatRoom

from channels.db import database_sync_to_async
from chat_app.models import ChatRoom

@database_sync_to_async
def user_can_join(room_id, user):
    """
    Check whether a user is allowed to join a chat room.

    Admin users can join any active room. Regular users
    can only join rooms they own that are active.
    """
    if user.is_staff:
        return ChatRoom.objects.filter(id=room_id, active=True).exists()

    return ChatRoom.objects.filter(
        id=room_id,
        user=user,
        active=True
    ).exists()




