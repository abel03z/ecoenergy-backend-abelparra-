from django.urls import include, path
from rest_framework.routers import DefaultRouter

from monitoring.api_views import AlertViewSet, MeasurementViewSet
from organizations.api_views import ZoneViewSet

from .api_views import CategoryViewSet, DeviceViewSet, ManufacturerViewSet

router = DefaultRouter()
# Principales (CRUD)
router.register("devices", DeviceViewSet, basename="device")
router.register("zones", ZoneViewSet, basename="zone")
router.register("categories", CategoryViewSet, basename="category")
router.register("manufacturers", ManufacturerViewSet, basename="manufacturer")
# Operacionales (solo lectura)
router.register("measurements", MeasurementViewSet, basename="measurement")
router.register("alerts", AlertViewSet, basename="alert")

urlpatterns = [
    path("", include(router.urls)),
]
