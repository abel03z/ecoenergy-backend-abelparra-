from django.contrib import messages
from django.http import HttpResponseRedirect


class SoftDeleteMixin:
    """
    Para usar junto a DeleteView: en vez de borrar la fila, marca deleted_at.
    La autenticación y el permiso los validan LoginRequiredMixin y
    PermissionRequiredMixin, y el scoping lo aplica get_queryset() de la vista.
    Solo acepta POST (con CSRF), nunca GET.
    """

    http_method_names = ["post"]
    success_message = "Registro eliminado correctamente."

    def can_soft_delete(self):
        """Regla de negocio opcional. Retorna (ok, mensaje_de_error)."""
        return True, ""

    def form_valid(self, form):
        ok, error = self.can_soft_delete()
        if not ok:
            messages.error(self.request, error)
            return HttpResponseRedirect(self.get_success_url())
        self.object.soft_delete()
        messages.success(self.request, self.success_message)
        return HttpResponseRedirect(self.get_success_url())
