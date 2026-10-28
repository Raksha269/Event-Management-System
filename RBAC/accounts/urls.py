from django.urls import path

from . import views

app_name = "rbac"

urlpatterns = [
    path("whoami/", views.WhoAmIView.as_view(), name="whoami"),
    path("attendee/", views.AttendeeAreaView.as_view(), name="attendee-area"),
    path("organizer/", views.OrganizerAreaView.as_view(), name="organizer-area"),
    path("admin-area/", views.AdminAreaView.as_view(), name="admin-area"),
    path("users/<int:user_id>/role/", views.ChangeRoleView.as_view(), name="change-role"),
]
