from datetime import timedelta

from django.db import models


class NotificationType(models.TextChoices):
    CONFIRMATION = "confirmation", "Registration confirmation"
    REMINDER_48H = "reminder_48h", "Reminder 48 hours before"
    REMINDER_2H = "reminder_2h", "Reminder 2 hours before"


REMINDER_TYPES = (NotificationType.REMINDER_48H, NotificationType.REMINDER_2H)


class NotificationStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    SENT = "sent", "Sent"            # accepted by the email provider (NOT 'delivered')
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


MAX_ATTEMPTS = 5
BACKOFF_BASE_SECONDS = 30
BACKOFF_MAX_SECONDS = 3600
STALE_QUEUED_AFTER = timedelta(minutes=10)
REMINDER_48H_WINDOW = timedelta(hours=48)
REMINDER_2H_WINDOW = timedelta(hours=2)

# Shared registration vocabulary (agree with #5/#6 owners)
REG_CONFIRMED = "confirmed"
