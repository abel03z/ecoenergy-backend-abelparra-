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
from organizations.models import Department, Organization, Zone
from .models import Category, Device, Manufacturer

TEST_MEDIA = tempfile.mkdtemp(prefix="ecoenergy_test_media_")


def make_image(name="foto.png", fmt="PNG", size=(20, 20)):
    buffer = io.BytesIO()
    Image.new("RGB", size, "green").save(buffer, fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def media_files():
    return [p for p in Path(TEST_MEDIA).rglob("*") if p.is_file()]


@override_settings(MEDIA_ROOT=TEST_MEDIA)
class DeviceImageTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.norte = Organization.objects.create(name="Norte")
        cls.sur = Organization.objects.create(name="Sur")
        d_norte = Department.objects.create(organization=cls.norte, name="Ops N")
        d_sur = Department.objects.create(organization=cls.sur, name="Ops S")
        cls.zona_norte = Zone.objects.create(department=d_norte, name="ZN", consumption_limit=10)
        cls.zona_sur = Zone.objects.create(department=d_sur, name="ZS", consumption_limit=10)
        cls.categoria = Category.objects.create(name="Medidor")
        cls.fabricante = Manufacturer.objects.create(name="Acme")

        group = Group.objects.create(name="Admin org")
        for action in ("add", "change", "delete", "view"):
            group.permissions.add(Permission.objects.get(codename=f"{action}_device"))
        cls.admin_norte = cls._user("admin_norte", cls.norte, group)

        solo_view = Group.objects.create(name="Consulta")
        solo_view.permissions.add(Permission.objects.get(codename="view_device"))
        cls.consulta_norte = cls._user("consulta_norte", cls.norte, solo_view)

    @staticmethod
    def _user(username, org, group):
        user = User.objects.create_user(username, password="x")
        user.groups.add(group)
        UserProfile.objects.create(user=user, organization=org, employee_code=f"E-{username}")
        return user

    def setUp(self):
        shutil.rmtree(TEST_MEDIA, ignore_errors=True)
        Path(TEST_MEDIA).mkdir(parents=True, exist_ok=True)
        self.client.force_login(self.admin_norte)

    def _payload(self, **extra):
        data = {
            "name": "Medidor A",
            "category": self.categoria.pk,
            "manufacturer": self.fabricante.pk,
            "zone": self.zona_norte.pk,
            "is_active": "on",
        }
        data.update(extra)
        return data

    # --- mini desafío: un archivo correcto y tres rechazos ---------------
    def test_imagen_valida_se_guarda(self):
        r = self.client.post(reverse("devices:device_create"),
                             self._payload(image=make_image()))
        self.assertRedirects(r, reverse("devices:dashboard"))
        disp = Device.objects.get(name="Medidor A")
        self.assertTrue(disp.image.name.startswith("devices/"))
        self.assertEqual(len(media_files()), 1)

    def test_imagen_demasiado_grande_se_rechaza(self):
        base = make_image("grande.png")
        grande = SimpleUploadedFile("grande.png", base.read() + b"0" * (2 * 1024 * 1024))
        r = self.client.post(reverse("devices:device_create"),
                             self._payload(image=grande))
        self.assertContains(r, "no puede superar 2 MB")
        self.assertFalse(Device.objects.exists())
        self.assertEqual(media_files(), [])

    def test_extension_prohibida_se_rechaza(self):
        r = self.client.post(reverse("devices:device_create"),
                             self._payload(image=make_image("virus.exe")))
        self.assertContains(r, "Formato no permitido")
        self.assertFalse(Device.objects.exists())
        self.assertEqual(media_files(), [])

    def test_archivo_renombrado_se_rechaza_por_contenido(self):
        falso = SimpleUploadedFile("evidencia.jpg", b"esto no es una imagen")
        r = self.client.post(reverse("devices:device_create"),
                             self._payload(image=falso))
        self.assertContains(r, "no es una imagen válida")
        self.assertFalse(Device.objects.exists())
        self.assertEqual(media_files(), [])

    def test_imagen_es_opcional(self):
        self.client.post(reverse("devices:device_create"), self._payload())
        disp = Device.objects.get(name="Medidor A")
        self.assertFalse(disp.image)
        r = self.client.get(reverse("devices:dashboard"))
        self.assertContains(r, "Sin imagen")

    # --- política de reemplazo / eliminación -----------------------------
    def test_reemplazar_imagen_elimina_la_anterior(self):
        self.client.post(reverse("devices:device_create"),
                         self._payload(image=make_image("uno.png")))
        disp = Device.objects.get()
        antigua = disp.image.name
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("devices:device_update", args=[disp.pk]),
                             self._payload(image=make_image("dos.png")))
        disp.refresh_from_db()
        self.assertNotEqual(disp.image.name, antigua)
        self.assertEqual(len(media_files()), 1)

    def test_editar_sin_nueva_imagen_conserva_la_actual(self):
        self.client.post(reverse("devices:device_create"),
                         self._payload(image=make_image()))
        disp = Device.objects.get()
        antigua = disp.image.name
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("devices:device_update", args=[disp.pk]),
                             self._payload(name="Renombrado"))
        disp.refresh_from_db()
        self.assertEqual(disp.image.name, antigua)
        self.assertEqual(len(media_files()), 1)

    def test_eliminar_borra_registro_y_archivo(self):
        self.client.post(reverse("devices:device_create"),
                         self._payload(image=make_image()))
        disp = Device.objects.get()
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(reverse("devices:device_delete", args=[disp.pk]))
        self.assertRedirects(r, reverse("devices:dashboard"))
        self.assertFalse(Device.objects.exists())
        self.assertEqual(media_files(), [])

    # --- POST, permisos y scoping ----------------------------------------
    def test_eliminar_por_get_no_esta_permitido(self):
        disp = Device.objects.create(name="X", zone=self.zona_norte, category=self.categoria, manufacturer=self.fabricante)
        r = self.client.get(reverse("devices:device_delete", args=[disp.pk]))
        self.assertEqual(r.status_code, 405)
        self.assertTrue(Device.objects.filter(pk=disp.pk).exists())

    def test_eliminar_sin_permiso_devuelve_403(self):
        disp = Device.objects.create(name="X", zone=self.zona_norte, category=self.categoria, manufacturer=self.fabricante)
        self.client.force_login(self.consulta_norte)
        r = self.client.post(reverse("devices:device_delete", args=[disp.pk]))
        self.assertEqual(r.status_code, 403)
        self.assertTrue(Device.objects.filter(pk=disp.pk).exists())

    def test_eliminar_requiere_login(self):
        disp = Device.objects.create(name="X", zone=self.zona_norte, category=self.categoria, manufacturer=self.fabricante)
        self.client.logout()
        r = self.client.post(reverse("devices:device_delete", args=[disp.pk]))
        # con raise_exception=True (igual que Categoria) un anónimo recibe 403
        self.assertIn(r.status_code, (302, 403))
        self.assertTrue(Device.objects.filter(pk=disp.pk).exists())

    def test_no_se_puede_eliminar_ni_editar_de_otra_organizacion(self):
        ajeno = Device.objects.create(name="Ajeno", zone=self.zona_sur, category=self.categoria, manufacturer=self.fabricante)
        r = self.client.post(reverse("devices:device_delete", args=[ajeno.pk]))
        self.assertEqual(r.status_code, 404)
        r = self.client.get(reverse("devices:device_update", args=[ajeno.pk]))
        self.assertEqual(r.status_code, 404)
        self.assertTrue(Device.objects.filter(pk=ajeno.pk).exists())

    def test_formulario_no_acepta_zona_de_otra_organizacion(self):
        r = self.client.post(reverse("devices:device_create"),
                             self._payload(zone=self.zona_sur.pk))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Device.objects.exists())

    def test_csrf_se_exige_en_eliminar(self):
        from django.test import Client
        disp = Device.objects.create(name="X", zone=self.zona_norte, category=self.categoria, manufacturer=self.fabricante)
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.admin_norte)
        r = c.post(reverse("devices:device_delete", args=[disp.pk]))
        self.assertEqual(r.status_code, 403)
        self.assertTrue(Device.objects.filter(pk=disp.pk).exists())
