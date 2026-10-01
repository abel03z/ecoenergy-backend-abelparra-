from django import forms

from core.filters import FilterFormMixin

from .models import Department, Zone

MAX_CONSUMPTION_LIMIT = 100000


class ZoneForm(forms.ModelForm):
    class Meta:
        model = Zone
        fields = ["department", "name", "consumption_limit"]
        labels = {
            "department": "Departamento",
            "name": "Nombre",
            "consumption_limit": "Límite de consumo (kWh)",
        }
        widgets = {
            "department": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "consumption_limit": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.1"}
            ),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        departments = Department.objects.select_related("organization")
        if organization is not None:
            departments = departments.filter(organization=organization)
        self.fields["department"].queryset = departments.order_by("name")

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if len(name) < 3:
            raise forms.ValidationError("El nombre debe tener al menos 3 caracteres.")
        return name

    def clean_consumption_limit(self):
        value = self.cleaned_data["consumption_limit"]
        if value <= 0:
            raise forms.ValidationError("El límite de consumo debe ser mayor que 0.")
        if value > MAX_CONSUMPTION_LIMIT:
            raise forms.ValidationError(
                f"El límite de consumo no puede superar {MAX_CONSUMPTION_LIMIT} kWh."
            )
        return value

    def clean(self):
        cleaned = super().clean()
        department, name = cleaned.get("department"), cleaned.get("name")
        if department and name:
            # Zone.objects solo considera zonas vivas.
            duplicated = Zone.objects.filter(department=department, name__iexact=name)
            if self.instance.pk:
                duplicated = duplicated.exclude(pk=self.instance.pk)
            if duplicated.exists():
                self.add_error("name", "Ya existe una zona con ese nombre en el departamento.")
        return cleaned


class ZoneFilterForm(FilterFormMixin, forms.Form):
    q = forms.CharField(
        required=False,
        max_length=100,
        label="Buscar",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre de la zona"}),
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.none(), required=False, label="Departamento",
        empty_label="Todos", widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        departments = Department.objects.select_related("organization")
        if organization is not None:
            departments = departments.filter(organization=organization)
        else:
            # Superusuario: los nombres se repiten entre organizaciones, se indica cuál es cuál.
            self.fields["department"].label_from_instance = (
                lambda d: f"{d.name} · {d.organization}"
            )
        self.fields["department"].queryset = departments.order_by("name")

    def apply(self, queryset):
        data = self.current_filters()
        if data.get("q"):
            queryset = queryset.filter(name__icontains=data["q"].strip())
        if data.get("department"):
            queryset = queryset.filter(department=data["department"])
        return queryset
