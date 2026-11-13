from datetime import timedelta
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import AuditEvent, Event
from .services import create_registration, process_payment, process_refund


class NonFunctionalFoundationTests(TestCase):
    def test_readiness_checks_database_and_returns_request_id(self):
        response = self.client.get(reverse("readiness"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertRegex(response["X-Request-ID"], r"^[0-9a-f]{32}$")

    def test_event_api_pagination_is_opt_in_and_bounded(self):
        for index in range(2):
            Event.objects.create(
                title=f"Published event {index}",
                venue="Online",
                date=timezone.now() + timedelta(days=index + 1),
                status=Event.Status.PUBLISHED,
            )

        url = reverse("api_events_list_create")
        legacy_response = self.client.get(url)
        self.assertEqual(legacy_response.status_code, 200)
        self.assertIsInstance(legacy_response.data, list)

        paginated_response = self.client.get(url, {"limit": 1, "offset": 0})
        self.assertEqual(paginated_response.status_code, 200)
        self.assertEqual(paginated_response.data["count"], 2)
        self.assertEqual(len(paginated_response.data["results"]), 1)

    def test_admin_audit_api_is_protected_and_read_only(self):
        admin = User.objects.create_user(username="nfr_admin", password="pass")
        admin.role = "administrator"
        AuditEvent.objects.create(action="test.record", actor=admin)
        url = reverse("api_admin_audit_events")

        self.assertNotEqual(self.client.get(url).status_code, 200)

        self.client.force_login(admin)
        response = self.client.get(url, {"limit": 10})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["action"], "test.record")

        record = AuditEvent.objects.get(action="test.record")
        with self.assertRaises(ValueError):
            record.save()
        with self.assertRaises(ValueError):
            record.delete()

    @override_settings(EMS_AUDIT_RETENTION_DAYS=5)
    def test_retention_command_removes_only_expired_records(self):
        expired = AuditEvent.objects.create(action="expired.record")
        retained = AuditEvent.objects.create(action="retained.record")
        AuditEvent.objects.filter(pk=expired.pk).update(
            created_at=timezone.now() - timedelta(days=6)
        )

        output = StringIO()
        call_command("purge_audit_events", stdout=output)

        self.assertFalse(AuditEvent.objects.filter(pk=expired.pk).exists())
        self.assertTrue(AuditEvent.objects.filter(pk=retained.pk).exists())
        self.assertIn("Removed 1 expired audit record", output.getvalue())

    def test_registration_payment_and_refund_are_audited(self):
        user = User.objects.create_user(username="nfr_attendee", password="pass")
        event = Event.objects.create(
            title="Audit workflow",
            venue="Online",
            date=timezone.now() + timedelta(days=1),
            capacity=2,
            ticket_price="10.00",
            status=Event.Status.PUBLISHED,
        )

        registration = create_registration(user, event.pk)
        payment = process_payment(registration.pk)
        process_refund(payment.pk, "Test retention workflow")

        actions = set(
            AuditEvent.objects.filter(actor=user).values_list("action", flat=True)
        )
        self.assertTrue(
            {"registration.created", "payment.confirmed", "payment.refunded"}
            <= actions
        )
