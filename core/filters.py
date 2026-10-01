"""Utilidades compartidas por los formularios de filtro de los listados (GET)."""
from urllib.parse import urlencode


class FilterFormMixin:
    """
    Para formularios de filtro opcionales: los valores inválidos se ignoran
    (cleaned_data conserva solo los campos válidos) y los filtros vigentes se
    pueden volver a escribir como query string para conservarlos al paginar.
    """

    def current_filters(self):
        self.is_valid()
        data = getattr(self, "cleaned_data", {})
        return {name: value for name, value in data.items() if value not in (None, "")}

    def query_string(self):
        """'' o 'a=1&b=2&' (listo para anteponer a page=N)."""
        params = {}
        for name, value in self.current_filters().items():
            params[name] = value.pk if hasattr(value, "pk") else str(value).strip()
        return urlencode(params) + "&" if params else ""

    def filter_context(self):
        query = self.query_string()
        return {"filter_form": self, "base_query": query, "has_filters": bool(query)}
