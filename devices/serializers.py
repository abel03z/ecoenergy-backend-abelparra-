from pathlib import Path

from rest_framework import serializers

from .models import Category, Device, Manufacturer
from .validators import validate_real_image

MAX_SIZE = 2 * 1024 * 1024  # 2 MB (misma regla que DeviceForm)
ALLOWED = {".jpg", ".jpeg", ".png"}


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        # Campos explícitos: no se publican created_at / updated_at / deleted_at.
        fields = ["id", "name", "category", "manufacturer", "zone", "is_active", "image"]
        read_only_fields = ["id"]

    def validate_name(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Ingrese al menos 3 caracteres.")
        return value

    def validate_zone(self, zone):
        # La organización la decide el servidor: el usuario solo puede usar zonas de la suya.
        from .api_views import organizacion_del_usuario

        request = self.context.get("request")
        if request is not None:
            org = organizacion_del_usuario(request.user)
            if org is not None and zone.department.organization_id != org.pk:
                raise serializers.ValidationError("Zona no válida para tu organización.")
        return zone

    def validate_image(self, image):
        # Mismas reglas que el formulario web (Clase 8).
        if not image:
            return image
        if image.size > MAX_SIZE:
            raise serializers.ValidationError("La imagen no puede superar 2 MB.")
        if Path(image.name).suffix.lower() not in ALLOWED:
            raise serializers.ValidationError("Formato no permitido. Use JPG o PNG.")
        try:
            validate_real_image(image)
        except Exception:
            raise serializers.ValidationError("El archivo no es una imagen válida.")
        return image


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]
        read_only_fields = ["id"]

    def validate_name(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Ingrese al menos 3 caracteres.")
        qs = Category.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe una categoría con ese nombre.")
        return value


class ManufacturerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Manufacturer
        fields = ["id", "name", "country"]
        read_only_fields = ["id"]

    def validate_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Ingrese al menos 2 caracteres.")
        qs = Manufacturer.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe un fabricante con ese nombre.")
        return value
