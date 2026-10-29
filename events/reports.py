import csv
from decimal import Decimal
import io

from django.db import models
from django.http import HttpResponse

from .models import Payment, Registration


def get_event_report_data(event):
    """
    Generate structured attendee list and revenue summary for an event (EMS-F-050).
    """
    registrations = (
        event.registrations.select_related("user", "ticket_type", "payment")
        .order_by("-created_at")
    )

    attendee_records = []
    gross_revenue = Decimal("0.00")
    total_refunded = Decimal("0.00")
    confirmed_tickets_count = 0

    for reg in registrations:
        ticket_tier_name = (
            reg.ticket_type.name if reg.ticket_type else "General Admission"
        )
        ticket_price = (
            reg.ticket_type.price if reg.ticket_type else reg.event.ticket_price
        )

        payment = getattr(reg, "payment", None)
        payment_status = payment.status if payment else "UNPAID"
        paid_amount = (
            payment.amount if payment else (ticket_price * reg.quantity)
        )

        if reg.status == Registration.Status.CONFIRMED:
            confirmed_tickets_count += reg.quantity

        if payment and payment.status in [
            Payment.Status.SUCCESS,
            Payment.Status.REFUNDED,
        ]:
            gross_revenue += payment.amount
        elif reg.status == Registration.Status.CONFIRMED and not payment and paid_amount:
            gross_revenue += paid_amount

        if payment and payment.status == Payment.Status.REFUNDED:
            total_refunded += payment.amount

        attendee_records.append(
            {
                "registration_id": reg.pk,
                "username": reg.user.username,
                "email": reg.user.email,
                "ticket_tier": ticket_tier_name,
                "quantity": reg.quantity,
                "amount": paid_amount,
                "status": reg.status,
                "payment_status": payment_status,
                "created_at": reg.created_at,
            }
        )

    net_revenue = gross_revenue - total_refunded

    # Breakdown by ticket tier
    ticket_tiers = []
    for tt in event.ticket_types.all():
        tier_confirmed_qty = (
            registrations.filter(
                ticket_type=tt, status=Registration.Status.CONFIRMED
            ).aggregate(total=models.Sum("quantity"))["total"]
            or 0
        )
        tier_revenue = tt.price * tier_confirmed_qty
        ticket_tiers.append(
            {
                "name": tt.name,
                "price": tt.price,
                "quantity_limit": tt.quantity_limit,
                "sold_count": tt.sold_count,
                "confirmed_quantity": tier_confirmed_qty,
                "revenue": tier_revenue,
            }
        )

    return {
        "event": event,
        "total_capacity": event.capacity,
        "remaining_capacity": event.remaining_capacity,
        "confirmed_tickets_count": confirmed_tickets_count,
        "total_registrations_count": len(attendee_records),
        "gross_revenue": gross_revenue,
        "total_refunded": total_refunded,
        "net_revenue": net_revenue,
        "ticket_tiers": ticket_tiers,
        "attendee_records": attendee_records,
    }


def generate_event_attendees_csv(event):
    """
    Export attendee and revenue report in CSV format (EMS-F-050).
    Matches on-screen attendee and revenue metrics.
    """
    report = get_event_report_data(event)
    output = io.StringIO()
    writer = csv.writer(output)

    # Summary Metadata
    writer.writerow(["Event Title", event.event_title])
    writer.writerow(
        [
            "Event Date",
            event.date.strftime("%Y-%m-%d %H:%M UTC") if event.date else "N/A",
        ]
    )
    writer.writerow(["Venue", event.venue])
    writer.writerow(["Total Capacity", event.capacity])
    writer.writerow(
        ["Confirmed Attendees", report["confirmed_tickets_count"]]
    )
    writer.writerow(["Gross Revenue", f"{report['gross_revenue']:.2f}"])
    writer.writerow(["Total Refunded", f"{report['total_refunded']:.2f}"])
    writer.writerow(["Net Revenue", f"{report['net_revenue']:.2f}"])
    writer.writerow([])

    # Table Header
    writer.writerow(
        [
            "Registration ID",
            "Username",
            "Email",
            "Ticket Tier",
            "Quantity",
            "Amount",
            "Registration Status",
            "Payment Status",
            "Registered At",
        ]
    )

    # Attendee rows
    for r in report["attendee_records"]:
        writer.writerow(
            [
                r["registration_id"],
                r["username"],
                r["email"],
                r["ticket_tier"],
                r["quantity"],
                f"{r['amount']:.2f}",
                r["status"],
                r["payment_status"],
                (
                    r["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                    if r["created_at"]
                    else ""
                ),
            ]
        )

    return output.getvalue()


def build_csv_response(event):
    """
    Helper to return an HTTP text/csv response for an event report.
    """
    csv_content = generate_event_attendees_csv(event)
    response = HttpResponse(csv_content, content_type="text/csv")
    filename = f"event_{event.pk}_attendees.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
