from rest_framework.permissions import SAFE_METHODS, BasePermission

# Los nombres deben coincidir exactamente con los grupos creados en Django
# (los mismos que usa seed_ecoenergy).
GRUPO_ADMIN = "Administrador organizacional"
GRUPO_OPERADOR = "Operador"


class AccesoRecursoPorRol(BasePermission):
    """Administrador: CRUD. Operador: solo lectura. Sin grupo: 403."""

    message = "Tu rol no permite esta operación."

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if user.groups.filter(name=GRUPO_ADMIN).exists():
            return True
        if request.method in SAFE_METHODS:
            return user.groups.filter(name=GRUPO_OPERADOR).exists()
        return False
