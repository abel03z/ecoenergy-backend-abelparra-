from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.admin_utils import get_user_organization
from core.pagination import paginate
from core.views import SoftDeleteMixin

from .forms import ZoneForm
from .models import Zone


class ZoneScopedMixin:
    """Limita las zonas a la organización del usuario (superusuario: todas)."""

    raise_exception = True

    def get_organization(self):
        return get_user_organization(self.request)

    def get_queryset(self):
        # Zone.objects ya excluye las zonas eliminadas lógicamente.
        qs = Zone.objects.select_related("department__organization")
        if not self.request.user.is_superuser:
            qs = qs.filter(department__organization=self.get_organization())
        return qs.order_by("name")


class ZoneListView(LoginRequiredMixin, PermissionRequiredMixin, ZoneScopedMixin, ListView):
    permission_required = "organizations.view_zone"
    template_name = "organizations/zone_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_obj, page_size, page_sizes = paginate(self.request, self.get_queryset())
        context.update(
            {"page_obj": page_obj, "page_size": page_size, "page_sizes": page_sizes}
        )
        return context


class ZoneFormMixin(ZoneScopedMixin):
    form_class = ZoneForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("organizations:zone_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.get_organization()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cancel_url"] = self.success_url
        return context


class ZoneCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, ZoneFormMixin, CreateView
):
    permission_required = "organizations.add_zone"
    success_message = "Zona creada correctamente."
    extra_context = {"page_title": "Nueva zona"}


class ZoneUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, ZoneFormMixin, UpdateView
):
    permission_required = "organizations.change_zone"
    success_message = "Zona actualizada correctamente."
    extra_context = {"page_title": "Editar zona"}


class ZoneDeleteView(
    LoginRequiredMixin, PermissionRequiredMixin, ZoneScopedMixin, SoftDeleteMixin, DeleteView
):
    permission_required = "organizations.delete_zone"
    success_url = reverse_lazy("organizations:zone_list")
    success_message = "Zona eliminada correctamente."

    def can_soft_delete(self):
        # Device.objects solo cuenta dispositivos vivos.
        if self.object.devices.exists():
            return False, (
                "No se puede eliminar esta zona porque tiene dispositivos asociados."
            )
        return True, ""
