from django.contrib import admin, messages
from django.utils import timezone


@admin.action(description="Archivar dispositivos seleccionados", permissions=["change"])
def archive_dispositivos(modeladmin, request, queryset):
    updated = queryset.filter(deleted_at__isnull=True).update(deleted_at=timezone.now())
    modeladmin.message_user(
        request, f"{updated} dispositivo(s) archivado(s).", level=messages.SUCCESS
    )

# dentro de DispositivoAdmin:
class DispositivoAdmin(admin.ModelAdmin):
    actions = [archive_dispositivos]

    def has_delete_permission(self, request, obj=None):
        return False
