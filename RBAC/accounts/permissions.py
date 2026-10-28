"""DRF permission classes. Usage:

    permission_classes = [IsAuthenticated, IsOrganizer, IsEventOwner]

Role check = what kind of user; Owner check = is it THEIR record.
Unauthenticated -> 401, authenticated but disallowed -> 403.
"""
from rest_framework.permissions import BasePermission

from .roles import Role


class HasRole(BasePermission):
    allowed_roles: tuple = ()

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated
                    and getattr(user, "role", None) in self.allowed_roles)


class IsAttendee(HasRole):
    allowed_roles = (Role.ATTENDEE,)


class IsOrganizer(HasRole):
    allowed_roles = (Role.ORGANIZER,)


class IsAdministrator(HasRole):
    allowed_roles = (Role.ADMINISTRATOR,)


class IsOwner(BasePermission):
    """Object-level: obj.<owner_field> must be the requesting user.
    Set owner_field on the view or use the subclasses below."""
    owner_field = "owner"

    def has_object_permission(self, request, view, obj):
        field = getattr(view, "owner_field", self.owner_field)
        owner = getattr(obj, field, None)
        owner_id = getattr(owner, "pk", owner)
        return owner_id is not None and owner_id == request.user.pk


class IsEventOwner(IsOwner):
    owner_field = "organizer"      # Event.organizer = FK(User)


class IsRegistrationOwner(IsOwner):
    owner_field = "attendee"       # Registration.attendee = FK(User)
