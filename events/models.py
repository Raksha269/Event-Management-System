from decimal import Decimal
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

try:
    from accounts.roles import DEFAULT_ROLE, Role
except ImportError:
    try:
        from RBAC.accounts.roles import DEFAULT_ROLE, Role
    except ImportError:
        class Role(models.TextChoices):
            ATTENDEE = "attendee", "Attendee"
            ORGANIZER = "organizer", "Organizer"
            ADMINISTRATOR = "administrator", "Administrator"

        DEFAULT_ROLE = Role.ATTENDEE


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=DEFAULT_ROLE,
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


# Attach dynamic role properties to standard User model for seamless RBAC integration
User = get_user_model()


def _get_user_role(self):
    if hasattr(self, "_role"):
        return self._role
    profile = getattr(self, "profile", None)
    if profile is not None:
        return getattr(profile, "role", Role.ATTENDEE)
    if getattr(self, "is_superuser", False):
        return Role.ADMINISTRATOR
    return Role.ATTENDEE


def _set_user_role(self, value):
    self._role = value
    profile = getattr(self, "profile", None)
    if profile is not None:
        profile.role = value
        if profile.pk:
            profile.save(update_fields=["role"])
    else:
        if getattr(self, "pk", None):
            try:
                UserProfile.objects.create(
                    user=self,
                    role=value,
                    email_verified=True,
                )
            except Exception:
                pass


if not hasattr(User, "role"):
    User.role = property(_get_user_role, _set_user_role)

if not hasattr(User, "is_organizer"):
    User.is_organizer = property(
        lambda self: getattr(self, "role", None) == Role.ORGANIZER or self.is_superuser
    )

if not hasattr(User, "is_attendee"):
    User.is_attendee = property(
        lambda self: getattr(self, "role", None) == Role.ATTENDEE
    )

if not hasattr(User, "is_administrator"):
    User.is_administrator = property(
        lambda self: getattr(self, "role", None) == Role.ADMINISTRATOR or self.is_superuser
    )


class Event(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"
        UNPUBLISHED = "UNPUBLISHED", "Unpublished"
        CANCELLED = "CANCELLED", "Cancelled"

    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organized_events",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=200, blank=True)
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True, default="General")
    date = models.DateTimeField()
    venue = models.CharField(max_length=200)
    ticket_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    capacity = models.PositiveIntegerField(default=100)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def save(self, *args, **kwargs):
        # Keep title and name synchronized for interoperability
        if self.title and not self.name:
            self.name = self.title
        elif self.name and not self.title:
            self.title = self.name
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title or self.name

    @property
    def event_title(self):
        return self.title or self.name

    @property
    def starts_at(self):
        return self.date

    @starts_at.setter
    def starts_at(self, value):
        self.date = value

    @property
    def is_published(self):
        return self.status == self.Status.PUBLISHED

    def publish(self):
        """Validate required details and publish the event (EMS-F-012)."""
        if not (self.title or self.name):
            raise ValueError("Event title is required for publication.")
        if not self.venue:
            raise ValueError("Event venue is required for publication.")
        if not self.date:
            raise ValueError("Event date is required for publication.")
        if self.capacity <= 0:
            raise ValueError("Event capacity must be greater than zero.")
        self.status = self.Status.PUBLISHED
        self.save(update_fields=["status"])

    def unpublish(self):
        """Unpublish the event, removing it from public visibility (EMS-F-012)."""
        self.status = self.Status.UNPUBLISHED
        self.save(update_fields=["status"])

    def can_be_edited(self):
        """Event can be edited prior to event start date (EMS-F-011)."""
        if not self.date:
            return True
        return timezone.now() < self.date

    @property
    def registered_attendees_count(self):
        """Total quantity of active registrations for this event."""
        manager = getattr(self, "registrations", None) or getattr(
            self, "registration_set", None
        )
        if manager is None:
            return 0
        total = manager.exclude(
            status=Registration.Status.CANCELLED
        ).aggregate(total=models.Sum("quantity"))["total"]
        return total or 0

    @property
    def remaining_capacity(self):
        """Available registration capacity."""
        return max(0, self.capacity - self.registered_attendees_count)

    @property
    def is_sold_out(self):
        return self.remaining_capacity <= 0


class TicketType(models.Model):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="ticket_types",
    )
    name = models.CharField(max_length=100)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    quantity_limit = models.PositiveIntegerField(default=0)
    sold_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("event", "name")

    def __str__(self):
        return f"{self.event.event_title} - {self.name}"

    @property
    def available_quantity(self):
        active_count = (
            self.registrations.exclude(
                status=Registration.Status.CANCELLED
            ).aggregate(total=models.Sum("quantity"))["total"]
            or 0
        )
        used = max(self.sold_count, active_count)
        return max(0, self.quantity_limit - used)

    @property
    def is_sold_out(self):
        return self.available_quantity <= 0


class Registration(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.PROTECT,
        related_name="registrations",
    )
    ticket_type = models.ForeignKey(
        TicketType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="registrations",
    )
    quantity = models.PositiveIntegerField(default=1)
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
