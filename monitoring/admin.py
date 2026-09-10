from django.contrib import admin
from .models import Medicion, Alerta, Mantenimiento


@admin.register(Medicion)
class MedicionAdmin(admin.ModelAdmin):
    list_display = ("dispositivo", "valor_consumo", "fecha_hora")
    search_fields = ("dispositivo__nombre",)
    list_filter = ("dispositivo",)
    ordering = ("-fecha_hora",)
    date_hierarchy = "fecha_hora"
    list_select_related = ("dispositivo",)


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ("dispositivo", "estado", "fecha_generada")
    search_fields = ("dispositivo__nombre",)
    list_filter = ("estado", "dispositivo")
    ordering = ("-fecha_generada",)
    date_hierarchy = "fecha_generada"
    list_select_related = ("dispositivo",)

@admin.register(Mantenimiento)
class MantenimientoAdmin(admin.ModelAdmin):
    list_display = ("dispositivo", "tipo", "estado", "fecha_programada")
    search_fields = ("dispositivo__nombre", "tipo")
    list_filter = ("estado", "dispositivo")
    ordering = ("-fecha_programada",)
    date_hierarchy = "fecha_programada"
    list_select_related = ("dispositivo",)