from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class EMSUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("EMS", {"fields": ("role",)}),)
    list_display = ("username", "email", "role", "is_active")
    list_filter = ("role", "is_active")
