"""
Filtros de Django Admin reutilizables que restringen las OPCIONES mostradas
en el panel "FILTER" (barra lateral derecha) a la organización del usuario
logueado, además de la restricción de datos que ya hace get_queryset().

Sin esto, get_queryset() sigue protegiendo los datos reales, pero el
desplegable de filtros muestra igual los nombres de zonas/departamentos/
dispositivos de otras organizaciones (fuga cosmética de información).
"""
from django.contrib import admin

from core.admin_utils import get_user_organization


class OrgScopedListFilter(admin.SimpleListFilter):
    """
    Filtro base. Cada subclase debe definir:
    - title, parameter_name (igual que cualquier SimpleListFilter)
    - related_model: el modelo sobre el que se filtra (ej. Zona, Dispositivo)
    - related_field_lookup: el lookup desde related_model hasta Organizacion
      (ej. "organizacion", "departamento__organizacion",
      "zona__departamento__organizacion"). Usar None si related_model ES
      Organizacion.
    """

    related_model = None
    related_field_lookup = None

    def lookups(self, request, model_admin):
        qs = self.related_model.objects.all()
        if not request.user.is_superuser:
            organizacion = get_user_organization(request)
            if self.related_field_lookup:
                qs = qs.filter(**{self.related_field_lookup: organizacion})
            else:
                qs = qs.filter(pk=organizacion.id)
        return [(obj.pk, str(obj)) for obj in qs]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(**{f"{self.parameter_name}__id": self.value()})
        return queryset
