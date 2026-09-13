from django.contrib import admin
from core.admin_utils import get_user_organization
from devices.models import Dispositivo
from .models import Medicion, Alerta, Mantenimiento


@admin.register(Medicion)
class MedicionAdmin(admin.ModelAdmin):
    list_display = ("dispositivo", "valor_consumo", "fecha_hora")
    search_fields = ("dispositivo__nombre",)
    list_filter = ("dispositivo",)
    ordering = ("-fecha_hora",)
    date_hierarchy = "fecha_hora"
    list_select_related = ("dispositivo",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.filter(deleted_at__isnull=True)
        if request.user.is_superuser:
            return qs
        organizacion = get_user_organization(request)
        return qs.filter(dispositivo__zona__departamento__organizacion=organizacion)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "dispositivo" and not request.user.is_superuser:
            organizacion = get_user_organization(request)
            kwargs["queryset"] = Dispositivo.objects.filter(
                zona__departamento__organizacion=organizacion,
                deleted_at__isnull=True,
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ("dispositivo", "estado", "fecha_generada")
    search_fields = ("dispositivo__nombre",)
    list_filter = ("estado", "dispositivo")
    ordering = ("-fecha_generada",)
    date_hierarchy = "fecha_generada"
    list_select_related = ("dispositivo",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.filter(deleted_at__isnull=True)
        if request.user.is_superuser:
            return qs
        organizacion = get_user_organization(request)
        return qs.filter(dispositivo__zona__departamento__organizacion=organizacion)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "dispositivo" and not request.user.is_superuser:
            organizacion = get_user_organization(request)
            kwargs["queryset"] = Dispositivo.objects.filter(
                zona__departamento__organizacion=organizacion,
                deleted_at__isnull=True,
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Mantenimiento)
class MantenimientoAdmin(admin.ModelAdmin):
    list_display = ("dispositivo", "tipo", "estado", "fecha_programada")
    search_fields = ("dispositivo__nombre", "tipo")
    list_filter = ("estado", "dispositivo")
    ordering = ("-fecha_programada",)
    date_hierarchy = "fecha_programada"
    list_select_related = ("dispositivo",)
