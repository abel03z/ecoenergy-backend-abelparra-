from rest_framework import viewsets

from .models import Device
from .serializers import DeviceSerializer


class DeviceViewSet(viewsets.ModelViewSet):
    # Device.objects ya excluye los registros eliminados lógicamente.
    queryset = Device.objects.select_related("zone", "category", "manufacturer").order_by("id")
    serializer_class = DeviceSerializer

    def perform_destroy(self, instance):
        # Misma política que la web: borrado lógico, no se borra la fila.
        instance.soft_delete()
