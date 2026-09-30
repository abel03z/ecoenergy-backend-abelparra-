from django.contrib import admin

from core.admin_filters import OrgScopedListFilter
from core.admin_utils import get_user_organization

from .models import Department, Organization, Zone


class DepartmentInline(admin.TabularInline):
    model = Department
    extra = 0
    fields = ("name",)
    show_change_link = True


class DepartmentOrganizationFilter(OrgScopedListFilter):
    title = "organización"
    parameter_name = "organization"
    related_model = Organization
    related_field_lookup = None


class ZoneDepartmentFilter(OrgScopedListFilter):
    title = "departamento"
    parameter_name = "department"
    related_model = Department
    related_field_lookup = "organization"


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)
    inlines = [DepartmentInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        organization = get_user_organization(request)
        return qs.filter(pk=organization.id)

    def has_change_permission(self, request, obj=None):
        allowed = super().has_change_permission(request, obj)
        if not allowed:
            return False
        if obj is None or request.user.is_superuser:
            return True
        organization = get_user_organization(request)
        return obj.id == organization.id

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "organization")
    search_fields = ("name", "organization__name")
    list_filter = (DepartmentOrganizationFilter,)
    ordering = ("organization__name", "name")
    list_select_related = ("organization",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        organization = get_user_organization(request)
        return qs.filter(organization=organization)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "organization" and not request.user.is_superuser:
            organization = get_user_organization(request)
            kwargs["queryset"] = Organization.objects.filter(pk=organization.id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_change_permission(self, request, obj=None):
        allowed = super().has_change_permission(request, obj)
        if not allowed:
            return False
        if obj is None or request.user.is_superuser:
            return True
        organization = get_user_organization(request)
        return obj.organization_id == organization.id

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "department", "consumption_limit")
    search_fields = ("name", "department__name")
    list_filter = (ZoneDepartmentFilter,)
    ordering = ("department__name", "name")
    list_select_related = ("department",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        organization = get_user_organization(request)
        return qs.filter(department__organization=organization)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "department" and not request.user.is_superuser:
            organization = get_user_organization(request)
            kwargs["queryset"] = Department.objects.filter(organization=organization)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_change_permission(self, request, obj=None):
        allowed = super().has_change_permission(request, obj)
        if not allowed:
            return False
        if obj is None or request.user.is_superuser:
            return True
        organization = get_user_organization(request)
        return obj.department.organization_id == organization.id

    def has_delete_permission(self, request, obj=None):
        return False
