from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from core.models import BaseModel


class Measurement(BaseModel):
    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.PROTECT,
        related_name="measurements",
    )
    consumption_value = models.FloatField(validators=[MinValueValidator(0)])
    measured_at = models.DateTimeField()

    def __str__(self):
        return f"{self.device} - {self.measured_at}"


class Alert(BaseModel):
    class Level(models.TextChoices):
        INFO = "INFO", "Info"
        WARNING = "WARNING", "Warning"
        CRITICAL = "CRITICAL", "Critical"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged"
        RESOLVED = "RESOLVED", "Resolved"

    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.PROTECT,
        related_name="alerts",
    )
    level = models.CharField(
        max_length=10, choices=Level.choices, default=Level.WARNING
    )
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.OPEN
    )
    message = models.CharField(max_length=255, blank=True)
    generated_at = models.DateTimeField()

    def __str__(self):
        return f"{self.device} - {self.status}"


class Maintenance(BaseModel):
    class Type(models.TextChoices):
        PREVENTIVE = "PREVENTIVE", "Preventive"
        CORRECTIVE = "CORRECTIVE", "Corrective"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        DONE = "DONE", "Done"

    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.PROTECT,
        related_name="maintenances",
    )
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maintenances",
    )
    type = models.CharField(max_length=15, choices=Type.choices)
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.PENDING
    )
    scheduled_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.device} - {self.type}"
