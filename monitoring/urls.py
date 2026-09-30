from django.urls import path

from . import views

app_name = "monitoring"

urlpatterns = [
    path("maintenances/", views.MaintenanceListView.as_view(), name="maintenance_list"),
    path("maintenances/export/", views.maintenance_export, name="maintenance_export"),
    path("maintenances/new/", views.MaintenanceCreateView.as_view(), name="maintenance_create"),
    path("maintenances/<int:pk>/edit/", views.MaintenanceUpdateView.as_view(), name="maintenance_update"),
    path("maintenances/<int:pk>/delete/", views.MaintenanceDeleteView.as_view(), name="maintenance_delete"),
]
