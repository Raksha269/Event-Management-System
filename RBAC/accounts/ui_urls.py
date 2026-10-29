from django.urls import path

from . import ui_views

app_name = "ui"

urlpatterns = [
    path("", ui_views.home, name="home"),
    path("overview/", ui_views.overview, name="overview"),
    path("users/", ui_views.users, name="users"),
    path("users/<int:user_id>/role/", ui_views.role_change, name="role-change"),
]
