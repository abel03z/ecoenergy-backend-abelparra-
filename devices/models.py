from django.db import models
from core.models import BaseModel


class Categoria(BaseModel):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class Dispositivo(BaseModel):
    zona = models.ForeignKey(
        "organizations.Zona",
        on_delete=models.PROTECT,
        related_name="dispositivos",
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="dispositivos",
    )
    nombre = models.CharField(max_length=120)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre
