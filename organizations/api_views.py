from rest_framework import viewsets

from core.api import Conflicto, ProtegidoMixin

from .models import Zone
from .serializers import ZoneSerializer


class ZoneViewSet(ProtegidoMixin, viewsets.ModelViewSet):
    queryset = Zone.objects.select_related("department").order_by("id")
    serializer_class = ZoneSerializer
    scope_path = "department__organization"

    def perform_destroy(self, instance):
        if instance.devices.exists():
            raise Conflicto("La zona tiene dispositivos asociados.")
        super().perform_destroy(instance)
