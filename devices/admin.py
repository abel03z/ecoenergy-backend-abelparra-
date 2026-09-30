from django.contrib import admin, messages
from django.utils import timezone

from core.admin_filters import OrgScopedListFilter
from core.admin_utils import get_user_organization
from organizations.models import Zone

from .models import Category, Device, DeviceAssignment, Manufacturer


class DeviceZoneFilter(OrgScopedListFilter):
    title = "zona"
    parameter_name = "zone"
    related_model = Zone
    related_field_lookup = "department__organization"


class AssignmentDeviceFilter(OrgScopedListFilter):
    title = "dispositivo"
    parameter_name = "device"
    related_model = Device
    related_field_lookup = "zone__department__organization"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ("name", "country")
    search_fields = ("name", "country")
    ordering = ("name",)


@admin.action(description="Archivar dispositivos seleccionados", permissions=["change"])
def archive_devices(modeladmin, request, queryset):
    updated = queryset.filter(deleted_at__isnull=True).update(deleted_at=timezone.now())
    modeladmin.message_user(
        request, f"{updated} dispositivo(s) archivado(s).", level=messages.SUCCESS
    )


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "manufacturer", "zone", "is_active")
    search_fields = ("name", "category__name", "manufacturer__name", "zone__name")
    list_filter = ("category", "manufacturer", DeviceZoneFilter)
    ordering = ("zone__name", "name")
    list_select_related = ("category", "manufacturer", "zone")
    actions = [archive_devices]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.filter(deleted_at__isnull=True)
        if request.user.is_superuser:
            return qs
        organization = get_user_organization(request)
        return qs.filter(zone__department__organization=organization)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "zone" and not request.user.is_superuser:
            organization = get_user_organization(request)
            kwargs["queryset"] = Zone.objects.filter(
                department__organization=organization,
                deleted_at__isnull=True,
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_change_permission(self, request, obj=None):
        allowed = super().has_change_permission(request, obj)
        if not allowed:
            return False
        if obj is None or request.user.is_superuser:
            return True
        organization = get_user_organization(request)
        return obj.zone.department.organization_id == organization.id

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DeviceAssignment)
class DeviceAssignmentAdmin(admin.ModelAdmin):
    list_display = ("device", "user", "assigned_at", "released_at")
    search_fields = ("device__name", "user__username")
    list_filter = (AssignmentDeviceFilter,)
    ordering = ("-assigned_at",)
    date_hierarchy = "assigned_at"
    list_select_related = ("device", "user")

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
        if db_field.name == "user" and not request.user.is_superuser:
            organization = get_user_organization(request)
            kwargs["queryset"] = db_field.related_model.objects.filter(
                profile__organization=organization
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_delete_permission(self, request, obj=None):
        return False
