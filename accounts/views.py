import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.utils import timezone
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from .forms import PasswordResetRequestForm, PasswordResetVerifyForm, SetNewPasswordForm
from .models import PasswordResetCode


def password_reset_request(request):
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            User = get_user_model()
            usuario = User.objects.filter(email=email).first()

            if usuario:
                PasswordResetCode.objects.filter(
                    user=usuario, used=False
                ).update(used=True)

                numero = secrets.randbelow(1000000)
                codigo = f"{numero:06d}"

                PasswordResetCode.objects.create(
                    user=usuario,
                    code_hash=make_password(codigo),
                    expires_at=timezone.now() + timedelta(seconds=settings.PASSWORD_RESET_CODE_TTL),
                )

                request.session["password_reset_user_id"] = usuario.id

                minutos = settings.PASSWORD_RESET_CODE_TTL // 60
                send_mail(
                    subject="Tu código de recuperación",
                    message=f"Tu código de recuperación es: {codigo}\nExpira en {minutos} minutos.",
                    from_email=None,
                    recipient_list=[email],
                )

            return render(request, "accounts/password_reset_sent.html")
    else:
        form = PasswordResetRequestForm()

    return render(request, "accounts/password_reset_request.html", {"form": form})

def password_reset_verify(request):
    user_id = request.session.get("password_reset_user_id")
    if not user_id:
        return redirect("password_reset_request")

    if request.method == "POST":
        form = PasswordResetVerifyForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"]

            reset_code = PasswordResetCode.objects.filter(
                user_id=user_id, used=False
            ).order_by("-created_at").first()

            if not reset_code:
                form.add_error(None, "Código inválido o expirado.")
            else:
                if timezone.now() > reset_code.expires_at:
                    form.add_error(None, "El código ha expirado, solicita uno nuevo.")
                elif reset_code.failed_attempts >= settings.PASSWORD_RESET_MAX_ATTEMPTS:
                    form.add_error(None, "Se agotaron los intentos, solicita un código nuevo.")
                else:
                    if check_password(code, reset_code.code_hash):
                        request.session["password_reset_code_id"] = reset_code.id
                        return redirect("password_reset_confirm_code")
                        
                    else:
                        reset_code.failed_attempts += 1
                        reset_code.save()
                        form.add_error(None, "Código incorrecto.")
    else:
        form = PasswordResetVerifyForm()

    return render(request, "accounts/password_reset_verify.html", {"form": form})

def password_reset_confirm_code(request):
    code_id = request.session.get("password_reset_code_id")
    if not code_id:
        return redirect("password_reset_request")

    reset_code = PasswordResetCode.objects.filter(id=code_id, used=False).first()
    if not reset_code:
        return redirect("password_reset_request")

    if request.method == "POST":
        form = SetNewPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data["new_password"]
            confirm_password = form.cleaned_data["confirm_password"]

            if new_password != confirm_password:
                form.add_error(None, "Las contraseñas no coinciden.")
            else:
                try:
                    validate_password(new_password, user=reset_code.user)
                except DjangoValidationError as errores:
                    for error in errores.messages:
                        form.add_error(None, error)
                else:
                    reset_code.user.set_password(new_password)
                    reset_code.user.save()

                    reset_code.used = True
                    reset_code.save()

                    del request.session["password_reset_user_id"]
                    del request.session["password_reset_code_id"]

                    return redirect("login")
    else:
        form = SetNewPasswordForm()

    return render(request, "accounts/password_reset_confirm.html", {"form": form})