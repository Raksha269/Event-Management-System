from django.urls import path

from . import api_views

urlpatterns = [
    path("events/", api_views.EventListCreateAPIView.as_view(), name="api_events_list_create"),
    path("events/<int:pk>/", api_views.EventDetailUpdateAPIView.as_view(), name="api_events_detail_update"),
    path("events/<int:pk>/publish/", api_views.EventPublishAPIView.as_view(), name="api_events_publish"),
    path("events/<int:pk>/unpublish/", api_views.EventUnpublishAPIView.as_view(), name="api_events_unpublish"),
    path("events/<int:pk>/ticket-types/", api_views.EventTicketTypeListCreateAPIView.as_view(), name="api_events_ticket_types"),
    path("events/<int:pk>/registrations/", api_views.EventRegistrationAPIView.as_view(), name="api_events_registrations"),
    path("events/<int:pk>/reports/attendees.csv", api_views.EventAttendeesCSVReportAPIView.as_view(), name="api_event_report_csv"),
    path("admin/users/", api_views.AdminUserListAPIView.as_view(), name="api_admin_users_list"),
    path("admin/users/<int:pk>/", api_views.AdminUserDetailUpdateAPIView.as_view(), name="api_admin_users_detail_update"),
]
