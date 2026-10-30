import logging

from .roles import Role

audit_log = logging.getLogger("ems.audit")


class RoleChangeError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def change_user_role(*, actor, target, new_role, reason):
    if new_role not in Role.values:
        raise RoleChangeError("invalid_role")
    reason = (reason or "").strip()
    if not reason:
        raise RoleChangeError("reason_required")
    if target.pk == actor.pk:
        raise RoleChangeError("cannot_change_own_role")

    from .models import UserProfile

    old_role = target.role
    profile, _ = UserProfile.objects.get_or_create(user=target)
    profile.role = new_role
    profile.save(update_fields=["role"])
    audit_log.info(
        "role_change actor=%s target=%s %s->%s reason=%s",
        actor.pk,
        target.pk,
        old_role,
        new_role,
        reason,
    )
    return old_role
