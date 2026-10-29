
# Create your models here.

from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    email_verified = models.BooleanField(default=False)
    verification_token = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        unique=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.email or self.user.username


import uuid

from django.conf import settings
from django.db import models


class Event(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date = models.DateTimeField()
    venue = models.CharField(max_length=200)
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2)
    capacity = models.PositiveIntegerField(default=100)

    def __str__(self):
        return self.name


class Registration(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    event = models.ForeignKey(Event, on_delete=models.PROTECT)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Successful"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    registration = models.OneToOneField(
        Registration,
        on_delete=models.PROTECT,
        related_name="payment",
    )
    transaction_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)


class Ticket(models.Model):
    registration = models.OneToOneField(
        Registration,
        on_delete=models.PROTECT,
        related_name="ticket",
    )
    ticket_code = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    qr_code = models.ImageField(
        upload_to="tickets/qr/",
        blank=True,
    )
    issued_at = models.DateTimeField(auto_now_add=True)


class Refund(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        COMPLETED = "COMPLETED", "Completed"

    payment = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        related_name="refunds",
    )
    reason = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)