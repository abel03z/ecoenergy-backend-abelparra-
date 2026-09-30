from django.core.validators import MinValueValidator
from django.db import models

from core.models import BaseModel


class Organization(BaseModel):
    name = models.CharField(max_length=150)

    def __str__(self):
        return self.name


class Department(BaseModel):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="departments",
    )
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Zone(BaseModel):
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="zones",
    )
    name = models.CharField(max_length=100)
    consumption_limit = models.FloatField(validators=[MinValueValidator(0)])

    def __str__(self):
        return self.name
