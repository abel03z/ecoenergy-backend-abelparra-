from django.db import models
from core.models import BaseModel


class Organizacion(BaseModel):
    nombre = models.CharField(max_length=150)

    def __str__(self):
        return self.nombre


class Departamento(BaseModel):
    organizacion = models.ForeignKey(
        Organizacion,
        on_delete=models.PROTECT,
        related_name="departamentos",
    )
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class Zona(BaseModel):
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        related_name="zonas",
    )
    nombre = models.CharField(max_length=100)
    limite_consumo = models.FloatField()

    def __str__(self):
        return self.nombre


class Usuario(BaseModel):
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        related_name="usuarios",
    )
    nombre = models.CharField(max_length=100)
    rol = models.CharField(max_length=50)

    def __str__(self):
        return self.nombre
