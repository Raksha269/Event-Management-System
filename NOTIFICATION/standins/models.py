"""TEMPORARY stand-ins for the Event (#4) and Registration (#5/#6) models so the
notification module can be built and tested now. Delete this app when the real
models exist and update notifications/adapters.py instead."""
from django.db import models


class Event(models.Model):
    title = models.CharField(max_length=200)
    starts_at = models.DateTimeField()
    timezone = models.CharField(max_length=64, default="UTC")
    venue = models.CharField(max_length=200, blank=True)
    is_cancelled = models.BooleanField(default=False)


class Registration(models.Model):
    STATUSES = ["pending", "confirmed", "failed", "cancelled", "refunded"]
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    attendee_email = models.EmailField()
    attendee_name = models.CharField(max_length=100, blank=True)
    booking_reference = models.CharField(max_length=20)
    ticket_type = models.CharField(max_length=50, default="General")
    status = models.CharField(max_length=20, default="pending")
    payment_state = models.CharField(max_length=20, default="pending")
    confirmed_at = models.DateTimeField(null=True, blank=True)
