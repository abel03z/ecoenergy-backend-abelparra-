from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from devices.models import Device

from .models import Maintenance

User = get_user_model()
DATETIME_FORMAT = "%Y-%m-%dT%H:%M"


class MaintenanceForm(forms.ModelForm):
    class Meta:
        model = Maintenance
        fields = ["device", "technician", "type", "status", "scheduled_at", "completed_at"]
        labels = {
            "device": "Dispositivo",
            "technician": "Técnico",
            "type": "Tipo",
            "status": "Estado",
            "scheduled_at": "Fecha programada",
            "completed_at": "Fecha de término",
        }
        widgets = {
            "device": forms.Select(attrs={"class": "form-select"}),
            "technician": forms.Select(attrs={"class": "form-select"}),
            "type": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "scheduled_at": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format=DATETIME_FORMAT,
            ),
            "completed_at": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format=DATETIME_FORMAT,
            ),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        devices = Device.objects.select_related("zone")
        technicians = User.objects.filter(is_active=True)
        if organization is not None:
            devices = devices.filter(zone__department__organization=organization)
            technicians = technicians.filter(profile__organization=organization)
        self.fields["device"].queryset = devices.order_by("name")
        self.fields["technician"].queryset = technicians.order_by("username")
        self.fields["technician"].empty_label = "— Sin asignar —"

    def clean(self):
        cleaned = super().clean()
        device = cleaned.get("device")
        type_ = cleaned.get("type")
        status = cleaned.get("status")
        scheduled_at = cleaned.get("scheduled_at")
        completed_at = cleaned.get("completed_at")
        now = timezone.now()

        if scheduled_at and not self.instance.pk and status == Maintenance.Status.PENDING:
            if scheduled_at < now:
                self.add_error(
                    "scheduled_at",
                    "Una mantención pendiente nueva no puede programarse en el pasado.",
                )

        if status == Maintenance.Status.DONE and not completed_at:
            self.add_error("completed_at", "Indica la fecha de término de una mantención realizada.")
        if completed_at:
            if status != Maintenance.Status.DONE:
                self.add_error(
                    "completed_at",
                    "Solo las mantenciones en estado «Done» pueden tener fecha de término.",
                )
            elif completed_at > now:
                self.add_error("completed_at", "La fecha de término no puede estar en el futuro.")

        if device and type_ and scheduled_at:
            duplicated = Maintenance.objects.filter(
                device=device, type=type_, scheduled_at=scheduled_at
            )
            if self.instance.pk:
                duplicated = duplicated.exclude(pk=self.instance.pk)
            if duplicated.exists():
                raise forms.ValidationError(
                    "Ya existe una mantención de ese tipo para el dispositivo en esa fecha."
                )
        return cleaned
