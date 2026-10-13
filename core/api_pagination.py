from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """20 por página por defecto. ?page=2 pide otra página; ?page_size=50 cambia el tamaño (máx. 100)."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
