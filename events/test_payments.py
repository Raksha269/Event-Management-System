
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
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