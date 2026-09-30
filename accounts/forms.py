from django import forms
from django.core.validators import RegexValidator


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={"class": "form-control", "autofocus": True}),
    )


class PasswordResetVerifyForm(forms.Form):
    code = forms.CharField(
        label="Código de verificación",
        max_length=6,
        min_length=6,
        validators=[RegexValidator(r"^\d{6}$", "El código debe tener exactamente 6 dígitos.")],
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "inputmode": "numeric",
            "autocomplete": "one-time-code",
            "maxlength": "6",
            "autofocus": True,
        }),
    )

    def clean_code(self):
        return self.cleaned_data["code"].strip()


class SetNewPasswordForm(forms.Form):
    new_password = forms.CharField(
        label="Nueva contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )
    confirm_password = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )

    def clean(self):
        cleaned = super().clean()
        new, confirm = cleaned.get("new_password"), cleaned.get("confirm_password")
        if new and confirm and new != confirm:
            self.add_error("confirm_password", "Las contraseñas no coinciden.")
        return cleaned
