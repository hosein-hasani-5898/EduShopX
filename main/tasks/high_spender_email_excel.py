from config.celery_config import app
from main.models import Payment
from django.db.models import Sum
import pandas as pd
from django.core.mail import EmailMessage
from account_app.models import User
from config import settings
from celery import shared_task, group
import time

@app.task(queue="tasks", bind=True)
def excel_task(self, threshold):
    """
    Generate an Excel file listing users who spent above a certain threshold.
    """
    users = (
        Payment.objects.filter(status="success")
        .values("user")
        .annotate(total_spent=Sum("amount"))
        .filter(total_spent__gte=threshold)
    )

    data = []
    for u in users:
        user = User.objects.get(id=u['user'])
        data.append({
            "Email": user.email,
            "Username": user.username,
            "Total Spent": u['total_spent'],
        })

    df = pd.DataFrame(data)
    file_path = f"/shared/high_spenders_{self.request.id}.xlsx"
    df.to_excel(file_path, index=False)
    return file_path


@app.task(queue='tasks')
def avg_order_task():
    """
    Calculate the average payment amount across all successful payments.
    """
    total_amount = Payment.objects.filter(status="success").aggregate(total=Sum('amount'))['total'] or 0
    total_orders = Payment.objects.filter(status="success").count()
    time.sleep(25)
    return total_amount / total_orders if total_orders else 0


BATCH_SIZE = 500

@shared_task(queue='tasks', bind=True, max_retries=3)
def send_mass_email_task(self, subject, message):
    """
    Send an email to all users in batches asynchronously.
    """
    users = list(User.objects.values_list("email", flat=True))
    batches = [users[i:i+BATCH_SIZE] for i in range(0, len(users), BATCH_SIZE)]

    job = group(send_email_batch.s(subject, message, batch) for batch in batches)
    result = job.apply_async()
    return result.id


@shared_task(queue='tasks', bind=True, max_retries=3)
def send_email_batch(self, subject, message, emails):
    """
    Send a batch of emails using BCC to the given list of addresses.
    """
    try:
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.EMAIL_HOST_USER,
            to=None,
            bcc=list(emails),
        )
        email.send(fail_silently=False)
        return f"Sent {len(emails)} emails"

    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)


