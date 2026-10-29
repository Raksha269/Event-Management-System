import io

import qrcode
from django.core.files.base import ContentFile
from django.db import models, transaction
from django.utils import timezone

from .models import Event, Payment, Refund, Registration, Ticket, TicketType


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
def create_registration(user, event_id, ticket_type_id=None, quantity=1):
    """
    Register an attendee for an event with row-level locking to prevent overselling.
    Enforces EMS-F-014:
    - Row-level lock on event and ticket type avoids race conditions.
    - Rejects attempts exceeding event or ticket-type capacity with a 'Sold Out' error.
    """
    if quantity <= 0:
        raise ValueError("Registration quantity must be at least 1.")

    try:
        event = Event.objects.select_for_update().get(pk=event_id)
    except Event.DoesNotExist:
        raise ValueError("Event does not exist.")

    if event.status != Event.Status.PUBLISHED:
        raise ValueError("Cannot register for an unpublished event.")

    current_event_count = (
        Registration.objects.filter(event=event)
        .exclude(status=Registration.Status.CANCELLED)
        .aggregate(total=models.Sum("quantity"))["total"]
        or 0
    )

    if current_event_count + quantity > event.capacity:
        raise ValueError("Sold Out: Event capacity exceeded.")

    ticket_type = None
    if ticket_type_id:
        try:
            ticket_type = TicketType.objects.select_for_update().get(
                pk=ticket_type_id, event=event
            )
        except TicketType.DoesNotExist:
            raise ValueError("Ticket type does not exist for this event.")

        current_tt_count = (
            Registration.objects.filter(ticket_type=ticket_type)
            .exclude(status=Registration.Status.CANCELLED)
            .aggregate(total=models.Sum("quantity"))["total"]
            or 0
        )
        if current_tt_count + quantity > ticket_type.quantity_limit:
            raise ValueError("Sold Out: Ticket type capacity exceeded.")

        ticket_type.sold_count += quantity
        ticket_type.save(update_fields=["sold_count"])

    registration = Registration.objects.create(
        user=user,
        event=event,
        ticket_type=ticket_type,
        quantity=quantity,
        status=Registration.Status.PENDING,
    )
    return registration


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

    if registration.ticket_type:
        amount = registration.ticket_type.price * registration.quantity
    else:
        amount = registration.event.ticket_price * registration.quantity

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

    if registration.ticket_type:
        ticket_type = TicketType.objects.select_for_update().get(
            pk=registration.ticket_type_id
        )
        ticket_type.sold_count = max(
            0, ticket_type.sold_count - registration.quantity
        )
        ticket_type.save(update_fields=["sold_count"])

    return refund
