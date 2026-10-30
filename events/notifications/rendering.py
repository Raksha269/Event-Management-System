from zoneinfo import ZoneInfo

from django.conf import settings
from django.template.loader import render_to_string

from .constants import NotificationType
from .data import RegistrationData


def render_notification(ntype: str, data: RegistrationData):
    """Returns (subject, text_body, html_body) built from CURRENT event/registration state."""
    local_start = data.event_starts_at.astimezone(ZoneInfo(data.event_timezone))
    ctx = {
        "data": data,
        "starts_at_local": local_start.strftime("%a %d %b %Y, %H:%M"),
        "timezone": data.event_timezone,
        "ticket_url": f"{settings.SITE_URL}/registrations/{data.registration_id}/",
        "support_email": settings.SUPPORT_EMAIL,
    }
    if ntype == NotificationType.CONFIRMATION:
        name, subject = "confirmation", f"Registration confirmed: {data.event_title}"
    else:
        when = "in 48 hours" if ntype == NotificationType.REMINDER_48H else "in 2 hours"
        ctx["when"] = when
        name, subject = "reminder", f"Reminder: {data.event_title} starts {when}"
    text = render_to_string(f"notifications/{name}.txt", ctx)
    html = render_to_string(f"notifications/{name}.html", ctx)
    return subject, text, html
