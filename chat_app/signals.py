from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Message


@receiver([post_save, post_delete], sender=Message)
def invalidate_message_cache(sender, instance, **kwargs):
    room_id = instance.room_id
    room_owner_id = instance.room.user_id

    cache.delete(f"messages:room:{room_id}:user:{room_owner_id}")
    cache.delete(f"chat:rooms:user:{room_owner_id}")


