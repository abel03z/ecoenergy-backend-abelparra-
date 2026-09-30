from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import ProtectedError
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from core.admin_utils import get_user_organization
from .models import Category, Device
from .forms import CategoryForm, DeviceForm

ALLOWED_PAGE_SIZES = {5, 10, 15}


@login_required
@permission_required("devices.view_device", raise_exception=True)
def dashboard(request):
    if request.user.is_superuser:
        devices = Device.objects.filter(deleted_at__isnull=True)
        organization = None
    else:
        organization = get_user_organization(request)
        devices = Device.objects.filter(
            zone__department__organization=organization,
            deleted_at__isnull=True,
        )

    devices = devices.select_related("zone", "category", "manufacturer").order_by("name")

    # 1. Leer page_size desde la URL
    raw_size = request.GET.get("page_size")
    if raw_size:
        try:
            selected_size = int(raw_size)
        except ValueError:
            selected_size = 5
        # 2. Guardar solamente tamaños permitidos
        if selected_size in ALLOWED_PAGE_SIZES:
            request.session["device_page_size"] = selected_size

    # 3. Recuperar preferencia desde la sesión
    page_size = request.session.get("device_page_size", 5)

    # 4. Paginar
    paginator = Paginator(devices, page_size)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "devices/dashboard.html",
        {
            "page_obj": page_obj,
            "page_size": page_size,
            "organization": organization,
        },
    )

class CategoryPageContextMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.all().order_by("name")
        context["open_modal"] = True
        return context

class CategoryListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "devices.view_category"
    raise_exception = True
    model = Category
    template_name = "devices/category_list.html"
    context_object_name = "categories"

    def get_queryset(self):
        return Category.objects.all().order_by("name")

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

class CategoryDeleteView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    DeleteView,
):
    permission_required = "devices.delete_category"
    raise_exception = True
    model = Category
    template_name = "devices/category_confirm_delete.html"
    success_url = reverse_lazy("devices:category_list")
    success_message = "Categoría eliminada correctamente."

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(
                request,
                "No se puede eliminar esta categoría porque tiene "
                "dispositivos asociados. Reasígnalos o elimínalos primero.",
            )
            return redirect("devices:category_list")


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
        qs = Device.objects.filter(deleted_at__isnull=True)
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
    SuccessMessageMixin,
    DeviceScopedMixin,
    DeleteView,
):
    permission_required = "devices.delete_device"
    raise_exception = True
    http_method_names = ["post"]  # nunca se elimina por GET
    success_url = reverse_lazy("devices:dashboard")
    success_message = "Dispositivo eliminado correctamente."

    def form_valid(self, form):
        image = self.object.image
        name, storage = image.name, image.storage
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                "No se puede eliminar este dispositivo porque tiene "
                "registros asociados.",
            )
            return redirect("devices:dashboard")
        # Política: al eliminar el registro, se elimina también su archivo.
        _delete_file_after_commit(storage, name)
        return response

