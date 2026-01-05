import logging
from django.core.mail import send_mail
from django.utils.html import strip_tags
from config import settings
from celery import shared_task
from celery.signals import task_failure

logger = logging.getLogger(__name__)


@shared_task(
    queue='tasks',
    bind=True,
    max_retries=5,
    default_retry_delay=10,
    time_limit=30
)
def send_email_task(
    self,
    to,
    subject=None,
    username=None,
    context=None,
    template_name=None
):
    """
    Send a welcome email to a user.

    Retries automatically on failure and logs all errors.
    """
    try:
        logger.info("Starting email task for %s", to)

        html_message = f"<p><b>{username}</b> dear,Registration was successful.</p>"
        plain_message = strip_tags(html_message)
        from_email = settings.EMAIL_HOST_USER

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=from_email,
            recipient_list=[to],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info("Email successfully sent to %s", to)

    except Exception as exc:
        logger.exception("Failed to send email to %s", to)
        raise self.retry(exc=exc)

@shared_task(queue='tasks')
def error_handler_task(task_id, exception=None):
    """
    Handle failed Celery tasks.
    """
    logger.error(
        "Celery task failed | task_id=%s | exception=%s",
        task_id,
        exception
    )

@task_failure.connect(sender=send_email_task)
def handle_send_email_failure(
    sender=None,
    task_id=None,
    exception=None,
    **kwargs
):
    error_handler_task.delay(task_id, str(exception))


