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
from .models import Categoria, Dispositivo
from .forms import CategoriaForm, DispositivoForm

ALLOWED_PAGE_SIZES = {5, 10, 15}


@login_required
@permission_required("devices.view_dispositivo", raise_exception=True)
def dashboard(request):
    if request.user.is_superuser:
        dispositivos = Dispositivo.objects.filter(deleted_at__isnull=True)
        organizacion = None
    else:
        organizacion = get_user_organization(request)
        dispositivos = Dispositivo.objects.filter(
            zona__departamento__organizacion=organizacion,
            deleted_at__isnull=True,
        )

    dispositivos = dispositivos.select_related("zona", "categoria").order_by("nombre")

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
    paginator = Paginator(dispositivos, page_size)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "devices/dashboard.html",
        {
            "page_obj": page_obj,
            "page_size": page_size,
            "organizacion": organizacion,
        },
    )

class CategoriaPageContextMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categorias"] = Categoria.objects.all().order_by("nombre")
        context["open_modal"] = True
        return context

class CategoriaListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "devices.view_categoria"
    raise_exception = True
    model = Categoria
    template_name = "devices/categoria_list.html"
    context_object_name = "categorias"

    def get_queryset(self):
        return Categoria.objects.all().order_by("nombre")

class CategoriaCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    CategoriaPageContextMixin,
    CreateView,
):
    permission_required = "devices.add_categoria"
    raise_exception = True
    model = Categoria
    form_class = CategoriaForm
    template_name = "devices/categoria_list.html"
    success_url = reverse_lazy("devices:categoria_list")
    success_message = "Categoría creada correctamente."


class CategoriaUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    CategoriaPageContextMixin,
    UpdateView,
):
    permission_required = "devices.change_categoria"
    raise_exception = True
    model = Categoria
    form_class = CategoriaForm
    template_name = "devices/categoria_list.html"
    success_url = reverse_lazy("devices:categoria_list")
    success_message = "Categoría actualizada correctamente."

class CategoriaDeleteView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    DeleteView,
):
    permission_required = "devices.delete_categoria"
    raise_exception = True
    model = Categoria
    template_name = "devices/categoria_confirm_delete.html"
    success_url = reverse_lazy("devices:categoria_list")
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
            return redirect("devices:categoria_list")


# ---------------------------------------------------------------------------
# Clase 8 · CRUD de Dispositivo con imagen (scoping por organización)
# ---------------------------------------------------------------------------

def _delete_file_after_commit(storage, name):
    """Borra un archivo del storage solo si la transacción termina bien."""
    if name:
        transaction.on_commit(lambda: storage.delete(name))


class DispositivoScopedMixin:
    """Limita el queryset a la organización del usuario (superusuario: todo)."""

    def get_organizacion(self):
        return get_user_organization(self.request)

    def get_queryset(self):
        qs = Dispositivo.objects.filter(deleted_at__isnull=True)
        if self.request.user.is_superuser:
            return qs
        return qs.filter(zona__departamento__organizacion=self.get_organizacion())


class DispositivoFormMixin(DispositivoScopedMixin):
    model = Dispositivo
    form_class = DispositivoForm
    template_name = "devices/dispositivo_form.html"
    success_url = reverse_lazy("devices:dashboard")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organizacion"] = self.get_organizacion()
        return kwargs


class DispositivoCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    DispositivoFormMixin,
    CreateView,
):
    permission_required = "devices.add_dispositivo"
    raise_exception = True
    success_message = "Dispositivo creado correctamente."


class DispositivoUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    DispositivoFormMixin,
    UpdateView,
):
    permission_required = "devices.change_dispositivo"
    raise_exception = True
    success_message = "Dispositivo actualizado correctamente."

    def form_valid(self, form):
        # Política: al reemplazar o limpiar la imagen, se elimina el archivo anterior.
        old_file = Dispositivo.objects.get(pk=self.object.pk).image
        old_name, storage = old_file.name, old_file.storage
        response = super().form_valid(form)
        if old_name and old_name != self.object.image.name:
            _delete_file_after_commit(storage, old_name)
        return response


class DispositivoDeleteView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    DispositivoScopedMixin,
    DeleteView,
):
    permission_required = "devices.delete_dispositivo"
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

