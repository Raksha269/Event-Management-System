"""Drop the email-status panel into any registration page:

    {% load notification_tags %}
    {% notification_status registration.pk %}

It shows email status only. Payment/registration status stays in the owner's own
section, so the two are never mixed up."""
from django import template

from events.notifications.constants import NotificationStatus as S, NotificationType as T
from events.notifications.models import Notification

register = template.Library()

MESSAGES = {
    S.QUEUED: ("info", "Confirmation email is being sent."),
    S.SENT: ("success", "Confirmation email was accepted by our email provider. It may take a few minutes to arrive."),
    S.FAILED: ("error", "We couldn't send the confirmation email. Your registration is not affected; your ticket is available on this page."),
    S.CANCELLED: ("info", "No confirmation email will be sent for this registration."),
}


def mask_email(email: str) -> str:
    name, _, domain = email.partition("@")
    return f"{name[:1]}***@{domain}" if domain else ""


@register.inclusion_tag("notifications/_status.html")
def notification_status(registration_id):
    n = Notification.objects.filter(
        registration_id=registration_id, notification_type=T.CONFIRMATION).first()
    if n is None:
        level, text, email = "info", "A confirmation email will be sent once your registration is confirmed.", ""
    else:
        level, text = MESSAGES[n.status]
        email = mask_email(n.recipient_email)
    return {"level": level, "text": text, "email": email}
