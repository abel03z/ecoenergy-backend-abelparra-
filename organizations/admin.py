from django.contrib import admin
from .models import Organizacion, Departamento, Zona


@admin.register(Organizacion)
class OrganizacionAdmin(admin.ModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)
    ordering = ("nombre",)


@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "organizacion")
    search_fields = ("nombre", "organizacion__nombre")
    list_filter = ("organizacion",)
    ordering = ("organizacion__nombre", "nombre")
    list_select_related = ("organizacion",)


@admin.register(Zona)
class ZonaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "departamento", "limite_consumo")
    search_fields = ("nombre", "departamento__nombre")
    list_filter = ("departamento",)
    ordering = ("departamento__nombre", "nombre")
    list_select_related = ("departamento",)