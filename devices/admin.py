from django.contrib import admin, messages
from django.utils import timezone
from core.admin_filters import OrgScopedListFilter
from core.admin_utils import get_user_organization
from organizations.models import Zona
from .models import Categoria, Dispositivo


class DispositivoZonaFilter(OrgScopedListFilter):
    title = "zona"
    parameter_name = "zona"
    related_model = Zona
    related_field_lookup = "departamento__organizacion"


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)
    ordering = ("nombre",)


@admin.action(description="Archivar dispositivos seleccionados", permissions=["change"])
def archive_dispositivos(modeladmin, request, queryset):
    updated = queryset.filter(deleted_at__isnull=True).update(deleted_at=timezone.now())
    modeladmin.message_user(
        request, f"{updated} dispositivo(s) archivado(s).", level=messages.SUCCESS
    )


@admin.register(Dispositivo)
class DispositivoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "zona")
    search_fields = ("nombre", "categoria__nombre", "zona__nombre")
    list_filter = ("categoria", DispositivoZonaFilter)
    ordering = ("zona__nombre", "nombre")
    list_select_related = ("categoria", "zona")
    actions = [archive_dispositivos]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.filter(deleted_at__isnull=True)
        if request.user.is_superuser:
            return qs
        organizacion = get_user_organization(request)
        return qs.filter(zona__departamento__organizacion=organizacion)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "zona" and not request.user.is_superuser:
            organizacion = get_user_organization(request)
            kwargs["queryset"] = Zona.objects.filter(
                departamento__organizacion=organizacion,
                deleted_at__isnull=True,
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_change_permission(self, request, obj=None):
        allowed = super().has_change_permission(request, obj)
        if not allowed:
            return False
        if obj is None or request.user.is_superuser:
            return True
        organizacion = get_user_organization(request)
        return obj.zona.departamento.organizacion_id == organizacion.id

    def has_delete_permission(self, request, obj=None):
        return False
