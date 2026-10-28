
from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path(
        "verify/<str:token>/",
        views.verify_email,
        name="verify_email",
    ),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
]
