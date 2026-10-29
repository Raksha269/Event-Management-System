import io

import qrcode
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from .models import Payment, Refund, Registration, Ticket


def mock_payment_gateway(amount):
    """
    Simulate a payment gateway.
    This function never processes real payments or stores card details.
    """
    if amount <= 0:
        return {
            "success": False,
            "message": "Payment amount must be positive.",
        }

    return {
        "success": True,
        "message": "Mock payment successful.",
    }


def generate_ticket_qr(ticket):
    """Generate and save a QR-code image for an e-ticket."""
    qr_data = (
        f"Ticket ID: {ticket.ticket_code}\n"
        f"Registration ID: {ticket.registration_id}"
    )

    image = qrcode.make(qr_data)
    image_buffer = io.BytesIO()
    image.save(image_buffer, format="PNG")

    ticket.qr_code.save(
        f"ticket_{ticket.ticket_code}.png",
        ContentFile(image_buffer.getvalue()),
        save=True,
    )


@transaction.atomic
def process_payment(registration_id):
    """
    Process a registration payment using the mock gateway.
    Successful payments confirm registration and issue an e-ticket.
    """
    registration = Registration.objects.select_for_update().get(
        pk=registration_id
    )

    existing_payment = Payment.objects.filter(
        registration=registration
    ).first()

    if existing_payment and existing_payment.status == Payment.Status.SUCCESS:
        return existing_payment

    if registration.status != Registration.Status.PENDING:
        raise ValueError("Only pending registrations can be paid.")

    amount = registration.event.ticket_price

    payment = existing_payment or Payment.objects.create(
        registration=registration,
        amount=amount,
    )

    result = mock_payment_gateway(amount)

    if not result["success"]:
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=["status"])
        return payment

    payment.status = Payment.Status.SUCCESS
    payment.save(update_fields=["status"])

    registration.status = Registration.Status.CONFIRMED
    registration.save(update_fields=["status"])

    ticket, _ = Ticket.objects.get_or_create(
        registration=registration
    )

    if not ticket.qr_code:
        generate_ticket_qr(ticket)

    return payment


@transaction.atomic
def process_refund(payment_id, reason):
    """
    Process a full refund through a controlled mock workflow.
    Only successful payments can be refunded.
    """
    payment = Payment.objects.select_for_update().get(pk=payment_id)

    if payment.status != Payment.Status.SUCCESS:
        raise ValueError("Only successful payments can be refunded.")

    if not reason or not reason.strip():
        raise ValueError("A refund reason is required.")

    if payment.refunds.filter(
        status__in=[
            Refund.Status.PENDING,
            Refund.Status.APPROVED,
            Refund.Status.COMPLETED,
        ]
    ).exists():
        raise ValueError("A refund has already been requested.")

    refund = Refund.objects.create(
        payment=payment,
        reason=reason.strip(),
        amount=payment.amount,
        status=Refund.Status.APPROVED,
    )

    # Simulate successful refund processing.
    refund.status = Refund.Status.COMPLETED
    refund.save(update_fields=["status"])

    payment.status = Payment.Status.REFUNDED
    payment.save(update_fields=["status"])

    registration = payment.registration
    registration.status = Registration.Status.CANCELLED
    registration.save(update_fields=["status"])

    return refund