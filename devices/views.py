from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.shortcuts import render

from core.admin_utils import get_user_organization
from .models import Dispositivo

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