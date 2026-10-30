"""Public API for other modules:

    from events.notifications.services import notify_registration_confirmed, cancel_reminders

    notify_registration_confirmed(registration.pk)   # after payment succeeds
    cancel_reminders(registration.pk)                # when a registration is cancelled

Neither call ever raises: a notification problem must not break registration/payment."""
import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from . import adapters
from .constants import (MAX_ATTEMPTS, REG_CONFIRMED, REMINDER_2H_WINDOW, REMINDER_48H_WINDOW,
                        REMINDER_TYPES, STALE_QUEUED_AFTER, NotificationStatus, NotificationType)
from .email_service import EmailSendError, get_backend
from .models import Notification
from .rendering import render_notification

logger = logging.getLogger(__name__)


def _key(ntype, registration_id):
    return f"{ntype}:{registration_id}"


def _create_once(ntype, data):
    """Idempotent: returns (notification, created). A repeat call never creates a second email."""
    with transaction.atomic():
        return Notification.objects.get_or_create(
            idempotency_key=_key(ntype, data.registration_id),
            defaults={"notification_type": ntype, "registration_id": data.registration_id,
                      "recipient_email": data.attendee_email},
        )


def dispatch(notification_id):
    """Hand to Celery. If the broker is down the row stays 'queued' and the periodic sweep retries."""
    try:
        from .tasks import send_notification
        send_notification.delay(notification_id)
    except Exception:
        logger.exception("Could not enqueue notification %s", notification_id)


def notify_registration_confirmed(registration_id):
    try:
        data = adapters.load_registration_data(registration_id)
        if data is None or data.status != REG_CONFIRMED:
            return None
        notification, created = _create_once(NotificationType.CONFIRMATION, data)
        if created:
            transaction.on_commit(lambda: dispatch(notification.pk))  # only after the DB commit
        return notification
    except Exception:
        logger.exception("notify_registration_confirmed failed for %s", registration_id)
        return None


def cancel_reminders(registration_id):
    try:
        return Notification.objects.filter(
            registration_id=registration_id, status=NotificationStatus.QUEUED,
            notification_type__in=REMINDER_TYPES,
        ).update(status=NotificationStatus.CANCELLED, error_category="registration_cancelled")
    except Exception:
        logger.exception("cancel_reminders failed for %s", registration_id)
        return 0


def deliver_notification(notification_id):
    """Send one notification. Returns 'sent' | 'retry' | 'failed' | 'skipped'."""
    with transaction.atomic():
        n = Notification.objects.select_for_update().get(pk=notification_id)
        if n.status != NotificationStatus.QUEUED:
            return "skipped"                       # already sent/failed/cancelled: no duplicates

        data = adapters.load_registration_data(n.registration_id)
        now = timezone.now()
        reason = None
        if data is None or data.status != REG_CONFIRMED:
            reason = "registration_not_active"
        elif data.event_cancelled:
            reason = "event_cancelled"
        elif n.notification_type in REMINDER_TYPES and data.event_starts_at <= now:
            reason = "event_started"
        if reason:                                  # state changed since queueing
            n.status, n.error_category = NotificationStatus.CANCELLED, reason
            n.save()
            return "skipped"

        n.attempts += 1
        try:
            subject, text, html = render_notification(n.notification_type, data)
            message_id = get_backend().send(to=n.recipient_email, subject=subject,
                                            text_body=text, html_body=html)
        except EmailSendError as exc:
            n.error_category = exc.category
            retryable = exc.transient and n.attempts < MAX_ATTEMPTS
        except Exception:
            logger.exception("Unexpected error sending notification %s", n.pk)
            n.error_category = "unexpected_error"
            retryable = n.attempts < MAX_ATTEMPTS
        else:
            n.status, n.provider_message_id, n.sent_at = NotificationStatus.SENT, message_id, now
            n.error_category = ""
            n.save()
            return "sent"

        if retryable:
            n.save()
            return "retry"
        n.status = NotificationStatus.FAILED
        n.save()
        return "failed"


def schedule_due_reminders(now=None):
    """Called by Celery beat every few minutes. Returns the number of reminders queued."""
    now = now or timezone.now()
    queued = 0
    for rid in adapters.upcoming_confirmed_registration_ids(now, now + REMINDER_48H_WINDOW):
        data = adapters.load_registration_data(rid)
        if data is None:
            continue
        until_start = data.event_starts_at - now
        if until_start <= REMINDER_2H_WINDOW:
            ntype = NotificationType.REMINDER_2H
        else:
            ntype = NotificationType.REMINDER_48H
            if data.confirmed_at and data.confirmed_at > data.event_starts_at - REMINDER_48H_WINDOW:
                continue            # registered inside the 48h window: confirmation email is enough
        try:
            notification, created = _create_once(ntype, data)
        except Exception:
            logger.exception("Could not create reminder for registration %s", rid)
            continue
        if created:
            dispatch(notification.pk)
            queued += 1
    return queued


def requeue_stale(now=None):
    """Safety net: re-dispatch rows stuck in 'queued' (e.g. broker was down)."""
    now = now or timezone.now()
    ids = Notification.objects.filter(
        status=NotificationStatus.QUEUED, updated_at__lt=now - STALE_QUEUED_AFTER,
    ).values_list("pk", flat=True)
    for pk in list(ids):
        dispatch(pk)
    return len(ids)
