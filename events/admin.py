from django.contrib import admin

from .models import (
    Event,
    Payment,
    Refund,
    Registration,
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
