from django.conf import settings

from .roles import Role


NAV = {
    Role.ATTENDEE: [
        ("Overview", "/overview/"),
        ("Find events", "/events/"),
        ("My registrations", "/registrations/"),
    ],
    Role.ORGANIZER: [
        ("Overview", "/overview/"),
        ("My events", "/organizer/events/"),
        ("Create event", "/organizer/events/new/"),
        ("Reports", "/organizer/reports/"),
    ],
    Role.ADMINISTRATOR: [
        ("Overview", "/overview/"),
        ("Users & roles", "/users/"),
        ("Audit & alerts", "/audit/"),
    ],
}
PUBLIC_NAV = [("Explore events", "/events/")]


def rbac_context(request):
    user = getattr(request, "user", None)
    role = user.role if user is not None and user.is_authenticated else None
    path = request.path
    return {
        "current_role": role,
        "current_role_label": Role(role).label if role else "",
        "login_url": settings.LOGIN_URL,
        "nav_items": [
            {"label": label, "href": href, "active": path == href}
            for label, href in NAV.get(role, PUBLIC_NAV)
        ],
    }
