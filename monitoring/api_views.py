from rest_framework import viewsets

from core.api import ProtegidoMixin

from .models import Alert, Measurement
from .serializers import AlertSerializer, MeasurementSerializer

SCOPE = "device__zone__department__organization"


class MeasurementViewSet(ProtegidoMixin, viewsets.ReadOnlyModelViewSet):
    """Operacional: solo GET lista y detalle (la lista de mayor volumen, paginada)."""

    queryset = Measurement.objects.select_related("device").order_by("-measured_at", "id")
    serializer_class = MeasurementSerializer
    scope_path = SCOPE


class AlertViewSet(ProtegidoMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Alert.objects.select_related("device").order_by("-generated_at", "id")
    serializer_class = AlertSerializer
    scope_path = SCOPE
