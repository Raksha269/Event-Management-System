from django.contrib import admin
from django.urls import include, path

from events import views as event_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("events.urls")),
    path("events/", include("events.event_urls")),
    path("api/v1/", include("events.api_urls")),
    path("", event_views.discover_events, name="home"),
]
