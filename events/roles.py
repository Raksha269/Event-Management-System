"""Role names used by account profiles and role-based permissions."""
from django.db import models


class Role(models.TextChoices):
    ATTENDEE = "attendee", "Attendee"
    ORGANIZER = "organizer", "Organizer"
    ADMINISTRATOR = "administrator", "Administrator"


DEFAULT_ROLE = Role.ATTENDEE
