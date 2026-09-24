from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("devices/", include("devices.urls")),
    path("", include("dispositivos.urls")),
]