"""Role change logic shared by the API view and the admin UI."""
import logging

from .roles import Role

audit_log = logging.getLogger("ems.audit")   # AuditModule owner can attach a handler


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
    old = target.role
    target.role = new_role
    target.save(update_fields=["role"])
    audit_log.info("role_change actor=%s target=%s %s->%s reason=%s",
                   actor.pk, target.pk, old, new_role, reason)
    return old
