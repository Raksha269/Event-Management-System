from django.urls import path
from .auth_views import LoginView
app_name = "auth"
urlpatterns = [path("login/", LoginView.as_view(), name="login")]
