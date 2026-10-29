import secrets

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db import models, transaction
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

try:
    from accounts.decorators import role_required
    from accounts.roles import Role
except ImportError:
    from RBAC.accounts.decorators import role_required
    from RBAC.accounts.roles import Role

from .forms import (
    EventForm,
    EventRegistrationForm,
    GatherLoginForm,
    RegistrationForm,
    TicketTypeForm,
)
from .models import Event, Registration, SecurityAlert, TicketType, UserProfile
from .reports import build_csv_response, get_event_report_data
from .security import (
    check_account_lockout,
    record_login_success,
    track_login_failure,
)
from .services import create_registration


def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                user = form.save(commit=False)

                # The account cannot be used until email verification.
                user.is_active = False
                user.save()

                verification_token = secrets.token_urlsafe(32)

                UserProfile.objects.create(
                    user=user,
                    email_verified=False,
                    verification_token=verification_token,
                )

                verification_url = request.build_absolute_uri(
                    reverse(
                        "verify_email",
                        kwargs={"token": verification_token},
                    )
                )

                transaction.on_commit(
                    lambda: send_mail(
                        subject="Verify your Gather account",
                        message=(
                            f"Hi {user.username},\n\n"
                            "Please verify your email address using this link:\n"
                            f"{verification_url}\n\n"
                            "If you did not create this account, you can ignore this email."
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                )

            messages.success(
                request,
                "Registration successful! Check the terminal for your email verification link.",
            )
            return redirect("register")
    else:
        form = RegistrationForm()

    return render(request, "events/register.html", {"form": form})


def verify_email(request, token):
    profile = (
        UserProfile.objects.filter(
            verification_token=token,
            email_verified=False,
        )
        .select_related("user")
        .first()
    )

    if profile is None:
        return render(
            request,
            "events/verification_result.html",
            {
                "success": False,
                "message": (
                    "This verification link is invalid or has already been used."
                ),
            },
            status=400,
        )

    profile.email_verified = True
    profile.verification_token = None
    profile.save(update_fields=["email_verified", "verification_token"])

    # Activate the account after successful email verification.
    User.objects.filter(pk=profile.user_id).update(is_active=True)

    return render(
        request,
        "events/verification_result.html",
        {
            "success": True,
            "message": "Your email has been verified successfully!",
        },
    )


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "")
        user_candidate = (
            User.objects.filter(username=username).first()
            or User.objects.filter(email__iexact=username).first()
        )

        if user_candidate:
            is_locked, lockout_msg = check_account_lockout(user_candidate)
            if is_locked:
                messages.error(request, lockout_msg)
                form = GatherLoginForm(request, data=request.POST)
                return render(request, "events/login.html", {"form": form})

        form = GatherLoginForm(request, data=request.POST)

        if form.is_valid():
            user = form.get_user()
            record_login_success(user)
            login(request, user)
            messages.success(request, "Welcome back!")
            return redirect("register")
        else:
            if username:
                _, err_msg = track_login_failure(username, request=request)
                if "locked" in err_msg.lower():
                    messages.error(request, err_msg)
    else:
        form = GatherLoginForm(request)

    return render(request, "events/login.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("login")


# --- Event Management Views (EMS-F-010 to EMS-F-014) ---


def discover_events(request):
    """
    Public browse and search view.
    Only published events are visible to public attendees (EMS-F-012).
    """
    events = Event.objects.filter(status=Event.Status.PUBLISHED)
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()

    if query:
        events = events.filter(
            models.Q(title__icontains=query)
            | models.Q(name__icontains=query)
            | models.Q(description__icontains=query)
            | models.Q(venue__icontains=query)
        )
    if category:
        events = events.filter(category__iexact=category)

    events = events.order_by("date")
    categories = (
        Event.objects.filter(status=Event.Status.PUBLISHED)
        .values_list("category", flat=True)
        .distinct()
    )

    return render(
        request,
        "events/discover.html",
        {
            "events": events,
            "query": query,
            "selected_category": category,
            "categories": [c for c in categories if c],
        },
    )


@role_required(Role.ORGANIZER, Role.ADMINISTRATOR)
def organizer_dashboard(request):
    """
    Organizer dashboard: view all events created by the logged-in organizer (EMS-F-010).
    Draft, Published, and Unpublished statuses are visible here.
    """
    events = Event.objects.filter(organizer=request.user).order_by("-created_at")
    return render(request, "events/dashboard.html", {"events": events})


@role_required(Role.ORGANIZER, Role.ADMINISTRATOR)
def event_create(request):
    """
    Create a new event in Draft status (EMS-F-010).
    """
    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.status = Event.Status.DRAFT
            event.save()
            messages.success(
                request,
                f"Event '{event.event_title}' created successfully as a Draft. Configure ticket types or publish when ready.",
            )
            return redirect("organizer_dashboard")
    else:
        form = EventForm()

    return render(
        request,
        "events/event_form.html",
        {
            "form": form,
            "title": "Create New Event",
            "submit_label": "Create Event (Save as Draft)",
        },
    )


@role_required(Role.ORGANIZER, Role.ADMINISTRATOR)
def event_edit(request, pk):
    """
    Edit event details prior to the event start date (EMS-F-011).
    Restricted to the owning organizer.
    """
    event = get_object_or_404(Event, pk=pk)

    # Ownership check
    if event.organizer != request.user and not request.user.is_superuser:
        raise PermissionDenied("You do not have permission to edit this event.")

    # Start date check (EMS-F-011)
    if not event.can_be_edited():
        messages.error(request, "Cannot edit an event that has already started.")
        return HttpResponseBadRequest("Cannot edit an event that has already started.")

    if request.method == "POST":
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"Event '{event.event_title}' updated successfully.",
            )
            return redirect("organizer_dashboard")
    else:
        form = EventForm(instance=event)

    return render(
        request,
        "events/event_form.html",
        {
            "form": form,
            "event": event,
            "title": f"Edit Event: {event.event_title}",
            "submit_label": "Save Changes",
        },
    )


@role_required(Role.ORGANIZER, Role.ADMINISTRATOR)
def event_publish(request, pk):
    """
    Publish an event, making it visible in public search (EMS-F-012).
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST request required.")

    event = get_object_or_404(Event, pk=pk)

    if event.organizer != request.user and not request.user.is_superuser:
        raise PermissionDenied("You do not have permission to publish this event.")

    try:
        event.publish()
        messages.success(
            request, f"Event '{event.event_title}' is now published and visible to attendees."
        )
    except ValueError as err:
        messages.error(request, f"Failed to publish event: {err}")

    return redirect("organizer_dashboard")


@role_required(Role.ORGANIZER, Role.ADMINISTRATOR)
def event_unpublish(request, pk):
    """
    Unpublish an event, hiding it from public discovery (EMS-F-012).
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST request required.")

    event = get_object_or_404(Event, pk=pk)

    if event.organizer != request.user and not request.user.is_superuser:
        raise PermissionDenied("You do not have permission to unpublish this event.")

    event.unpublish()
    messages.success(
        request, f"Event '{event.event_title}' has been unpublished."
    )
    return redirect("organizer_dashboard")


def event_detail(request, pk):
    """
    Public event detail view.
    Draft or unpublished events are only visible to the owning organizer (EMS-F-012).
    """
    event = get_object_or_404(Event, pk=pk)

    if not event.is_published:
        if not request.user.is_authenticated or (
            event.organizer != request.user and not request.user.is_superuser
        ):
            raise Http404("Event not found or not published.")

    form = EventRegistrationForm(event=event)
    ticket_types = event.ticket_types.all()

    return render(
        request,
        "events/event_detail.html",
        {
            "event": event,
            "form": form,
            "ticket_types": ticket_types,
        },
    )


@role_required(Role.ORGANIZER, Role.ADMINISTRATOR)
def ticket_types_manage(request, pk):
    """
    Configure ticket types and capacity for an event (EMS-F-013).
    """
    event = get_object_or_404(Event, pk=pk)

    if event.organizer != request.user and not request.user.is_superuser:
        raise PermissionDenied(
            "You do not have permission to manage tickets for this event."
        )

    if request.method == "POST":
        form = TicketTypeForm(request.POST)
        if form.is_valid():
            ticket_type = form.save(commit=False)
            ticket_type.event = event

            # Validate that ticket type limit does not exceed event capacity
            existing_total = (
                event.ticket_types.aggregate(
                    total=models.Sum("quantity_limit")
                )["total"]
                or 0
            )

            if existing_total + ticket_type.quantity_limit > event.capacity:
                form.add_error(
                    "quantity_limit",
                    f"Total ticket quantity ({existing_total + ticket_type.quantity_limit}) "
                    f"cannot exceed event capacity ({event.capacity}).",
                )
            elif event.ticket_types.filter(name=ticket_type.name).exists():
                form.add_error(
                    "name", "A ticket type with this name already exists for this event."
                )
            else:
                ticket_type.save()
                messages.success(
                    request, f"Ticket type '{ticket_type.name}' added successfully."
                )
                return redirect("ticket_types_manage", pk=event.pk)
    else:
        form = TicketTypeForm()

    ticket_types = event.ticket_types.all()
    configured_capacity = (
        ticket_types.aggregate(total=models.Sum("quantity_limit"))["total"] or 0
    )

    return render(
        request,
        "events/ticket_types.html",
        {
            "event": event,
            "ticket_types": ticket_types,
            "form": form,
            "configured_capacity": configured_capacity,
        },
    )


@login_required
def event_register(request, pk):
    """
    Attendee registration view with capacity checking (EMS-F-014).
    Rejects registration and displays 'Sold Out' if capacity is exhausted.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST request required.")

    event = get_object_or_404(Event, pk=pk)
    form = EventRegistrationForm(request.POST, event=event)

    if form.is_valid():
        ticket_type = form.cleaned_data.get("ticket_type")
        quantity = form.cleaned_data.get("quantity", 1)
        ticket_type_id = ticket_type.pk if ticket_type else None

        try:
            registration = create_registration(
                user=request.user,
                event_id=event.pk,
                ticket_type_id=ticket_type_id,
                quantity=quantity,
            )
            messages.success(
                request,
                f"Successfully registered {quantity} ticket(s) for '{event.event_title}'.",
            )
        except ValueError as err:
            messages.error(request, str(err))

    return redirect("event_detail", pk=event.pk)


# --- Reporting & Administration Views (EMS-F-050, EMS-F-051) ---


@login_required
def event_report(request, pk):
    """
    On-screen attendee list and revenue report for an event (EMS-F-050).
    Only owning organizer or administrator can access.
    """
    event = get_object_or_404(Event, pk=pk)

    is_owner = event.organizer == request.user
    is_admin = getattr(request.user, "is_administrator", False) or (
        getattr(request.user, "role", None) == Role.ADMINISTRATOR
    )

    if not is_owner and not is_admin:
        raise PermissionDenied("You do not have permission to view reports for this event.")

    report = get_event_report_data(event)
    return render(
        request,
        "events/event_report.html",
        {
            "event": event,
            "report": report,
        },
    )


@login_required
def event_report_csv(request, pk):
    """
    Download attendee and revenue report in CSV format (EMS-F-050).
    Only owning organizer or administrator can access.
    """
    event = get_object_or_404(Event, pk=pk)

    is_owner = event.organizer == request.user
    is_admin = getattr(request.user, "is_administrator", False) or (
        getattr(request.user, "role", None) == Role.ADMINISTRATOR
    )

    if not is_owner and not is_admin:
        raise PermissionDenied("You do not have permission to download reports for this event.")

    return build_csv_response(event)


@role_required(Role.ADMINISTRATOR)
def admin_user_list(request):
    """
    Administrator view to list and manage all user accounts (EMS-F-051).
    """
    users = User.objects.all().select_related("profile").order_by("-date_joined")
    query = request.GET.get("q", "").strip()
    role_filter = request.GET.get("role", "").strip()

    if query:
        users = users.filter(
            models.Q(username__icontains=query) | models.Q(email__icontains=query)
        )
    if role_filter:
        users = users.filter(profile__role=role_filter)

    return render(
        request,
        "events/admin_user_list.html",
        {
            "users": users,
            "query": query,
            "selected_role": role_filter,
            "available_roles": Role.choices,
        },
    )


@role_required(Role.ADMINISTRATOR)
def admin_user_toggle_active(request, pk):
    """
    Administrator toggles user account activation status (EMS-F-051).
    Deactivated accounts cannot log in.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST request required.")

    target = get_object_or_404(User, pk=pk)

    if target.pk == request.user.pk:
        messages.error(request, "Administrators cannot deactivate their own account.")
        return redirect("admin_user_list")

    target.is_active = not target.is_active
    target.save(update_fields=["is_active"])

    status_str = "activated" if target.is_active else "deactivated"
    messages.success(request, f"User '{target.username}' has been {status_str}.")
    return redirect("admin_user_list")


@role_required(Role.ADMINISTRATOR)
def admin_user_change_role(request, pk):
    """
    Administrator changes the role of a user account (EMS-F-051).
    Takes effect immediately.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST request required.")

    target = get_object_or_404(User, pk=pk)
    new_role = request.POST.get("role")

    if target.pk == request.user.pk:
        messages.error(request, "Administrators cannot change their own role.")
        return redirect("admin_user_list")

    if new_role not in Role.values:
        messages.error(request, f"Invalid role selection: '{new_role}'.")
        return redirect("admin_user_list")

    old_role = target.role
    target.role = new_role
    messages.success(
        request,
        f"Role for '{target.username}' changed from '{old_role}' to '{new_role}'.",
    )
    return redirect("admin_user_list")


@role_required(Role.ADMINISTRATOR)
def admin_alerts_list(request):
    """
    Administrator monitoring panel for security alerts (EMS-SR-005).
    """
    alerts = SecurityAlert.objects.all().select_related("target_user")
    severity = request.GET.get("severity", "").strip()
    alert_type = request.GET.get("type", "").strip()

    if severity:
        alerts = alerts.filter(severity=severity)
    if alert_type:
        alerts = alerts.filter(alert_type=alert_type)

    total_count = SecurityAlert.objects.count()
    unresolved_count = SecurityAlert.objects.filter(is_resolved=False).count()
    high_count = SecurityAlert.objects.filter(
        severity__in=[SecurityAlert.Severity.HIGH, SecurityAlert.Severity.CRITICAL]
    ).count()
    lockout_count = SecurityAlert.objects.filter(
        alert_type=SecurityAlert.AlertType.ACCOUNT_LOCKOUT
    ).count()

    return render(
        request,
        "events/admin_alerts.html",
        {
            "alerts": alerts,
            "total_count": total_count,
            "unresolved_count": unresolved_count,
            "high_count": high_count,
            "lockout_count": lockout_count,
            "selected_severity": severity,
            "selected_type": alert_type,
            "severity_choices": SecurityAlert.Severity.choices,
            "type_choices": SecurityAlert.AlertType.choices,
        },
    )


@role_required(Role.ADMINISTRATOR)
def admin_alert_resolve(request, pk):
    """
    Administrator marks a security alert as resolved (EMS-SR-005).
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST request required.")

    alert = get_object_or_404(SecurityAlert, pk=pk)
    alert.is_resolved = True
    alert.save(update_fields=["is_resolved"])

    messages.success(request, f"Alert #{alert.pk} marked as resolved.")
    return redirect("admin_alerts_list")
