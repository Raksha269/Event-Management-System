"""Translate the event app's models into the notification service data contract."""
from datetime import datetime
from typing import List, Optional

from django.conf import settings
from django.utils import timezone

from events.models import Event, Registration

from .data import RegistrationData


def load_registration_data(registration_id: int) -> Optional[RegistrationData]:
    reg = (
        Registration.objects.select_related("event", "user", "ticket_type")
        .filter(pk=registration_id)
        .first()
    )
    if reg is None:
        return None
    ev = reg.event
    payment = getattr(reg, "payment", None)
    ticket = getattr(reg, "ticket", None)
    return RegistrationData(
        registration_id=reg.pk,
        status=reg.status.lower(),
        payment_state=payment.status.lower() if payment else "pending",
        attendee_email=reg.user.email,
        attendee_name=reg.user.get_full_name() or reg.user.get_username(),
        booking_reference=str(ticket.ticket_code) if ticket else f"REG-{reg.pk}",
        ticket_type=reg.ticket_type.name if reg.ticket_type else "General",
        event_title=ev.event_title,
        event_starts_at=ev.date,
        event_timezone=getattr(
            ev,
            "timezone",
            settings.TIME_ZONE or timezone.get_default_timezone_name(),
        ),
        event_venue=ev.venue,
        event_cancelled=ev.status == Event.Status.CANCELLED,
        confirmed_at=reg.confirmed_at,
    )


def upcoming_confirmed_registration_ids(now: datetime, horizon: datetime) -> List[int]:
    """Confirmed registrations for non-cancelled events starting in (now, horizon]."""
    return list(Registration.objects.filter(
        status=Registration.Status.CONFIRMED,
        event__status=Event.Status.PUBLISHED,
        event__date__gt=now,
        event__date__lte=horizon,
    ).values_list("pk", flat=True))
