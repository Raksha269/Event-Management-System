from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from .roles import DEFAULT_ROLE, Role


class User(AbstractUser):
    """Custom user with RBAC roles and login lockout tracking."""

    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=DEFAULT_ROLE,
    )
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(blank=True, null=True)

    @property
    def is_attendee(self):
        return self.role == Role.ATTENDEE

    @property
    def is_organizer(self):
        return self.role == Role.ORGANIZER

    @property
    def is_administrator(self):
        return self.role == Role.ADMINISTRATOR

    @property
    def is_locked(self):
        return (
            self.locked_until is not None
            and self.locked_until > timezone.now()
        )