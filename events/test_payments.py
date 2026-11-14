
import tempfile
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone

from .models import Event, Payment, Refund, Registration, Ticket
from .services import process_payment, process_refund


class PaymentWorkflowTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="payment_user",
            password="StrongTestPass123!",
        )

        self.event = Event.objects.create(
            name="Test Event",
            description="Test event for payments",
            date=timezone.now() + timedelta(days=7),
            venue="Bengaluru",
            ticket_price=Decimal("500.00"),
            capacity=100,
        )

        self.registration = Registration.objects.create(
            user=self.user,
            event=self.event,
        )

    def test_successful_payment_creates_ticket(self):
        payment = process_payment(self.registration.pk)

        self.registration.refresh_from_db()

        self.assertEqual(payment.status, Payment.Status.SUCCESS)
        self.assertEqual(
            self.registration.status,
            Registration.Status.CONFIRMED,
        )

        ticket = Ticket.objects.get(registration=self.registration)
        self.assertTrue(ticket.qr_code.name)

    @patch(
        "events.services.mock_payment_gateway",
        return_value={
            "success": False,
            "message": "Payment declined",
        },
    )
    def test_failed_payment_does_not_create_ticket(self, mock_gateway):
        payment = process_payment(self.registration.pk)

        self.registration.refresh_from_db()

        self.assertEqual(payment.status, Payment.Status.FAILED)
        self.assertEqual(
            self.registration.status,
            Registration.Status.PENDING,
        )

        self.assertFalse(
            Ticket.objects.filter(
                registration=self.registration
            ).exists()
        )

    def test_successful_payment_can_be_refunded(self):
        payment = process_payment(self.registration.pk)

        refund = process_refund(payment.pk, "Event cancellation")

        payment.refresh_from_db()
        self.registration.refresh_from_db()

        self.assertEqual(refund.status, Refund.Status.COMPLETED)
        self.assertEqual(refund.amount, Decimal("500.00"))
        self.assertEqual(payment.status, Payment.Status.REFUNDED)
        self.assertEqual(
            self.registration.status,
            Registration.Status.CANCELLED,
        )

    def test_failed_payment_cannot_be_refunded(self):
        payment = Payment.objects.create(
            registration=self.registration,
            amount=Decimal("500.00"),
            status=Payment.Status.FAILED,
        )

        with self.assertRaises(ValueError):
            process_refund(payment.pk, "Refund attempt")

    def test_payment_is_not_duplicated(self):
        first_payment = process_payment(self.registration.pk)
        second_payment = process_payment(self.registration.pk)

        self.assertEqual(first_payment.pk, second_payment.pk)

        self.assertEqual(
            Payment.objects.filter(
                registration=self.registration
            ).count(),
            1,
        )

        self.assertEqual(
            Ticket.objects.filter(
                registration=self.registration
            ).count(),
            1,
        )

    def test_refund_requires_a_reason(self):
        payment = process_payment(self.registration.pk)

        with self.assertRaises(ValueError):
            process_refund(payment.pk, "   ")

@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="ems_ticket_tests_"))
class TicketAccessTests(TestCase):
    """Verify ticket access and QR-code authorization."""

    def setUp(self):
        self.owner = User.objects.create_user(
            username="ticket_owner",
            password="StrongTestPass123!",
        )
        self.other_user = User.objects.create_user(
            username="other_attendee",
            password="StrongTestPass123!",
        )

        self.event = Event.objects.create(
            name="Ticket Security Test Event",
            description="Test ticket ownership",
            date=timezone.now() + timedelta(days=7),
            venue="Bengaluru",
            ticket_price=Decimal("500.00"),
            capacity=100,
        )

        self.registration = Registration.objects.create(
            user=self.owner,
            event=self.event,
        )

        process_payment(self.registration.pk)

        self.ticket_url = (
            f"/events/registrations/{self.registration.pk}/ticket/"
        )
        self.qr_url = (
            f"/events/registrations/{self.registration.pk}/ticket/qr/"
        )

    def test_owner_can_view_confirmed_ticket(self):
        self.client.force_login(self.owner)

        response = self.client.get(self.ticket_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "events/ticket_detail.html")

    def test_other_attendee_cannot_view_ticket(self):
        self.client.force_login(self.other_user)

        response = self.client.get(self.ticket_url)

        self.assertEqual(response.status_code, 404)

    def test_other_attendee_cannot_access_qr(self):
        self.client.force_login(self.other_user)

        response = self.client.get(self.qr_url)

        self.assertEqual(response.status_code, 404)

    def test_owner_can_access_qr(self):
        self.client.force_login(self.owner)

        response = self.client.get(self.qr_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        # response.close()  # Temporarily disabled for PostgreSQL CI diagnosis

    def test_pending_registration_cannot_view_ticket(self):
        self.registration.status = Registration.Status.PENDING
        self.registration.save(update_fields=["status"])

        self.client.force_login(self.owner)

        response = self.client.get(self.ticket_url)

        self.assertEqual(response.status_code, 404)

    def test_anonymous_user_cannot_view_ticket(self):
        response = self.client.get(self.ticket_url)

        self.assertEqual(response.status_code, 302)
