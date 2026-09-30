"""Paginación con tamaño de página persistido en request.session."""
from django.core.paginator import Paginator

ALLOWED_PAGE_SIZES = (5, 15, 30)
DEFAULT_PAGE_SIZE = 5
SESSION_KEY = "page_size"


def get_page_size(request):
    """
    Lee ?page_size= y lo guarda en la sesión SOLO si es un valor permitido.
    Un valor inválido (texto, 7, 9999...) se ignora: se mantiene la preferencia
    guardada o, si tampoco es válida, el valor por defecto.
    """
    raw = request.GET.get("page_size")
    if raw is not None:
        try:
            size = int(raw)
        except (TypeError, ValueError):
            size = None
        if size in ALLOWED_PAGE_SIZES:
            request.session[SESSION_KEY] = size

    stored = request.session.get(SESSION_KEY, DEFAULT_PAGE_SIZE)
    if stored not in ALLOWED_PAGE_SIZES:
        stored = DEFAULT_PAGE_SIZE
        request.session[SESSION_KEY] = stored
    return stored


def paginate(request, queryset):
    """Devuelve (page_obj, page_size, allowed_sizes) para usar en el contexto."""
    page_size = get_page_size(request)
    page_obj = Paginator(queryset, page_size).get_page(request.GET.get("page"))
    return page_obj, page_size, ALLOWED_PAGE_SIZES
