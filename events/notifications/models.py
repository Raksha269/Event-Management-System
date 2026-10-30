from django.db import models

from .constants import NotificationStatus, NotificationType


class Notification(models.Model):
    """One email to one registration. Stores no card data and no email body."""
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices)
    registration_id = models.PositiveBigIntegerField(db_index=True)  # plain id: no hard link to #5/#6 models
    recipient_email = models.EmailField()
    idempotency_key = models.CharField(max_length=100, unique=True)  # "<type>:<registration_id>"
    status = models.CharField(max_length=12, choices=NotificationStatus.choices,
                              default=NotificationStatus.QUEUED, db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    provider_message_id = models.CharField(max_length=200, blank=True)
    error_category = models.CharField(max_length=50, blank=True)  # safe category, never raw errors
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.idempotency_key} [{self.status}]"
