from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Device
from .permissions import AccesoRecursoPorRol
from .serializers import DeviceSerializer


def organizacion_del_usuario(user):
    """None para superusuario (ve todo); PermissionDenied si no tiene organización."""
    if user.is_superuser:
        return None
    profile = getattr(user, "profile", None)
    if profile is None or profile.organization_id is None:
        raise PermissionDenied("El usuario no posee una organización asignada.")
    return profile.organization


class DeviceViewSet(viewsets.ModelViewSet):
    # Device.objects ya excluye los registros eliminados lógicamente.
    queryset = Device.objects.select_related("zone", "category", "manufacturer").order_by("id")
    serializer_class = DeviceSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, AccesoRecursoPorRol]

    def get_queryset(self):
        # Alcance: solo dispositivos de la organización del usuario.
        qs = super().get_queryset()
        org = organizacion_del_usuario(self.request.user)
        if org is None:
            return qs
        return qs.filter(zone__department__organization=org)

    def perform_destroy(self, instance):
        # Misma política que la web: borrado lógico, no se borra la fila.
        instance.soft_delete()
