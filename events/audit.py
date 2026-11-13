"""Helpers for durable, privacy-conscious audit records."""

from .models import AuditEvent


def record_audit_event(
    action, *, actor=None, target=None, outcome="success", request=None
):
    """Persist a business/security action without copying sensitive request data."""
    target_type = target.__class__.__name__ if target is not None else ""
    target_id = str(target.pk) if target is not None and target.pk is not None else ""
    meta = getattr(request, "META", {}) if request is not None else {}
    # Do not trust client-supplied forwarding headers for audit metadata.
    ip_address = meta.get("REMOTE_ADDR") or None
    request_id = getattr(request, "request_id", "") if request is not None else ""
    return AuditEvent.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        outcome=outcome,
        request_id=request_id[:64],
        ip_address=ip_address,
    )
