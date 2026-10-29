from django.urls import path

from . import views

urlpatterns = [
    path("", views.organizer_dashboard, name="organizer_dashboard"),
    path("discover/", views.discover_events, name="discover_events"),
    path("create/", views.event_create, name="event_create"),
    path("<int:pk>/", views.event_detail, name="event_detail"),
    path("<int:pk>/edit/", views.event_edit, name="event_edit"),
    path("<int:pk>/publish/", views.event_publish, name="event_publish"),
    path("<int:pk>/unpublish/", views.event_unpublish, name="event_unpublish"),
    path("<int:pk>/tickets/", views.ticket_types_manage, name="ticket_types_manage"),
    path("<int:pk>/register/", views.event_register, name="event_register"),
    path("<int:pk>/report/", views.event_report, name="event_report"),
    path("<int:pk>/report/attendees.csv", views.event_report_csv, name="event_report_csv"),
]
