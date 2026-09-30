from django.contrib import admin

from core.admin_filters import OrgScopedListFilter
from core.admin_utils import get_user_organization
from devices.models import Device

from .models import Alert, Maintenance, Measurement


class DeviceScopedFilter(OrgScopedListFilter):
    title = "dispositivo"
    parameter_name = "device"
    related_model = Device
    related_field_lookup = "zone__department__organization"


class DeviceScopedAdminMixin:
    """Limita el listado y el selector de dispositivo a la organización del usuario."""

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.filter(deleted_at__isnull=True)
        if request.user.is_superuser:
            return qs
        organization = get_user_organization(request)
        return qs.filter(device__zone__department__organization=organization)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "device" and not request.user.is_superuser:
            organization = get_user_organization(request)
            kwargs["queryset"] = Device.objects.filter(
                zone__department__organization=organization,
                deleted_at__isnull=True,
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Measurement)
class MeasurementAdmin(DeviceScopedAdminMixin, admin.ModelAdmin):
    list_display = ("device", "consumption_value", "measured_at")
    search_fields = ("device__name",)
    list_filter = (DeviceScopedFilter,)
    ordering = ("-measured_at",)
    date_hierarchy = "measured_at"
    list_select_related = ("device",)


@admin.register(Alert)
class AlertAdmin(DeviceScopedAdminMixin, admin.ModelAdmin):
    list_display = ("device", "level", "status", "generated_at")
    search_fields = ("device__name", "message")
    list_filter = ("level", "status", DeviceScopedFilter)
    ordering = ("-generated_at",)
    date_hierarchy = "generated_at"
    list_select_related = ("device",)


@admin.register(Maintenance)
class MaintenanceAdmin(DeviceScopedAdminMixin, admin.ModelAdmin):
    list_display = ("device", "type", "status", "technician", "scheduled_at")
    search_fields = ("device__name", "type", "technician__username")
    list_filter = ("type", "status", DeviceScopedFilter)
    ordering = ("-scheduled_at",)
    date_hierarchy = "scheduled_at"
    list_select_related = ("device", "technician")
