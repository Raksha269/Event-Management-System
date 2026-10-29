from celery import shared_task

from .constants import BACKOFF_BASE_SECONDS, BACKOFF_MAX_SECONDS, MAX_ATTEMPTS
from .models import Notification
from .services import deliver_notification, requeue_stale, schedule_due_reminders


def backoff_seconds(attempts: int) -> int:
    """30s, 60s, 120s, 240s ... capped at 1 hour."""
    return min(BACKOFF_BASE_SECONDS * 2 ** max(attempts - 1, 0), BACKOFF_MAX_SECONDS)


@shared_task(bind=True, max_retries=MAX_ATTEMPTS)
def send_notification(self, notification_id):
    result = deliver_notification(notification_id)
    if result == "retry":
        attempts = Notification.objects.values_list("attempts", flat=True).get(pk=notification_id)
        raise self.retry(countdown=backoff_seconds(attempts))
    return result


@shared_task
def run_scheduled_notifications():
    """Celery beat entry point: queue due reminders, then re-dispatch anything stuck."""
    return {"reminders_queued": schedule_due_reminders(), "requeued": requeue_stale()}
