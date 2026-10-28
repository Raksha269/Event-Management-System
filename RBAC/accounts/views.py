import logging

from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .permissions import IsAdministrator, IsAttendee, IsOrganizer
from .roles import Role

audit_log = logging.getLogger("ems.audit")   # AuditModule owner can attach a handler


def forbidden(request, exception=None):
    """Plain 403 page. Reveals nothing about the protected record."""
    return render(request, "403.html", status=403)


class WhoAmIView(APIView):
    def get(self, request):
        u = request.user
        return Response({"username": u.username, "role": u.role})


class AttendeeAreaView(APIView):
    permission_classes = [IsAttendee]

    def get(self, request):
        return Response({"area": "attendee"})


class OrganizerAreaView(APIView):
    permission_classes = [IsOrganizer]

    def get(self, request):
        return Response({"area": "organizer"})


class AdminAreaView(APIView):
    permission_classes = [IsAdministrator]

    def get(self, request):
        return Response({"area": "administrator"})


class ChangeRoleView(APIView):
    """Admin-only role change. Role comes from the validated body of an
    ADMIN's request - never from the target user's own input."""
    permission_classes = [IsAdministrator]

    def post(self, request, user_id):
        new_role = request.data.get("role")
        reason = (request.data.get("reason") or "").strip()
        if new_role not in Role.values:
            return Response({"error": "invalid_role"}, status=400)
        if not reason:
            return Response({"error": "reason_required"}, status=400)
        try:
            target = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"error": "not_found"}, status=404)
        if target.pk == request.user.pk:
            return Response({"error": "cannot_change_own_role"}, status=400)
        old = target.role
        target.role = new_role
        target.save(update_fields=["role"])
        audit_log.info("role_change actor=%s target=%s %s->%s reason=%s",
                       request.user.pk, target.pk, old, new_role, reason)
        return Response({"id": target.pk, "old_role": old, "new_role": new_role})
