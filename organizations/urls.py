from django.urls import path

from . import views

app_name = "organizations"

urlpatterns = [
    path("zones/", views.ZoneListView.as_view(), name="zone_list"),
    path("zones/new/", views.ZoneCreateView.as_view(), name="zone_create"),
    path("zones/<int:pk>/edit/", views.ZoneUpdateView.as_view(), name="zone_update"),
    path("zones/<int:pk>/delete/", views.ZoneDeleteView.as_view(), name="zone_delete"),
]
