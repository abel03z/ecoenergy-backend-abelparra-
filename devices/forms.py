from django import forms
from django.core.exceptions import ValidationError
from .models import Categoria


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nombre"]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej.: Sensores de temperatura",
            }),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        if len(nombre) < 3:
            raise ValidationError("Ingrese al menos 3 caracteres.")

        existe = Categoria.objects.filter(
            nombre__iexact=nombre
        ).exclude(
            pk=self.instance.pk
        ).exists()
        if existe:
            raise ValidationError("Ya existe una categoría con ese nombre.")

        return nombre