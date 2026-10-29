import logging

from django.contrib.auth.models import User
from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

try:
    from accounts.permissions import IsAdministrator, IsEventOwner, IsOrganizer
    from accounts.roles import Role
except ImportError:
    from RBAC.accounts.permissions import (
        IsAdministrator,
        IsEventOwner,
        IsOrganizer,
    )
    from RBAC.accounts.roles import Role

from .models import Event, Registration, SecurityAlert, TicketType
from .reports import build_csv_response
from .serializers import (
    EventSerializer,
    RegistrationSerializer,
    SecurityAlertSerializer,
    TicketTypeSerializer,
    UserAdminSerializer,
)
from .services import create_registration

audit_log = logging.getLogger("ems.audit")


class EventListCreateAPIView(generics.ListCreateAPIView):
    """
    GET /api/v1/events/ - Public search and browse published events.
    POST /api/v1/events/ - Organizer creates a new event in Draft status (EMS-F-010).
    """

    serializer_class = EventSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), IsOrganizer()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        queryset = Event.objects.filter(status=Event.Status.PUBLISHED)
        q = self.request.query_params.get("q")
        category = self.request.query_params.get("category")

        if q:
            queryset = queryset.filter(
                models.Q(title__icontains=q)
                | models.Q(name__icontains=q)
                | models.Q(description__icontains=q)
                | models.Q(venue__icontains=q)
            )
        if category:
            queryset = queryset.filter(category__iexact=category)

        return queryset.order_by("date")

    def perform_create(self, serializer):
        serializer.save(
            organizer=self.request.user,
            status=Event.Status.DRAFT,
        )


