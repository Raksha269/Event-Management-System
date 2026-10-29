from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/rbac/", include("accounts.urls")),
    path("", include("accounts.ui_urls")),
]

handler403 = "accounts.views.forbidden"   # RBAC
handler404 = "accounts.views.not_found"   # RBAC
