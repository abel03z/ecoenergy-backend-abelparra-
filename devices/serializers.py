from pathlib import Path

from rest_framework import serializers

from .models import Device
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
