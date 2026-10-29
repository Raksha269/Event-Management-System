from django.urls import path

from . import views

urlpatterns = [
    path("users/", views.admin_user_list, name="admin_user_list"),
    path("users/<int:pk>/toggle-active/", views.admin_user_toggle_active, name="admin_user_toggle_active"),
    path("users/<int:pk>/role/", views.admin_user_change_role, name="admin_user_change_role"),
]
