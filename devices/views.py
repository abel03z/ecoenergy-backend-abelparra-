from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from core.admin_utils import get_user_organization
from core.pagination import paginate
from core.views import SoftDeleteMixin
from .models import Category, Device
from .forms import CategoryForm, DeviceFilterForm, DeviceForm


@login_required
@permission_required("devices.view_device", raise_exception=True)
def dashboard(request):
    # Device.objects ya excluye los eliminados lógicamente.
    if request.user.is_superuser:
        devices = Device.objects.all()
        organization = None
    else:
        organization = get_user_organization(request)
        devices = Device.objects.filter(zone__department__organization=organization)

    filter_form = DeviceFilterForm(request.GET or None, organization=organization)
    devices = filter_form.apply(devices)

    devices = devices.select_related("zone", "category", "manufacturer").order_by("name")
    page_obj, page_size, page_sizes = paginate(request, devices)

    return render(
        request,
        "devices/dashboard.html",
        {
            "page_obj": page_obj,
            "page_size": page_size,
            "page_sizes": page_sizes,
            "organization": organization,
            "filter_form": filter_form,
            "base_query": filter_form.query_string(),
            "has_filters": bool(filter_form.query_string()),
        },
    )


class CategoryPageContextMixin:
    """Agrega al contexto el listado paginado de categorías (tabla + modal)."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_obj, page_size, page_sizes = paginate(
            self.request, Category.objects.order_by("name")
        )
        context.update(
            {
                "categories": page_obj,
                "page_obj": page_obj,
                "page_size": page_size,
                "page_sizes": page_sizes,
            }
        )
        return context


class CategoryListView(
    LoginRequiredMixin, PermissionRequiredMixin, CategoryPageContextMixin, ListView
):
    permission_required = "devices.view_category"
    raise_exception = True
    model = Category
    template_name = "devices/category_list.html"

    def get_queryset(self):
        return Category.objects.order_by("name")


class CategoryCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    CategoryPageContextMixin,
    CreateView,
):
    permission_required = "devices.add_category"
    raise_exception = True
    model = Category
    form_class = CategoryForm
    template_name = "devices/category_list.html"
    success_url = reverse_lazy("devices:category_list")
    success_message = "Categoría creada correctamente."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["open_modal"] = True
        return context


class CategoryUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    CategoryPageContextMixin,
    UpdateView,
):
    permission_required = "devices.change_category"
    raise_exception = True
    model = Category
    form_class = CategoryForm
    template_name = "devices/category_list.html"
    success_url = reverse_lazy("devices:category_list")
    success_message = "Categoría actualizada correctamente."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["open_modal"] = True
        return context


class CategoryDeleteView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SoftDeleteMixin,
    DeleteView,
):
    permission_required = "devices.delete_category"
    raise_exception = True
    model = Category
    success_url = reverse_lazy("devices:category_list")
    success_message = "Categoría eliminada correctamente."

    def can_soft_delete(self):
        # Device.objects solo cuenta dispositivos vivos.
        if self.object.devices.exists():
            return False, (
                "No se puede eliminar esta categoría porque tiene "
                "dispositivos asociados. Reasígnalos o elimínalos primero."
            )
        return True, ""


# ---------------------------------------------------------------------------
# Clase 8 · CRUD de Dispositivo con imagen (scoping por organización)
# ---------------------------------------------------------------------------

def _delete_file_after_commit(storage, name):
    """Borra un archivo del storage solo si la transacción termina bien."""
    if name:
        transaction.on_commit(lambda: storage.delete(name))


class DeviceScopedMixin:
    """Limita el queryset a la organización del usuario (superusuario: todo)."""

    def get_organization(self):
        return get_user_organization(self.request)

    def get_queryset(self):
        qs = Device.objects.all()
        if self.request.user.is_superuser:
            return qs
        return qs.filter(zone__department__organization=self.get_organization())


class DeviceFormMixin(DeviceScopedMixin):
    model = Device
    form_class = DeviceForm
    template_name = "devices/device_form.html"
    success_url = reverse_lazy("devices:dashboard")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.get_organization()
        return kwargs


class DeviceCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    DeviceFormMixin,
    CreateView,
):
    permission_required = "devices.add_device"
    raise_exception = True
    success_message = "Dispositivo creado correctamente."


class DeviceUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    DeviceFormMixin,
    UpdateView,
):
    permission_required = "devices.change_device"
    raise_exception = True
    success_message = "Dispositivo actualizado correctamente."

    def form_valid(self, form):
        # Política: al reemplazar o limpiar la imagen, se elimina el archivo anterior.
        old_file = Device.objects.get(pk=self.object.pk).image
        old_name, storage = old_file.name, old_file.storage
        response = super().form_valid(form)
        if old_name and old_name != self.object.image.name:
            _delete_file_after_commit(storage, old_name)
        return response


class DeviceDeleteView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    DeviceScopedMixin,
    SoftDeleteMixin,
    DeleteView,
):
    permission_required = "devices.delete_device"
    raise_exception = True
    success_url = reverse_lazy("devices:dashboard")
    success_message = "Dispositivo eliminado correctamente."
    # Borrado lógico: el registro y su imagen se conservan (se puede restaurar).
