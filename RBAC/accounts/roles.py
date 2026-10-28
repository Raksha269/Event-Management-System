"""Single source of truth for role names (EMS-F-005).
Everyone imports from here; never hard-code 'organizer' etc. elsewhere."""
from django.db import models


class Role(models.TextChoices):
    ATTENDEE = "attendee", "Attendee"
    ORGANIZER = "organizer", "Organizer"
    ADMINISTRATOR = "administrator", "Administrator"


DEFAULT_ROLE = Role.ATTENDEE   # public signup ALWAYS gets this
