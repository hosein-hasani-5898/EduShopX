from config.celery_config import app
from celery.schedules import crontab
from chat_app.models import ChatRoom
from celery import shared_task


app.conf.beat_schedule = {
    'delete-old-chatrooms-every-6-hours': {
        'task': 'chat_app.tasks.delete_old_rooms',
        'schedule': crontab(minute='0', hour="0"),
    },
}

@shared_task(
    queue='tasks', bind=True, autoretry_for=(Exception,), 
    retry_backoff=30, retry_kwargs={'max_retries': 3}
)
def delete_old_rooms(self):
    """
    Delete all chat rooms marked as inactive.
    """
    ChatRoom.objects.filter(
        active=False

    ).delete()

