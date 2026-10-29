from django.template import Context, Template
from django.test import TestCase

from notifications.constants import NotificationStatus as S, NotificationType as T
from notifications.models import Notification


def render(registration_id):
    return Template("{% load notification_tags %}{% notification_status rid %}").render(
        Context({"rid": registration_id}))


def make(status, rid=1):
    return Notification.objects.create(
        notification_type=T.CONFIRMATION, registration_id=rid, recipient_email="asha@x.com",
        idempotency_key=f"confirmation:{rid}", status=status)


class StatusPanelTests(TestCase):
    def test_no_notification_yet(self):
        self.assertIn("will be sent once", render(1))

    def test_each_status_has_clear_wording(self):
        expected = {S.QUEUED: "being sent", S.SENT: "accepted by our email provider",
                    S.FAILED: "send the confirmation email", S.CANCELLED: "No confirmation email"}
        for i, (status, text) in enumerate(expected.items(), start=10):
            make(status, i)
            self.assertIn(text, render(i))

    def test_never_claims_delivery_and_masks_email(self):
        make(S.SENT)
        html = render(1)
        self.assertNotIn("delivered", html.lower().replace("not guaranteed", ""))
        self.assertIn("a***@x.com", html)
        self.assertNotIn("asha@x.com", html)

    def test_failure_does_not_blame_registration(self):
        make(S.FAILED)
        self.assertIn("Your registration is not affected", render(1))

    def test_mentions_reminder_timing(self):
        self.assertIn("48 hours and 2 hours", render(1))
