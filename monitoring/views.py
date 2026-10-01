from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.admin_utils import get_user_organization
from core.pagination import paginate
from core.views import SoftDeleteMixin

from .exports import XLSX_CONTENT_TYPE, build_maintenance_workbook
from .forms import MaintenanceFilterForm, MaintenanceForm
from .models import Maintenance


def scoped_maintenances(request):
    """
    Mantenciones visibles para el usuario: sin eliminadas lógicamente
    (Maintenance.objects) y solo de su organización (superusuario: todas).
    Lo usan el listado, las vistas de edición/eliminación y la exportación a Excel.
    """
    qs = Maintenance.objects.select_related("device", "technician")
    if not request.user.is_superuser:
        qs = qs.filter(device__zone__department__organization=get_user_organization(request))
    return qs.order_by("-scheduled_at", "pk")


def maintenance_filter_form(request):
    """Formulario de filtros (GET) con opciones limitadas a la organización del usuario."""
    organization = None if request.user.is_superuser else get_user_organization(request)
    return MaintenanceFilterForm(request.GET or None, organization=organization)


class MaintenanceScopedMixin:
    """Limita las mantenciones a los dispositivos de la organización del usuario."""

    raise_exception = True

    def get_organization(self):
        return get_user_organization(self.request)

    def get_queryset(self):
        return scoped_maintenances(self.request)


class MaintenanceListView(
    LoginRequiredMixin, PermissionRequiredMixin, MaintenanceScopedMixin, ListView
):
    permission_required = "monitoring.view_maintenance"
    template_name = "monitoring/maintenance_list.html"

    def get_filter_form(self):
        if not hasattr(self, "_filter_form"):
            self._filter_form = maintenance_filter_form(self.request)
        return self._filter_form

    def get_queryset(self):
        return self.get_filter_form().apply(super().get_queryset())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_obj, page_size, page_sizes = paginate(self.request, self.get_queryset())
        context.update(
            {
                "page_obj": page_obj,
                "page_size": page_size,
                "page_sizes": page_sizes,
                **self.get_filter_form().filter_context(),
            }
        )
        return context


class MaintenanceFormMixin(MaintenanceScopedMixin):
    form_class = MaintenanceForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("monitoring:maintenance_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.get_organization()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cancel_url"] = self.success_url
        return context


class MaintenanceCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    MaintenanceFormMixin,
    CreateView,
):
    permission_required = "monitoring.add_maintenance"
    success_message = "Mantención creada correctamente."
    extra_context = {"page_title": "Nueva mantención"}


class MaintenanceUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    MaintenanceFormMixin,
    UpdateView,
):
    permission_required = "monitoring.change_maintenance"
    success_message = "Mantención actualizada correctamente."
    extra_context = {"page_title": "Editar mantención"}


class MaintenanceDeleteView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    MaintenanceScopedMixin,
    SoftDeleteMixin,
    DeleteView,
):
    permission_required = "monitoring.delete_maintenance"
    success_url = reverse_lazy("monitoring:maintenance_list")
    success_message = "Mantención eliminada correctamente."


@login_required
@permission_required("monitoring.view_maintenance", raise_exception=True)
def maintenance_export(request):
    """
    Descarga .xlsx con las mantenciones que el usuario puede ver, aplicando
    además los filtros activos del listado (si los hay).
    """
    queryset = maintenance_filter_form(request).apply(scoped_maintenances(request))
    content = build_maintenance_workbook(queryset)
    filename = f"mantenciones_{timezone.localtime():%Y%m%d_%H%M}.xlsx"
    response = HttpResponse(content, content_type=XLSX_CONTENT_TYPE)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
