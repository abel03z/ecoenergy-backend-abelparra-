from django.db import models
from core.models import BaseModel


class Medicion(BaseModel):
    dispositivo = models.ForeignKey(
        "devices.Dispositivo",
        on_delete=models.CASCADE,
        related_name="mediciones",
    )
    valor_consumo = models.FloatField()
    fecha_hora = models.DateTimeField()

    def __str__(self):
        return f"{self.dispositivo} - {self.fecha_hora}"


class Alerta(BaseModel):
    dispositivo = models.ForeignKey(
        "devices.Dispositivo",
        on_delete=models.CASCADE,
        related_name="alertas",
    )
    estado = models.CharField(max_length=50)
    fecha_generada = models.DateTimeField()

    def __str__(self):
        return f"{self.dispositivo} - {self.estado}"


class Mantenimiento(BaseModel):
    dispositivo = models.ForeignKey(
        "devices.Dispositivo",
        on_delete=models.PROTECT,
        related_name="mantenimientos",
    )
#    usuario = models.ForeignKey(
#        "organizations.Usuario",
#        on_delete=models.PROTECT,
#        related_name="mantenimientos",
#    )
    tipo = models.CharField(max_length=50)
    estado = models.CharField(max_length=50)
    fecha_programada = models.DateTimeField()

    def __str__(self):
        return f"{self.dispositivo} - {self.tipo}"
