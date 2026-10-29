from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .permissions import IsAdministrator, IsAttendee, IsOrganizer
from .services import RoleChangeError, change_user_role


def not_found(request, exception=None):
    return render(request, "404.html", status=404)


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
        try:
            target = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"error": "not_found"}, status=404)
        try:
            old = change_user_role(actor=request.user, target=target,
                                   new_role=request.data.get("role"),
                                   reason=request.data.get("reason"))
        except RoleChangeError as exc:
            return Response({"error": exc.code}, status=400)
        return Response({"id": target.pk, "old_role": old, "new_role": target.role})
