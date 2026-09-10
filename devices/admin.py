from django.contrib import admin
from .models import Categoria, Dispositivo


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)
    ordering = ("nombre",)


@admin.register(Dispositivo)
class DispositivoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "zona")
    search_fields = ("nombre", "categoria__nombre", "zona__nombre")
    list_filter = ("categoria", "zona")
    ordering = ("zona__nombre", "nombre")
    list_select_related = ("categoria", "zona")