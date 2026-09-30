import io
import shutil
import tempfile
from pathlib import Path

from django.contrib.auth.models import Group, Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from accounts.models import UserProfile
from organizations.models import Departamento, Organizacion, Zona
from .models import Categoria, Dispositivo

TEST_MEDIA = tempfile.mkdtemp(prefix="ecoenergy_test_media_")


def make_image(name="foto.png", fmt="PNG", size=(20, 20)):
    buffer = io.BytesIO()
    Image.new("RGB", size, "green").save(buffer, fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def media_files():
    return [p for p in Path(TEST_MEDIA).rglob("*") if p.is_file()]


@override_settings(MEDIA_ROOT=TEST_MEDIA)
class DispositivoImagenTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.norte = Organizacion.objects.create(nombre="Norte")
        cls.sur = Organizacion.objects.create(nombre="Sur")
        d_norte = Departamento.objects.create(organizacion=cls.norte, nombre="Ops N")
        d_sur = Departamento.objects.create(organizacion=cls.sur, nombre="Ops S")
        cls.zona_norte = Zona.objects.create(departamento=d_norte, nombre="ZN", limite_consumo=10)
        cls.zona_sur = Zona.objects.create(departamento=d_sur, nombre="ZS", limite_consumo=10)
        cls.categoria = Categoria.objects.create(nombre="Medidor")

        group = Group.objects.create(name="Admin org")
        for action in ("add", "change", "delete", "view"):
            group.permissions.add(Permission.objects.get(codename=f"{action}_dispositivo"))
        cls.admin_norte = cls._user("admin_norte", cls.norte, group)

        solo_view = Group.objects.create(name="Consulta")
        solo_view.permissions.add(Permission.objects.get(codename="view_dispositivo"))
        cls.consulta_norte = cls._user("consulta_norte", cls.norte, solo_view)

    @staticmethod
    def _user(username, org, group):
        user = User.objects.create_user(username, password="x")
        user.groups.add(group)
        UserProfile.objects.create(user=user, organizacion=org, employee_code=f"E-{username}")
        return user

    def setUp(self):
        shutil.rmtree(TEST_MEDIA, ignore_errors=True)
        Path(TEST_MEDIA).mkdir(parents=True, exist_ok=True)
        self.client.force_login(self.admin_norte)

    def _payload(self, **extra):
        data = {
            "nombre": "Medidor A",
            "categoria": self.categoria.pk,
            "zona": self.zona_norte.pk,
            "activo": "on",
        }
        data.update(extra)
        return data

    # --- mini desafío: un archivo correcto y tres rechazos ---------------
    def test_imagen_valida_se_guarda(self):
        r = self.client.post(reverse("devices:dispositivo_create"),
                             self._payload(image=make_image()))
        self.assertRedirects(r, reverse("devices:dashboard"))
        disp = Dispositivo.objects.get(nombre="Medidor A")
        self.assertTrue(disp.image.name.startswith("devices/"))
        self.assertEqual(len(media_files()), 1)

    def test_imagen_demasiado_grande_se_rechaza(self):
        base = make_image("grande.png")
        grande = SimpleUploadedFile("grande.png", base.read() + b"0" * (2 * 1024 * 1024))
        r = self.client.post(reverse("devices:dispositivo_create"),
                             self._payload(image=grande))
        self.assertContains(r, "no puede superar 2 MB")
        self.assertFalse(Dispositivo.objects.exists())
        self.assertEqual(media_files(), [])

    def test_extension_prohibida_se_rechaza(self):
        r = self.client.post(reverse("devices:dispositivo_create"),
                             self._payload(image=make_image("virus.exe")))
        self.assertContains(r, "Formato no permitido")
        self.assertFalse(Dispositivo.objects.exists())
        self.assertEqual(media_files(), [])

    def test_archivo_renombrado_se_rechaza_por_contenido(self):
        falso = SimpleUploadedFile("evidencia.jpg", b"esto no es una imagen")
        r = self.client.post(reverse("devices:dispositivo_create"),
                             self._payload(image=falso))
        self.assertContains(r, "no es una imagen válida")
        self.assertFalse(Dispositivo.objects.exists())
        self.assertEqual(media_files(), [])

    def test_imagen_es_opcional(self):
        self.client.post(reverse("devices:dispositivo_create"), self._payload())
        disp = Dispositivo.objects.get(nombre="Medidor A")
        self.assertFalse(disp.image)
        r = self.client.get(reverse("devices:dashboard"))
        self.assertContains(r, "Sin imagen")

    # --- política de reemplazo / eliminación -----------------------------
    def test_reemplazar_imagen_elimina_la_anterior(self):
        self.client.post(reverse("devices:dispositivo_create"),
                         self._payload(image=make_image("uno.png")))
        disp = Dispositivo.objects.get()
        antigua = disp.image.name
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("devices:dispositivo_update", args=[disp.pk]),
                             self._payload(image=make_image("dos.png")))
        disp.refresh_from_db()
        self.assertNotEqual(disp.image.name, antigua)
        self.assertEqual(len(media_files()), 1)

    def test_editar_sin_nueva_imagen_conserva_la_actual(self):
        self.client.post(reverse("devices:dispositivo_create"),
                         self._payload(image=make_image()))
        disp = Dispositivo.objects.get()
        antigua = disp.image.name
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("devices:dispositivo_update", args=[disp.pk]),
                             self._payload(nombre="Renombrado"))
        disp.refresh_from_db()
        self.assertEqual(disp.image.name, antigua)
        self.assertEqual(len(media_files()), 1)

    def test_eliminar_borra_registro_y_archivo(self):
        self.client.post(reverse("devices:dispositivo_create"),
                         self._payload(image=make_image()))
        disp = Dispositivo.objects.get()
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(reverse("devices:dispositivo_delete", args=[disp.pk]))
        self.assertRedirects(r, reverse("devices:dashboard"))
        self.assertFalse(Dispositivo.objects.exists())
        self.assertEqual(media_files(), [])

    # --- POST, permisos y scoping ----------------------------------------
    def test_eliminar_por_get_no_esta_permitido(self):
        disp = Dispositivo.objects.create(nombre="X", zona=self.zona_norte, categoria=self.categoria)
        r = self.client.get(reverse("devices:dispositivo_delete", args=[disp.pk]))
        self.assertEqual(r.status_code, 405)
        self.assertTrue(Dispositivo.objects.filter(pk=disp.pk).exists())

    def test_eliminar_sin_permiso_devuelve_403(self):
        disp = Dispositivo.objects.create(nombre="X", zona=self.zona_norte, categoria=self.categoria)
        self.client.force_login(self.consulta_norte)
        r = self.client.post(reverse("devices:dispositivo_delete", args=[disp.pk]))
        self.assertEqual(r.status_code, 403)
        self.assertTrue(Dispositivo.objects.filter(pk=disp.pk).exists())

    def test_eliminar_requiere_login(self):
        disp = Dispositivo.objects.create(nombre="X", zona=self.zona_norte, categoria=self.categoria)
        self.client.logout()
        r = self.client.post(reverse("devices:dispositivo_delete", args=[disp.pk]))
        # con raise_exception=True (igual que Categoria) un anónimo recibe 403
        self.assertIn(r.status_code, (302, 403))
        self.assertTrue(Dispositivo.objects.filter(pk=disp.pk).exists())

    def test_no_se_puede_eliminar_ni_editar_de_otra_organizacion(self):
        ajeno = Dispositivo.objects.create(nombre="Ajeno", zona=self.zona_sur, categoria=self.categoria)
        r = self.client.post(reverse("devices:dispositivo_delete", args=[ajeno.pk]))
        self.assertEqual(r.status_code, 404)
        r = self.client.get(reverse("devices:dispositivo_update", args=[ajeno.pk]))
        self.assertEqual(r.status_code, 404)
        self.assertTrue(Dispositivo.objects.filter(pk=ajeno.pk).exists())

    def test_formulario_no_acepta_zona_de_otra_organizacion(self):
        r = self.client.post(reverse("devices:dispositivo_create"),
                             self._payload(zona=self.zona_sur.pk))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Dispositivo.objects.exists())

    def test_csrf_se_exige_en_eliminar(self):
        from django.test import Client
        disp = Dispositivo.objects.create(nombre="X", zona=self.zona_norte, categoria=self.categoria)
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.admin_norte)
        r = c.post(reverse("devices:dispositivo_delete", args=[disp.pk]))
        self.assertEqual(r.status_code, 403)
        self.assertTrue(Dispositivo.objects.filter(pk=disp.pk).exists())
