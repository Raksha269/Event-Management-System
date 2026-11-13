from django.contrib import admin

from .models import (
    AuditEvent,
    Event,
    Payment,
    Refund,
    Registration,
    SecurityAlert,
    Ticket,
    TicketType,
    UserProfile,
)

admin.site.register(UserProfile)
admin.site.register(Event)
admin.site.register(TicketType)
admin.site.register(Registration)
admin.site.register(Payment)
admin.site.register(Ticket)
admin.site.register(Refund)
admin.site.register(SecurityAlert)


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = (
        "created_at", "action", "actor", "target_type", "target_id", "outcome"
    )
    list_filter = ("action", "outcome", "created_at")
    search_fields = ("action", "target_type", "target_id", "request_id")
    readonly_fields = tuple(field.name for field in AuditEvent._meta.fields)
    ordering = ("-created_at", "-pk")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
