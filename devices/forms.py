from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_image_file_extension

from organizations.models import Zone
from .models import Category, Device
from .validators import validate_real_image


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej.: Sensores de temperatura",
            }),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if len(name) < 3:
            raise ValidationError("Ingrese al menos 3 caracteres.")

        exists = Category.objects.filter(
            name__iexact=name
        ).exclude(
            pk=self.instance.pk
        ).exists()
        if exists:
            raise ValidationError("Ya existe una categoría con ese nombre.")

        return name

MAX_SIZE = 2 * 1024 * 1024  # 2 MB
ALLOWED = {".jpg", ".jpeg", ".png"}


class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = ["name", "category", "manufacturer", "zone", "is_active", "image"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "manufacturer": forms.Select(attrs={"class": "form-select"}),
            "zone": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "image": forms.ClearableFileInput(attrs={
                "class": "form-control",
                "accept": ".jpg,.jpeg,.png",
            }),
        }
        labels = {
            "name": "Nombre",
            "category": "Categoría",
            "manufacturer": "Fabricante",
            "zone": "Zona",
            "is_active": "Activo",
            "image": "Imagen (JPG o PNG, máx. 2 MB)",
        }
        error_messages = {
            "image": {"invalid_image": "El archivo no es una imagen válida."},
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        zones = Zone.objects.filter(deleted_at__isnull=True)
        if organization is not None:
            # scoping: solo zonas de la organización del usuario
            zones = zones.filter(department__organization=organization)
        self.fields["zone"].queryset = zones.order_by("name")
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
