import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import PasswordResetCode

User = get_user_model()
GOOD_PASSWORD = "NuevaClave#2026"


class PasswordPolicyTests(TestCase):
    """AUTH_PASSWORD_VALIDATORS: 10+ caracteres, mayúscula, minúscula, número y especial."""

    def assertRejected(self, password, fragment):
        with self.assertRaises(ValidationError) as ctx:
            validate_password(password)
        self.assertIn(fragment, " ".join(ctx.exception.messages))

    def test_contrasena_valida(self):
        validate_password(GOOD_PASSWORD)  # no lanza excepción

    def test_largo_minimo_10(self):
        self.assertRejected("Ab1#xyz90", "10 caracteres")  # 9 caracteres

    def test_exige_mayuscula(self):
        self.assertRejected("nuevaclave#2026", "mayúscula")

    def test_exige_minuscula(self):
        self.assertRejected("NUEVACLAVE#2026", "minúscula")

    def test_exige_numero(self):
        self.assertRejected("NuevaClave#abcd", "número")

    def test_exige_caracter_especial(self):
        self.assertRejected("NuevaClave2026", "carácter especial")

    def test_rechaza_contrasena_comun(self):
        self.assertRejected("password123", "común")


class PasswordResetFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            "abel", email="abel@ecoenergy.test", password="ClaveAntigua#1"
        )

    def _request_code(self, email="abel@ecoenergy.test"):
        mail.outbox.clear()
        return self.client.post(reverse("password_reset_request"), {"email": email})

    def _code_from_mail(self):
        self.assertEqual(len(mail.outbox), 1)
        return re.search(r"\b(\d{6})\b", mail.outbox[0].body).group(1)

    def _verify(self, code):
        return self.client.post(reverse("password_reset_verify"), {"code": code})

    def _set_password(self, new=GOOD_PASSWORD, confirm=None):
        return self.client.post(
            reverse("password_reset_confirm_code"),
            {"new_password": new, "confirm_password": new if confirm is None else confirm},
        )

    # --- flujo completo
    def test_flujo_completo_de_extremo_a_extremo(self):
        r = self._request_code()
        self.assertContains(r, "Revisa tu correo")
        code = self._code_from_mail()
        self.assertEqual(len(code), 6)

        r = self._verify(code)
        self.assertRedirects(r, reverse("password_reset_confirm_code"))

        r = self._set_password()
        self.assertRedirects(r, reverse("login"))

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(GOOD_PASSWORD))
        self.assertTrue(self.client.login(username="abel", password=GOOD_PASSWORD))

    def test_el_codigo_se_guarda_hasheado(self):
        self._request_code()
        code = self._code_from_mail()
        stored = PasswordResetCode.objects.get(user=self.user)
        self.assertNotEqual(stored.code_hash, code)
        self.assertNotIn(code, stored.code_hash)

    # --- el código no se reutiliza
    def test_el_codigo_no_puede_reutilizarse_tras_una_recuperacion_exitosa(self):
        self._request_code()
        code = self._code_from_mail()
        self._verify(code)
        self._set_password()

        # Intento de reutilizar el mismo código (aunque la sesión se reconstruyera).
        session = self.client.session
        session["password_reset_user_id"] = self.user.id
        session.save()
        r = self._verify(code)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "inválido o expirado")
        self.assertTrue(PasswordResetCode.objects.get(user=self.user).used)

    def test_no_se_puede_confirmar_sin_haber_verificado_el_codigo(self):
        r = self._set_password()
        self.assertRedirects(r, reverse("password_reset_request"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("ClaveAntigua#1"))

    def test_un_codigo_nuevo_invalida_el_anterior(self):
        self._request_code()
        old = self._code_from_mail()
        self._request_code()
        new = self._code_from_mail()
        self.assertEqual(PasswordResetCode.objects.filter(user=self.user, used=False).count(), 1)
        if old != new:
            r = self._verify(old)
            self.assertContains(r, "Código incorrecto")
        self.assertRedirects(self._verify(new), reverse("password_reset_confirm_code"))

    # --- validaciones del código
    def test_codigo_incorrecto_y_bloqueo_por_intentos(self):
        self._request_code()
        real = self._code_from_mail()
        wrong = "000000" if real != "000000" else "111111"
        for _ in range(5):
            self.assertContains(self._verify(wrong), "Código incorrecto")
        # agotados los intentos, ni siquiera el código correcto sirve
        self.assertContains(self._verify(real), "Se agotaron los intentos")

    def test_codigo_expirado(self):
        self._request_code()
        code = self._code_from_mail()
        PasswordResetCode.objects.filter(user=self.user).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        self.assertContains(self._verify(code), "expirado")

    def test_codigo_debe_tener_6_digitos(self):
        self._request_code()
        for bad in ("12345", "1234567", "abcdef", "12 456"):
            r = self._verify(bad)
            self.assertEqual(r.status_code, 200, bad)
            self.assertIn("code", r.context["form"].errors, bad)

    # --- nueva contraseña
    def _verified_session(self):
        self._request_code()
        self._verify(self._code_from_mail())

    def test_las_contrasenas_deben_coincidir(self):
        self._verified_session()
        r = self._set_password(confirm="OtraClave#2026")
        self.assertIn("confirm_password", r.context["form"].errors)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("ClaveAntigua#1"))

    def test_rechaza_contrasenas_debiles_y_no_consume_el_codigo(self):
        self._verified_session()
        for weak in ("corta1A#", "sinmayuscula#2026", "SINMINUSCULA#2026", "SinNumero#Clave", "SinEspecial2026"):
            r = self._set_password(new=weak)
            self.assertEqual(r.status_code, 200, weak)
            self.assertIn("new_password", r.context["form"].errors, weak)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("ClaveAntigua#1"))
        self.assertFalse(PasswordResetCode.objects.get(user=self.user).used)
        # y después sí se puede con una contraseña válida
        self.assertRedirects(self._set_password(), reverse("login"))

    def test_la_contrasena_nunca_queda_en_texto_plano(self):
        self._verified_session()
        self._set_password()
        self.user.refresh_from_db()
        self.assertNotIn(GOOD_PASSWORD, self.user.password)
        self.assertTrue(self.user.password.startswith(("pbkdf2_", "argon2", "bcrypt", "scrypt")))

    def test_codigo_que_expira_entre_verificar_y_confirmar(self):
        self._verified_session()
        PasswordResetCode.objects.filter(user=self.user).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        r = self._set_password()
        self.assertRedirects(r, reverse("password_reset_request"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("ClaveAntigua#1"))

    # --- correos inexistentes / modo demo
    def test_correo_inexistente_responde_igual_y_no_envia_nada(self):
        r = self._request_code(email="nadie@ecoenergy.test")
        self.assertContains(r, "Revisa tu correo")
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(PasswordResetCode.objects.count(), 0)
        # sin código emitido no se puede entrar al paso de verificación
        self.assertRedirects(self._verify("123456"), reverse("password_reset_request"))

    def test_por_defecto_no_muestra_el_codigo_en_pantalla(self):
        r = self._request_code()
        code = self._code_from_mail()
        self.assertNotContains(r, code)

    @override_settings(PASSWORD_RESET_DEMO_MODE=True)
    def test_modo_demo_muestra_el_codigo(self):
        r = self._request_code()
        code = self._code_from_mail()
        self.assertContains(r, f"Modo demostración: tu código es {code}")