class EventDetailUpdateAPIView(generics.RetrieveUpdateAPIView):
    """
    GET /api/v1/events/{id}/ - View event details.
    PUT/PATCH /api/v1/events/{id}/ - Owning organizer edits event prior to start date (EMS-F-011).
    """

    serializer_class = EventSerializer
    queryset = Event.objects.all()

    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH"]:
            return [permissions.IsAuthenticated(), IsOrganizer(), IsEventOwner()]
        return [permissions.AllowAny()]

    def get_object(self):
        event = get_object_or_404(Event, pk=self.kwargs["pk"])

        # Check read permission: if unpublished, only owning organizer or staff can view
        if self.request.method == "GET" and not event.is_published:
            user = self.request.user
            if not user.is_authenticated or (
                event.organizer != user and not user.is_staff
            ):
                raise permissions.exceptions.NotFound("Event not found.")

        # Check object permissions for write
        self.check_object_permissions(self.request, event)
        return event

    def update(self, request, *args, **kwargs):
        event = self.get_object()

        # EMS-F-011: changes permitted only prior to event start date
        if not event.can_be_edited():
            return Response(
                {
                    "code": "EVENT_ALREADY_STARTED",
                    "message": "Cannot edit an event that has already started.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().update(request, *args, **kwargs)


class EventPublishAPIView(APIView):
    """
    POST /api/v1/events/{id}/publish/ - Owning organizer publishes an event (EMS-F-012).
    """

    permission_classes = [permissions.IsAuthenticated, IsOrganizer, IsEventOwner]

    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        self.check_object_permissions(request, event)

        try:
            event.publish()
        except ValueError as err:
            return Response(
                {"code": "PUBLICATION_ERROR", "message": str(err)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = EventSerializer(event)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EventUnpublishAPIView(APIView):
    """
    POST /api/v1/events/{id}/unpublish/ - Owning organizer unpublishes an event (EMS-F-012).
    """

    permission_classes = [permissions.IsAuthenticated, IsOrganizer, IsEventOwner]

    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        self.check_object_permissions(request, event)

        event.unpublish()
        serializer = EventSerializer(event)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EventTicketTypeListCreateAPIView(APIView):
    """
    POST /api/v1/events/{id}/ticket-types/ - Owning organizer adds a ticket type (EMS-F-013).
    """

    permission_classes = [permissions.IsAuthenticated, IsOrganizer, IsEventOwner]

    def get(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        ticket_types = event.ticket_types.all()
        serializer = TicketTypeSerializer(ticket_types, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        self.check_object_permissions(request, event)

        serializer = TicketTypeSerializer(data=request.data)
        if serializer.is_valid():
            quantity_limit = serializer.validated_data["quantity_limit"]
            existing_total = (
                event.ticket_types.aggregate(total=models.Sum("quantity_limit"))[
                    "total"
                ]
                or 0
            )

            if existing_total + quantity_limit > event.capacity:
                return Response(
                    {
                        "code": "CAPACITY_EXCEEDED",
                        "message": (
                            f"Total ticket type capacity ({existing_total + quantity_limit}) "
                            f"exceeds event capacity ({event.capacity})."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            ticket_type = serializer.save(event=event)
            return Response(
                TicketTypeSerializer(ticket_type).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EventRegistrationAPIView(APIView):
    """
    POST /api/v1/events/{id}/registrations/ - Reserve tickets with capacity control (EMS-F-014).
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        ticket_type_id = request.data.get("ticket_type_id")
        quantity = int(request.data.get("quantity", 1))

        try:
            registration = create_registration(
                user=request.user,
                event_id=pk,
                ticket_type_id=ticket_type_id,
                quantity=quantity,
            )
        except ValueError as err:
            err_msg = str(err)
            if "Sold Out" in err_msg or "capacity" in err_msg.lower():
                return Response(
                    {"code": "CAPACITY_EXCEEDED", "message": err_msg},
                    status=status.HTTP_409_CONFLICT,
                )
            return Response(
                {"code": "VALIDATION_ERROR", "message": err_msg},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RegistrationSerializer(registration)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EventAttendeesCSVReportAPIView(APIView):
    """
    GET /api/v1/events/{id}/reports/attendees.csv - Owning organizer or admin downloads CSV report (EMS-F-050).
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        event = get_object_or_404(Event, pk=pk)

        # Owning organizer or administrator permitted
        is_owner = event.organizer_id == request.user.pk
        is_admin = getattr(request.user, "is_administrator", False) or (
            getattr(request.user, "role", None) == Role.ADMINISTRATOR
        )

        if not is_owner and not is_admin:
            raise PermissionDenied(
                "You do not have permission to download reports for this event."
            )

        return build_csv_response(event)


class AdminUserListAPIView(generics.ListAPIView):
    """
    GET /api/v1/admin/users/ - Administrator lists all users with role and status (EMS-F-051).
    """

    permission_classes = [permissions.IsAuthenticated, IsAdministrator]
    serializer_class = UserAdminSerializer

    def get_queryset(self):
        queryset = User.objects.all().order_by("-date_joined")
        q = self.request.query_params.get("q")
        role = self.request.query_params.get("role")

        if q:
            queryset = queryset.filter(
                models.Q(username__icontains=q) | models.Q(email__icontains=q)
            )
        if role:
            # Match role in UserProfile
            queryset = queryset.filter(profile__role=role)

        return queryset


class AdminUserDetailUpdateAPIView(APIView):
    """
    GET /api/v1/admin/users/{id}/ - Retrieve user.
    PATCH /api/v1/admin/users/{id}/ - Administrator activates, deactivates, or changes role (EMS-F-051).
    """

    permission_classes = [permissions.IsAuthenticated, IsAdministrator]

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        serializer = UserAdminSerializer(user)
        return Response(serializer.data)

    def patch(self, request, pk):
        target = get_object_or_404(User, pk=pk)

        # Safety: Administrator cannot deactivate their own account
        if target.pk == request.user.pk and request.data.get("is_active") is False:
            return Response(
                {
                    "code": "CANNOT_DEACTIVATE_SELF",
                    "message": "Administrators cannot deactivate their own account.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Safety: Administrator cannot change their own role
        new_role = request.data.get("role")
        if (
            target.pk == request.user.pk
            and new_role is not None
            and new_role != target.role
        ):
            return Response(
                {
                    "code": "CANNOT_CHANGE_OWN_ROLE",
                    "message": "Administrators cannot change their own role.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = UserAdminSerializer(target, data=request.data, partial=True)
        if serializer.is_valid():
            old_role = target.role
            old_active = target.is_active
            updated_user = serializer.save()

            audit_log.info(
                "admin_user_update actor=%s target=%s role=%s->%s active=%s->%s",
                request.user.pk,
                target.pk,
                old_role,
                updated_user.role,
                old_active,
                updated_user.is_active,
            )
            return Response(UserAdminSerializer(updated_user).data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminSecurityAlertsListAPIView(generics.ListAPIView):
    """
    GET /api/v1/admin/alerts/ - Administrator views all security alerts (EMS-SR-005).
    Supports filtering by ?severity=HIGH, ?type=ACCOUNT_LOCKOUT, and ?is_resolved=false.
    """

    serializer_class = SecurityAlertSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdministrator]

    def get_queryset(self):
        queryset = SecurityAlert.objects.all().select_related("target_user")
        severity = self.request.query_params.get("severity")
        alert_type = self.request.query_params.get("type") or self.request.query_params.get("alert_type")
        is_resolved = self.request.query_params.get("is_resolved")

        if severity:
            queryset = queryset.filter(severity__iexact=severity.strip())
        if alert_type:
            queryset = queryset.filter(alert_type__iexact=alert_type.strip())
        if is_resolved is not None:
            if is_resolved.strip().lower() in ["true", "1"]:
                queryset = queryset.filter(is_resolved=True)
            elif is_resolved.strip().lower() in ["false", "0"]:
                queryset = queryset.filter(is_resolved=False)

        return queryset


class AdminSecurityAlertResolveAPIView(APIView):
    """
    POST /api/v1/admin/alerts/{id}/resolve/ - Administrator resolves an alert (EMS-SR-005).
    """

    permission_classes = [permissions.IsAuthenticated, IsAdministrator]

    def post(self, request, pk):
        alert = get_object_or_404(SecurityAlert, pk=pk)
        alert.is_resolved = True
        alert.save(update_fields=["is_resolved"])

        audit_log.info(
            "security_alert_resolved admin_id=%s alert_id=%s",
            request.user.pk,
            alert.pk,
        )
        serializer = SecurityAlertSerializer(alert)
        return Response(serializer.data, status=status.HTTP_200_OK)
