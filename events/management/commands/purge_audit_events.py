"""Apply the configured EMS audit retention policy."""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from events.models import AuditEvent


class Command(BaseCommand):
    help = "Delete audit events older than EMS_AUDIT_RETENTION_DAYS."

    def handle(self, *args, **options):
        days = settings.EMS_AUDIT_RETENTION_DAYS
        if days < 1:
            raise ValueError("EMS_AUDIT_RETENTION_DAYS must be at least 1.")
        cutoff = timezone.now() - timedelta(days=days)
        deleted, _ = AuditEvent.objects.filter(created_at__lt=cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f"Removed {deleted} expired audit record(s)."))
