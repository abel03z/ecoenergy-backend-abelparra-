import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import (
    password_validators_help_texts,
    validate_password,
)
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import PasswordResetRequestForm, PasswordResetVerifyForm, SetNewPasswordForm
from .models import PasswordResetCode

SESSION_USER = "password_reset_user_id"
SESSION_CODE = "password_reset_code_id"


def _clear_reset_session(request):
    request.session.pop(SESSION_USER, None)
    request.session.pop(SESSION_CODE, None)


def password_reset_request(request):
    """Paso 1: pide el correo y envía un código numérico de 6 dígitos."""
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            user = get_user_model().objects.filter(email__iexact=email, is_active=True).first()

            if user:
                # Un solo código vigente por usuario: los anteriores se invalidan.
                PasswordResetCode.objects.filter(user=user, used=False).update(used=True)

                code = f"{secrets.randbelow(1_000_000):06d}"  # 000000–999999, criptográficamente seguro
                PasswordResetCode.objects.create(
                    user=user,
                    code_hash=make_password(code),  # nunca se guarda en texto plano
                    expires_at=timezone.now() + timedelta(seconds=settings.PASSWORD_RESET_CODE_TTL),
                )
                request.session[SESSION_USER] = user.id
                request.session.pop(SESSION_CODE, None)

                minutes = settings.PASSWORD_RESET_CODE_TTL // 60
                send_mail(
                    subject="Tu código de recuperación · EcoEnergy",
                    message=f"Tu código de recuperación es: {code}\nExpira en {minutes} minutos.",
                    from_email=None,
                    recipient_list=[user.email],
                )
                if settings.PASSWORD_RESET_DEMO_MODE:
                    # SOLO para demostraciones sin servidor de correo. Desactivado por defecto.
                    messages.info(request, f"Modo demostración: tu código es {code}")

            # Misma respuesta exista o no la cuenta (no revela qué correos están registrados).
            return render(request, "accounts/password_reset_sent.html")
    else:
        form = PasswordResetRequestForm()

    return render(request, "accounts/password_reset_request.html", {"form": form})


def password_reset_verify(request):
    """Paso 2: verifica el código ingresado."""
    user_id = request.session.get(SESSION_USER)
    if not user_id:
        return redirect("password_reset_request")

    if request.method == "POST":
        form = PasswordResetVerifyForm(request.POST)
        if form.is_valid():
            reset_code = (
                PasswordResetCode.objects.filter(user_id=user_id, used=False)
                .order_by("-created_at", "-pk")
                .first()
            )
            if not reset_code:
                form.add_error(None, "Código inválido o expirado. Solicita uno nuevo.")
            elif timezone.now() > reset_code.expires_at:
                form.add_error(None, "El código ha expirado, solicita uno nuevo.")
            elif reset_code.failed_attempts >= settings.PASSWORD_RESET_MAX_ATTEMPTS:
                form.add_error(None, "Se agotaron los intentos, solicita un código nuevo.")
            elif check_password(form.cleaned_data["code"], reset_code.code_hash):
                request.session[SESSION_CODE] = reset_code.id
                return redirect("password_reset_confirm_code")
            else:
                reset_code.failed_attempts += 1
                reset_code.save(update_fields=["failed_attempts", "updated_at"])
                form.add_error(None, "Código incorrecto.")
    else:
        form = PasswordResetVerifyForm()

    return render(request, "accounts/password_reset_verify.html", {"form": form})


def password_reset_confirm_code(request):
    """Paso 3: define la nueva contraseña (dos veces) y consume el código."""
    code_id = request.session.get(SESSION_CODE)
    if not code_id:
        return redirect("password_reset_request")

    reset_code = PasswordResetCode.objects.filter(id=code_id, used=False).select_related("user").first()
    if not reset_code or timezone.now() > reset_code.expires_at:
        _clear_reset_session(request)
        messages.error(request, "El código ya no es válido. Solicita uno nuevo.")
        return redirect("password_reset_request")

    if request.method == "POST":
        form = SetNewPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data["new_password"]
            try:
                # Aplica AUTH_PASSWORD_VALIDATORS: largo mínimo 10, mayúscula,
                # minúscula, número, carácter especial, contraseñas comunes, etc.
                validate_password(new_password, user=reset_code.user)
            except DjangoValidationError as errors:
                for error in errors.messages:
                    form.add_error("new_password", error)
            else:
                reset_code.user.set_password(new_password)  # se guarda hasheada
                reset_code.user.save(update_fields=["password"])

                # El código queda consumido: no se puede reutilizar.
                reset_code.used = True
                reset_code.save(update_fields=["used", "updated_at"])
                _clear_reset_session(request)

                messages.success(request, "Contraseña actualizada. Ya puedes ingresar.")
                return redirect("login")
    else:
        form = SetNewPasswordForm()

    return render(
        request,
        "accounts/password_reset_confirm.html",
        {"form": form, "password_help": password_validators_help_texts()},
    )
