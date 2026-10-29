from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect, render

from .decorators import role_required
from .roles import Role
from .services import RoleChangeError, change_user_role

User = get_user_model()

CARDS = {
    Role.ATTENDEE: [
        {"title": "Find events", "text": "Browse upcoming events and register.", "action": "Find events", "href": "/events/"},
        {"title": "My registrations", "text": "See your tickets and registration status.", "action": "View registrations", "href": "/registrations/"}],
    Role.ORGANIZER: [
        {"title": "Create an event", "text": "Set up details, tickets and capacity.", "action": "Create event", "href": "/organizer/events/new/"},
        {"title": "My events", "text": "Manage drafts and published events.", "action": "View my events", "href": "/organizer/events/"}],
    Role.ADMINISTRATOR: [
        {"title": "Users & roles", "text": "Search accounts and manage roles.", "action": "Manage users", "href": "/users/"},
        {"title": "Audit & alerts", "text": "Review security events.", "action": "Open audit log", "href": "/audit/"}],
}


def home(request):
    return redirect("ui:overview")


@role_required(*Role.values)
def overview(request):
    return render(request, "accounts/overview.html", {"cards": CARDS[request.user.role]})


@role_required(Role.ADMINISTRATOR)
def users(request):
    q = request.GET.get("q", "").strip()
    role = request.GET.get("role", "")
    qs = User.objects.order_by("username")
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q))
    if role in Role.values:
        qs = qs.filter(role=role)
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    return render(request, "accounts/users.html",
                  {"page": page, "q": q, "role": role, "roles": Role.choices})


ERROR_TEXT = {
    "invalid_role": ("role", "Choose a valid role."),
    "reason_required": ("reason", "Enter a reason for the change."),
    "cannot_change_own_role": ("role", "You can't change your own role."),
}


@role_required(Role.ADMINISTRATOR)
def role_change(request, user_id):
    try:
        target = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        raise Http404
    ctx = {"target": target, "roles": Role.choices, "selected": target.role, "reason": "", "errors": {}}
    if request.method == "POST":
        ctx["selected"] = request.POST.get("role", "")
        ctx["reason"] = request.POST.get("reason", "")
        if not request.POST.get("confirm"):
            ctx["errors"]["confirm"] = "Tick the box to confirm."
        try:
            if not ctx["errors"]:
                change_user_role(actor=request.user, target=target,
                                 new_role=ctx["selected"], reason=ctx["reason"])
                messages.success(request, f"{target.username} is now {Role(ctx['selected']).label}.")
                return redirect("ui:users")
        except RoleChangeError as exc:
            field, msg = ERROR_TEXT[exc.code]
            ctx["errors"][field] = msg
        if ctx["errors"] and "confirm" in ctx["errors"]:
            if ctx["selected"] not in Role.values:
                ctx["errors"]["role"] = ERROR_TEXT["invalid_role"][1]
            if not ctx["reason"].strip():
                ctx["errors"]["reason"] = ERROR_TEXT["reason_required"][1]
            if target.pk == request.user.pk:
                ctx["errors"]["role"] = ERROR_TEXT["cannot_change_own_role"][1]
        return render(request, "accounts/role_change.html", ctx, status=400)
    return render(request, "accounts/role_change.html", ctx)
