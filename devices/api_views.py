from rest_framework import viewsets

from core.api import Conflicto, ProtegidoMixin, organizacion_del_usuario  # noqa: F401

from .models import Category, Device, Manufacturer
from .serializers import CategorySerializer, DeviceSerializer, ManufacturerSerializer


class DeviceViewSet(ProtegidoMixin, viewsets.ModelViewSet):
    # Device.objects ya excluye los registros eliminados lógicamente.
    queryset = Device.objects.select_related("zone", "category", "manufacturer").order_by("id")
    serializer_class = DeviceSerializer
    scope_path = "zone__department__organization"


class CategoryViewSet(ProtegidoMixin, viewsets.ModelViewSet):
    queryset = Category.objects.order_by("id")
    serializer_class = CategorySerializer

    def perform_destroy(self, instance):
        if instance.devices.exists():
            raise Conflicto("La categoría tiene dispositivos asociados.")
        super().perform_destroy(instance)


class ManufacturerViewSet(ProtegidoMixin, viewsets.ModelViewSet):
    queryset = Manufacturer.objects.order_by("id")
    serializer_class = ManufacturerSerializer

    def perform_destroy(self, instance):
        if instance.devices.exists():
            raise Conflicto("El fabricante tiene dispositivos asociados.")
        super().perform_destroy(instance)
