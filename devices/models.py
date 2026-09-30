from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.models import BaseModel


class Category(BaseModel):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Manufacturer(BaseModel):
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=60, blank=True)

    def __str__(self):
        return self.name


class Device(BaseModel):
    zone = models.ForeignKey(
        "organizations.Zone",
        on_delete=models.PROTECT,
        related_name="devices",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="devices",
    )
    manufacturer = models.ForeignKey(
        Manufacturer,
        on_delete=models.PROTECT,
        related_name="devices",
    )
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    image = models.ImageField(
        upload_to="devices/%Y/%m/",
        blank=True,
    )

    def __str__(self):
        return self.name


class DeviceAssignment(BaseModel):
    """Operational table: which user is responsible for a device, and when."""

    device = models.ForeignKey(
        Device,
        on_delete=models.PROTECT,
        related_name="assignments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="device_assignments",
    )
    assigned_at = models.DateTimeField(default=timezone.now)
    released_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.device} -> {self.user}"

    def clean(self):
        super().clean()
        if self.released_at and self.released_at < self.assigned_at:
            raise ValidationError(
                {"released_at": "La fecha de término no puede ser anterior a la de inicio."}
            )
