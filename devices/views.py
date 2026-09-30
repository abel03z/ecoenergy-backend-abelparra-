from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import Paginator
from django.db.models import ProtectedError
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from core.admin_utils import get_user_organization
from .models import Categoria, Dispositivo
from .forms import CategoriaForm

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