from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import Student, Teacher


@receiver(post_delete, sender=[Student, Teacher])
def delete_user_on_profile_delete(sender, instance, **kwargs):
    """
    Deletes the associated User when a Student or Teacher profile is deleted.
    """
    if instance.user:
        instance.user.delete()

