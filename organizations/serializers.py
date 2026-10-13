from rest_framework import serializers

from core.api import organizacion_del_usuario

from .models import Zone


class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = ["id", "name", "department", "consumption_limit"]
        read_only_fields = ["id"]

    def validate_name(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Ingrese al menos 3 caracteres.")
        return value

    def validate_consumption_limit(self, value):
        # Validación de campo: el modelo permite 0, pero una zona sin límite no tiene sentido.
        if value <= 0:
            raise serializers.ValidationError("El límite de consumo debe ser mayor que 0.")
        return value

    def validate_department(self, department):
        # Regla de relación: solo departamentos de la organización del usuario.
        request = self.context.get("request")
        if request is not None:
            org = organizacion_del_usuario(request.user)
            if org is not None and department.organization_id != org.pk:
                raise serializers.ValidationError("Departamento no válido para tu organización.")
        return department

    def validate(self, attrs):
        # Regla de negocio: el nombre de la zona es único dentro de su departamento.
        department = attrs.get("department") or getattr(self.instance, "department", None)
        name = attrs.get("name") or getattr(self.instance, "name", None)
        if department and name:
            qs = Zone.objects.filter(department=department, name__iexact=name)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"name": "Ya existe una zona con ese nombre en el departamento."}
                )
        return attrs
