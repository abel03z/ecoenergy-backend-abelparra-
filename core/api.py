"""Piezas compartidas por la API REST (Evaluación sumativa 3)."""
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from devices.permissions import AccesoRecursoPorRol


class Conflicto(APIException):
    """409: la operación choca con el estado actual (p. ej. borrar algo en uso)."""

    status_code = 409
    default_detail = "La operación no se puede realizar por el estado actual del recurso."
    default_code = "conflict"


def organizacion_del_usuario(user):
    """None para superusuario (ve todo); PermissionDenied si no tiene organización."""
    if user.is_superuser:
        return None
    profile = getattr(user, "profile", None)
    if profile is None or profile.organization_id is None:
        raise PermissionDenied("El usuario no posee una organización asignada.")
    return profile.organization


class ProtegidoMixin:
    """JWT + permiso por rol + alcance por organización para los seis recursos.

    scope_path: ruta ORM desde el modelo hasta Organization (None = recurso global).
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, AccesoRecursoPorRol]
    scope_path = None

    def get_queryset(self):
        qs = super().get_queryset()
        org = organizacion_del_usuario(self.request.user)
        if org is not None and self.scope_path:
            qs = qs.filter(**{self.scope_path: org})
        return qs

    def perform_destroy(self, instance):
        # Borrado lógico (se explica en el README): la fila no se elimina.
        instance.soft_delete()
