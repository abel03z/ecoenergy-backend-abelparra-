from django.contrib import admin
from core.admin_filters import OrgScopedListFilter
from core.admin_utils import get_user_organization
from .models import Organizacion, Departamento, Zona

class DepartamentoInline(admin.TabularInline):
    model = Departamento
    extra = 0
    fields = ("nombre",)
    show_change_link = True


class DepartamentoOrganizacionFilter(OrgScopedListFilter):
    title = "organización"
    parameter_name = "organizacion"
    related_model = Organizacion
    related_field_lookup = None


class ZonaDepartamentoFilter(OrgScopedListFilter):
    title = "departamento"
    parameter_name = "departamento"
    related_model = Departamento
    related_field_lookup = "organizacion"


@admin.register(Organizacion)
class OrganizacionAdmin(admin.ModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)
    ordering = ("nombre",)
    inlines = [DepartamentoInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        organizacion = get_user_organization(request)
        return qs.filter(pk=organizacion.id)

    def has_change_permission(self, request, obj=None):
        allowed = super().has_change_permission(request, obj)
        if not allowed:
            return False
        if obj is None or request.user.is_superuser:
            return True
        organizacion = get_user_organization(request)
        return obj.id == organizacion.id

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "organizacion")
    search_fields = ("nombre", "organizacion__nombre")
    list_filter = (DepartamentoOrganizacionFilter,)
    ordering = ("organizacion__nombre", "nombre")
    list_select_related = ("organizacion",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        organizacion = get_user_organization(request)
        return qs.filter(organizacion=organizacion)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "organizacion" and not request.user.is_superuser:
            organizacion = get_user_organization(request)
            kwargs["queryset"] = Organizacion.objects.filter(pk=organizacion.id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_change_permission(self, request, obj=None):
        allowed = super().has_change_permission(request, obj)
        if not allowed:
            return False
        if obj is None or request.user.is_superuser:
            return True
        organizacion = get_user_organization(request)
        return obj.organizacion_id == organizacion.id

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Zona)
class ZonaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "departamento", "limite_consumo")
    search_fields = ("nombre", "departamento__nombre")
    list_filter = (ZonaDepartamentoFilter,)
    ordering = ("departamento__nombre", "nombre")
    list_select_related = ("departamento",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        organizacion = get_user_organization(request)
        return qs.filter(departamento__organizacion=organizacion)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "departamento" and not request.user.is_superuser:
            organizacion = get_user_organization(request)
            kwargs["queryset"] = Departamento.objects.filter(organizacion=organizacion)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_change_permission(self, request, obj=None):
        allowed = super().has_change_permission(request, obj)
        if not allowed:
            return False
        if obj is None or request.user.is_superuser:
            return True
        organizacion = get_user_organization(request)
        return obj.departamento.organizacion_id == organizacion.id

    def has_delete_permission(self, request, obj=None):
        return False
