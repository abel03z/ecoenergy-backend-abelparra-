from rest_framework import serializers

from .models import Alert, Measurement


class MeasurementSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)

    class Meta:
        model = Measurement
        fields = ["id", "device", "device_name", "consumption_value", "measured_at"]
        read_only_fields = fields


class AlertSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)

    class Meta:
        model = Alert
        fields = ["id", "device", "device_name", "level", "status", "message", "generated_at"]
        read_only_fields = fields
