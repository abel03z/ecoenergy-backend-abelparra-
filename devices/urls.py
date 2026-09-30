from django.urls import path
from . import views

app_name = "devices"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("categorias/", views.CategoriaListView.as_view(), name="categoria_list"),
    path("categorias/new/", views.CategoriaCreateView.as_view(), name="categoria_create"),
    path("categorias/<int:pk>/edit/", views.CategoriaUpdateView.as_view(), name="categoria_update"),
    path("categorias/<int:pk>/delete/", views.CategoriaDeleteView.as_view(), name="categoria_delete"),
]