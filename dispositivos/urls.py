from django.urls import path
from . import views

app_name = "dispositivos"

urlpatterns = [
    path("", views.inicio, name="inicio"),
]

from django.urls import path
from . import views

app_name = "dispositivos"

urlpatterns = [
    path("dispositivos/", views.catalogo, name="catalogo"),
    path("", views.inicio, name="inicio"),
    path(
        "zonas/<int:zona_id>/dispositivos/",
        views.dispositivos_zona,
        name="por_zona",
    ),
]
