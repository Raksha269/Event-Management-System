import logging

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Prefetch
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import LimitOffsetPagination

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

from .models import AuditEvent, Event, Registration, SecurityAlert, TicketType
from .audit import record_audit_event
from .reports import build_csv_response
from .serializers import (
    EventSerializer,
    EventListSerializer,
    RegistrationSerializer,
    SecurityAlertSerializer,
    TicketTypeSerializer,
    UserAdminSerializer,
)
from .services import create_registration

audit_log = logging.getLogger("ems.audit")


class OptInLimitOffsetPagination(LimitOffsetPagination):
    """Support paging without changing the existing default array responses."""

    default_limit = 50
    max_limit = 100

    def paginate_queryset(self, queryset, request, view=None):
        if "limit" not in request.query_params and "offset" not in request.query_params:
            return None
        return super().paginate_queryset(queryset, request, view=view)


class EventListCreateAPIView(generics.ListCreateAPIView):
    """
    GET /api/v1/events/ - Public search and browse published events.
    POST /api/v1/events/ - Organizer creates a new event in Draft status (EMS-F-010).
    """

    serializer_class = EventSerializer
    pagination_class = OptInLimitOffsetPagination

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), IsOrganizer()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        if self.request.method == "GET" and (
            "limit" in self.request.query_params
            or "offset" in self.request.query_params
        ):
            return EventListSerializer
        return self.serializer_class

    def get_queryset(self):
        active_tickets = TicketType.objects.annotate(
            _active_registration_quantity=Coalesce(
                models.Sum(
                    "registrations__quantity",
                    filter=~models.Q(
                        registrations__status=Registration.Status.CANCELLED
                    ),
                ),
                models.Value(0),
            )
        )
        queryset = (
            Event.objects.filter(status=Event.Status.PUBLISHED)
            .annotate(
                _active_registration_quantity=Coalesce(
                    models.Sum(
                        "registrations__quantity",
                        filter=~models.Q(
                            registrations__status=Registration.Status.CANCELLED
                        ),
                    ),
                    models.Value(0),
                )
            )
            .prefetch_related(
                Prefetch("ticket_types", queryset=active_tickets)
            )
        )
        if "limit" in self.request.query_params or "offset" in self.request.query_params:
            queryset = queryset.defer("description")
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
        event = serializer.save(
            organizer=self.request.user,
            status=Event.Status.DRAFT,
        )
        record_audit_event("event.created", actor=self.request.user, target=event, request=self.request)


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

    def perform_update(self, serializer):
        event = serializer.save()
        record_audit_event(
            "event.updated", actor=self.request.user, target=event, request=self.request
        )

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

        record_audit_event("event.published", actor=request.user, target=event, request=request)

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
        record_audit_event("event.unpublished", actor=request.user, target=event, request=request)
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
                request=request,
                idempotency_key=request.headers.get("Idempotency-Key"),
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
        replayed = getattr(registration, "_idempotency_replayed", False)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK if replayed else status.HTTP_201_CREATED,
            headers={"Idempotency-Replayed": "true"} if replayed else None,
        )


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
    pagination_class = OptInLimitOffsetPagination

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
            record_audit_event("admin.user_updated", actor=request.user, target=updated_user, request=request)
            return Response(UserAdminSerializer(updated_user).data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminSecurityAlertsListAPIView(generics.ListAPIView):
    """
    GET /api/v1/admin/alerts/ - Administrator views all security alerts (EMS-SR-005).
    Supports filtering by ?severity=HIGH, ?type=ACCOUNT_LOCKOUT, and ?is_resolved=false.
    """

    serializer_class = SecurityAlertSerializer
    pagination_class = OptInLimitOffsetPagination
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
        record_audit_event("security.alert_resolved", actor=request.user, target=alert, request=request)

        audit_log.info(
            "security_alert_resolved admin_id=%s alert_id=%s",
            request.user.pk,
            alert.pk,
        )
        serializer = SecurityAlertSerializer(alert)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AdminAuditEventsAPIView(APIView):
    """Read-only, administrator-only access to retained audit history."""

    permission_classes = [permissions.IsAuthenticated, IsAdministrator]

    def get(self, request):
        try:
            limit = min(max(int(request.query_params.get("limit", 50)), 1), 100)
            offset = max(int(request.query_params.get("offset", 0)), 0)
        except (TypeError, ValueError):
            return Response({"detail": "limit and offset must be integers."}, status=400)

        rows = AuditEvent.objects.select_related("actor").order_by("-created_at", "-pk")
        count = rows.count()
        results = list(rows[offset:offset + limit].values(
            "id", "actor_id", "actor__username", "action", "target_type",
            "target_id", "outcome", "request_id", "ip_address", "created_at",
        ))
        return Response({"count": count, "limit": limit, "offset": offset, "results": results})
