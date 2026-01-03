from django.db.models import F
from celery import shared_task
from main.models import ShortLink

@shared_task(queue='tasks')
def click_plus_task(link_id):
    """
    Increment the click count of a ShortLink object by 1.
    """
    link = ShortLink.objects.get(id=link_id)
    link.clicks = F("clicks") + 1
    link.save(update_fields=["clicks"])
    link.refresh_from_db()
