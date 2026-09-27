from django import forms

class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(label="Correo electrónico")

class PasswordResetVerifyForm(forms.Form):
    code = forms.CharField(label="Código de verificación", max_length=6)

class SetNewPasswordForm(forms.Form):
    new_password = forms.CharField(label="Nueva contraseña", widget=forms.PasswordInput)
    confirm_password = forms.CharField(label="Confirmar contraseña", widget=forms.PasswordInput)