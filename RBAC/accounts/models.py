from django.contrib.auth.models import AbstractUser
from django.db import models

from .roles import DEFAULT_ROLE, Role


class User(AbstractUser):
    """Custom user with a role. The Auth teammate (issues #1/#2) can extend
    this same model (email verification, lockout fields) - do not create a
    second user model."""

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=DEFAULT_ROLE)

    @property
    def is_attendee(self):
        return self.role == Role.ATTENDEE

    @property
    def is_organizer(self):
        return self.role == Role.ORGANIZER

    @property
    def is_administrator(self):
        return self.role == Role.ADMINISTRATOR
