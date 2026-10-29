"""THE ONLY FILE THAT KNOWS ABOUT THE EVENT/REGISTRATION MODELS.

Today it reads the temporary `standins` app. When issues #4/#5/#6 are merged,
change the imports and the field mapping below - nothing else needs to change."""
from datetime import datetime
from typing import List, Optional

from standins.models import Registration   # <-- swap for the real model

from .data import RegistrationData


def load_registration_data(registration_id: int) -> Optional[RegistrationData]:
    reg = Registration.objects.select_related("event").filter(pk=registration_id).first()
    if reg is None:
        return None
    ev = reg.event
    return RegistrationData(
        registration_id=reg.pk, status=reg.status, payment_state=reg.payment_state,
        attendee_email=reg.attendee_email, attendee_name=reg.attendee_name,
        booking_reference=reg.booking_reference, ticket_type=reg.ticket_type,
        event_title=ev.title, event_starts_at=ev.starts_at, event_timezone=ev.timezone,
        event_venue=ev.venue, event_cancelled=ev.is_cancelled, confirmed_at=reg.confirmed_at,
    )


def upcoming_confirmed_registration_ids(now: datetime, horizon: datetime) -> List[int]:
    """Confirmed registrations for non-cancelled events starting in (now, horizon]."""
    return list(Registration.objects.filter(
        status="confirmed", event__is_cancelled=False,
        event__starts_at__gt=now, event__starts_at__lte=horizon,
    ).values_list("pk", flat=True))
