from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("idempotency_key", "recipient_email", "status", "attempts", "sent_at")
    list_filter = ("status", "notification_type")
    search_fields = ("recipient_email", "idempotency_key")
