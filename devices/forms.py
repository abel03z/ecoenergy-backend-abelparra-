from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_image_file_extension

from organizations.models import Zona
from .models import Categoria, Dispositivo
from .validators import validate_real_image


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

MAX_SIZE = 2 * 1024 * 1024  # 2 MB
ALLOWED = {".jpg", ".jpeg", ".png"}


class DispositivoForm(forms.ModelForm):
    class Meta:
        model = Dispositivo
        fields = ["nombre", "categoria", "zona", "activo", "image"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "categoria": forms.Select(attrs={"class": "form-select"}),
            "zona": forms.Select(attrs={"class": "form-select"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "image": forms.ClearableFileInput(attrs={
                "class": "form-control",
                "accept": ".jpg,.jpeg,.png",
            }),
        }
        labels = {"image": "Imagen (JPG o PNG, máx. 2 MB)"}
        error_messages = {
            "image": {"invalid_image": "El archivo no es una imagen válida."},
        }

    def __init__(self, *args, organizacion=None, **kwargs):
        super().__init__(*args, **kwargs)
        zonas = Zona.objects.filter(deleted_at__isnull=True)
        if organizacion is not None:
            # scoping: solo zonas de la organización del usuario
            zonas = zonas.filter(departamento__organizacion=organizacion)
        self.fields["zona"].queryset = zonas.order_by("nombre")
        # La extensión se valida en clean_image() con un mensaje propio.
        self.fields["image"].validators = [
            v for v in self.fields["image"].validators
            if v is not validate_image_file_extension
        ]

    def clean_image(self):
        image = self.cleaned_data.get("image")
        # Sin archivo nuevo (o "limpiar"): no hay nada que validar.
        if not image or not hasattr(image, "size"):
            return image
        # Si el archivo ya estaba guardado, tampoco se vuelve a validar.
        if getattr(image, "_committed", False):
            return image

        if image.size > MAX_SIZE:
            raise ValidationError("La imagen no puede superar 2 MB.")

        suffix = Path(image.name).suffix.lower()
        if suffix not in ALLOWED:
            raise ValidationError("Formato no permitido. Use JPG o PNG.")

        validate_real_image(image)
        return image
