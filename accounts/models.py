from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.models import BaseModel


class UserProfile(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    organizacion = models.ForeignKey(
        "organizations.Organizacion",
        on_delete=models.PROTECT,
        related_name="user_profiles",
    )
    departamento = models.ForeignKey(
        "organizations.Departamento",
        on_delete=models.PROTECT,
        related_name="user_profiles",
        null=True,
        blank=True,
    )
    employee_code = models.CharField(max_length=30, unique=True)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.user.username} · {self.organizacion}"

    def clean(self):
        super().clean()
        if (
            self.departamento_id
            and self.departamento.organizacion_id != self.organizacion_id
        ):
            raise ValidationError({
                "departamento": (
                    "El departamento debe pertenecer "
                    "a la organización seleccionada."
                )
            })