from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class RegistrationData:
    """Everything the notification module needs to know. Built only by adapters.py."""
    registration_id: int
    status: str
    payment_state: str
    attendee_email: str
    attendee_name: str
    booking_reference: str
    ticket_type: str
    event_title: str
    event_starts_at: datetime          # timezone-aware
    event_timezone: str                # e.g. "Asia/Kolkata"
    event_venue: str
    event_cancelled: bool
    confirmed_at: Optional[datetime]
