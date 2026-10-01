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

    def test_eliminar_es_borrado_logico_y_conserva_archivo(self):
        self.client.post(reverse("devices:device_create"),
                         self._payload(image=make_image()))
        disp = Device.objects.get()
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(reverse("devices:device_delete", args=[disp.pk]))
        self.assertRedirects(r, reverse("devices:dashboard"))
        # ya no aparece en consultas normales...
        self.assertFalse(Device.objects.filter(pk=disp.pk).exists())
        # ...pero la fila sigue en la BD con deleted_at y la imagen se conserva
        fila = Device.all_objects.get(pk=disp.pk)
        self.assertIsNotNone(fila.deleted_at)
        self.assertEqual(len(media_files()), 1)

    def test_dispositivo_eliminado_no_aparece_en_el_listado(self):
        disp = Device.objects.create(name="Fantasma", zone=self.zona_norte,
                                     category=self.categoria, manufacturer=self.fabricante)
        self.assertContains(self.client.get(reverse("devices:dashboard")), "Fantasma")
        self.client.post(reverse("devices:device_delete", args=[disp.pk]))
        self.assertNotContains(self.client.get(reverse("devices:dashboard")), "Fantasma")

    def test_dispositivo_eliminado_no_se_puede_editar(self):
        disp = Device.objects.create(name="X", zone=self.zona_norte,
                                     category=self.categoria, manufacturer=self.fabricante)
        self.client.post(reverse("devices:device_delete", args=[disp.pk]))
        r = self.client.get(reverse("devices:device_update", args=[disp.pk]))
        self.assertEqual(r.status_code, 404)

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


class CategorySoftDeleteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        org = Organization.objects.create(name="Org")
        dept = Department.objects.create(organization=org, name="D")
        cls.zone = Zone.objects.create(department=dept, name="Z", consumption_limit=10)
        cls.maker = Manufacturer.objects.create(name="Acme")

        full = Group.objects.create(name="Admin categorías")
        for action in ("add", "change", "delete", "view"):
            full.permissions.add(Permission.objects.get(codename=f"{action}_category"))
        only_view = Group.objects.create(name="Lector categorías")
        only_view.permissions.add(Permission.objects.get(codename="view_category"))

        cls.admin = User.objects.create_user("cat_admin", password="x")
        cls.admin.groups.add(full)
        cls.reader = User.objects.create_user("cat_reader", password="x")
        cls.reader.groups.add(only_view)

    def setUp(self):
        self.client.force_login(self.admin)

    def test_eliminar_categoria_es_borrado_logico(self):
        cat = Category.objects.create(name="Temporal")
        r = self.client.post(reverse("devices:category_delete", args=[cat.pk]))
        self.assertRedirects(r, reverse("devices:category_list"))
        self.assertFalse(Category.objects.filter(pk=cat.pk).exists())
        self.assertIsNotNone(Category.all_objects.get(pk=cat.pk).deleted_at)
        self.assertNotContains(self.client.get(reverse("devices:category_list")), "Temporal")

    def test_no_elimina_categoria_con_dispositivos_vivos(self):
        cat = Category.objects.create(name="En uso")
        Device.objects.create(name="D1", zone=self.zone, category=cat, manufacturer=self.maker)
        self.client.post(reverse("devices:category_delete", args=[cat.pk]))
        self.assertTrue(Category.objects.filter(pk=cat.pk).exists())

    def test_eliminar_categoria_por_get_no_esta_permitido(self):
        cat = Category.objects.create(name="Temporal")
        r = self.client.get(reverse("devices:category_delete", args=[cat.pk]))
        self.assertEqual(r.status_code, 405)
        self.assertTrue(Category.objects.filter(pk=cat.pk).exists())

    def test_eliminar_categoria_sin_permiso_devuelve_403(self):
        cat = Category.objects.create(name="Temporal")
        self.client.force_login(self.reader)
        r = self.client.post(reverse("devices:category_delete", args=[cat.pk]))
        self.assertEqual(r.status_code, 403)
        self.assertTrue(Category.objects.filter(pk=cat.pk).exists())

    def test_nombre_de_categoria_eliminada_se_puede_reutilizar(self):
        cat = Category.objects.create(name="Reutilizable")
        self.client.post(reverse("devices:category_delete", args=[cat.pk]))
        r = self.client.post(reverse("devices:category_create"), {"name": "Reutilizable"})
        self.assertRedirects(r, reverse("devices:category_list"))


class PaginationSessionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Organization.objects.create(name="Org")
        group = Group.objects.create(name="Lectores")
        group.permissions.add(Permission.objects.get(codename="view_category"))
        cls.user = User.objects.create_user("pager", password="x")
        cls.user.groups.add(group)
        for i in range(40):
            Category.objects.create(name=f"Categoría {i:02d}")

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("devices:category_list")

    def test_por_defecto_son_5_por_pagina(self):
        r = self.client.get(self.url)
        self.assertEqual(len(r.context["page_obj"]), 5)

    def test_tamanos_permitidos_5_15_30(self):
        for size in (5, 15, 30):
            r = self.client.get(self.url, {"page_size": size})
            self.assertEqual(len(r.context["page_obj"]), size)

    def test_la_seleccion_persiste_en_la_sesion(self):
        self.client.get(self.url, {"page_size": 15})
        self.assertEqual(self.client.session["page_size"], 15)
        r = self.client.get(self.url)  # sin parámetro
        self.assertEqual(len(r.context["page_obj"]), 15)

    def test_valores_no_permitidos_se_normalizan(self):
        self.client.get(self.url, {"page_size": 15})
        for raw in ("10", "9999", "-5", "abc", "0"):
            r = self.client.get(self.url, {"page_size": raw})
            self.assertEqual(len(r.context["page_obj"]), 15, raw)
        self.assertEqual(self.client.session["page_size"], 15)

    def test_valor_invalido_sin_preferencia_usa_el_defecto(self):
        r = self.client.get(self.url, {"page_size": "9999"})
        self.assertEqual(len(r.context["page_obj"]), 5)


class DeviceFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.norte = Organization.objects.create(name="Norte")
        cls.sur = Organization.objects.create(name="Sur")
        d_norte = Department.objects.create(organization=cls.norte, name="Ops N")
        d_sur = Department.objects.create(organization=cls.sur, name="Ops S")
        cls.z1 = Zone.objects.create(department=d_norte, name="Zona 1", consumption_limit=10)
        cls.z2 = Zone.objects.create(department=d_norte, name="Zona 2", consumption_limit=10)
        cls.z_sur = Zone.objects.create(department=d_sur, name="Zona Sur", consumption_limit=10)
        cls.bomba = Category.objects.create(name="Bomba de agua")
        cls.medidor = Category.objects.create(name="Medidor")
        cls.abb = Manufacturer.objects.create(name="ABB")
        cls.bosch = Manufacturer.objects.create(name="Bosch")

        def device(name, zone, category, maker):
            return Device.objects.create(name=name, zone=zone, category=category, manufacturer=maker)

        device("Bomba 001", cls.z1, cls.bomba, cls.abb)
        device("Bomba 002", cls.z2, cls.bomba, cls.bosch)
        device("Medidor 001", cls.z1, cls.medidor, cls.abb)
        device("Medidor Sur", cls.z_sur, cls.bomba, cls.abb)

        group = Group.objects.create(name="Lector dispositivos")
        group.permissions.add(Permission.objects.get(codename="view_device"))
        cls.user = User.objects.create_user("f_user", password="x")
        cls.user.groups.add(group)
        UserProfile.objects.create(user=cls.user, organization=cls.norte, employee_code="F1")

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("devices:dashboard")

    def names(self, params=None):
        r = self.client.get(self.url, params or {})
        self.assertEqual(r.status_code, 200)
        return [d.name for d in r.context["page_obj"]]

    def test_sin_filtros_muestra_los_de_mi_organizacion(self):
        self.assertEqual(self.names(), ["Bomba 001", "Bomba 002", "Medidor 001"])

    def test_filtra_por_categoria(self):
        self.assertEqual(self.names({"category": self.bomba.pk}), ["Bomba 001", "Bomba 002"])

    def test_filtra_por_fabricante(self):
        self.assertEqual(self.names({"manufacturer": self.abb.pk}), ["Bomba 001", "Medidor 001"])

    def test_filtra_por_zona(self):
        self.assertEqual(self.names({"zone": self.z2.pk}), ["Bomba 002"])

    def test_filtra_por_nombre(self):
        self.assertEqual(self.names({"q": "medidor"}), ["Medidor 001"])

    def test_combina_filtros(self):
        self.assertEqual(self.names({"category": self.bomba.pk, "manufacturer": self.abb.pk}), ["Bomba 001"])

    def test_no_se_puede_filtrar_por_zona_de_otra_organizacion(self):
        # el valor es inválido para este usuario: se ignora y no se filtran datos ajenos
        self.assertEqual(self.names({"zone": self.z_sur.pk}), ["Bomba 001", "Bomba 002", "Medidor 001"])
        self.assertNotIn("Medidor Sur", self.names({"category": self.bomba.pk}))

    def test_valores_invalidos_se_ignoran(self):
        self.assertEqual(self.names({"category": "abc", "zone": "99999"}),
                         ["Bomba 001", "Bomba 002", "Medidor 001"])

    def test_sin_resultados_muestra_mensaje(self):
        r = self.client.get(self.url, {"q": "no existe"})
        self.assertContains(r, "Ningún dispositivo coincide con los filtros.")

    def test_la_paginacion_conserva_los_filtros(self):
        for i in range(20):
            Device.objects.create(name=f"Bomba extra {i:02d}", zone=self.z1,
                                  category=self.bomba, manufacturer=self.abb)
        r = self.client.get(self.url, {"category": self.bomba.pk})
        self.assertContains(r, f"?category={self.bomba.pk}&amp;page=2")
        self.assertContains(r, f"?category={self.bomba.pk}&amp;page_size=15")


class ActionsColumnTests(TestCase):
    """La columna «Acciones» solo aparece si el usuario puede editar o eliminar."""

    @classmethod
    def setUpTestData(cls):
        org = Organization.objects.create(name="Org")
        dept = Department.objects.create(organization=org, name="D")
        zone = Zone.objects.create(department=dept, name="Z", consumption_limit=10)
        Device.objects.create(name="Dev", zone=zone, category=Category.objects.create(name="Cat"),
                              manufacturer=Manufacturer.objects.create(name="Acme"))
        reader = Group.objects.create(name="Solo ver")
        for codename in ("view_device", "view_category"):
            reader.permissions.add(Permission.objects.get(codename=codename))
        editor = Group.objects.create(name="Editor")
        for codename in ("view_device", "change_device", "view_category", "change_category"):
            editor.permissions.add(Permission.objects.get(codename=codename))
        cls.reader = User.objects.create_user("a_reader", password="x")
        cls.reader.groups.add(reader)
        UserProfile.objects.create(user=cls.reader, organization=org, employee_code="A1")
        cls.editor = User.objects.create_user("a_editor", password="x")
        cls.editor.groups.add(editor)
        UserProfile.objects.create(user=cls.editor, organization=org, employee_code="A2")

    def test_lector_no_ve_la_columna_acciones(self):
        self.client.force_login(self.reader)
        for name in ("devices:dashboard", "devices:category_list"):
            self.assertNotContains(self.client.get(reverse(name)), "Acciones", msg_prefix=name)

    def test_con_permiso_de_edicion_si_la_ve(self):
        self.client.force_login(self.editor)
        for name in ("devices:dashboard", "devices:category_list"):
            self.assertContains(self.client.get(reverse(name)), "Acciones", msg_prefix=name)



class CategoryFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        for name in ("Bomba de agua", "Medidor de agua", "Medidor eléctrico", "Inversor"):
            Category.objects.create(name=name)
        group = Group.objects.create(name="Lector categorías filtro")
        group.permissions.add(Permission.objects.get(codename="view_category"))
        cls.user = User.objects.create_user("c_filter", password="x")
        cls.user.groups.add(group)

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("devices:category_list")

    def names(self, params=None):
        r = self.client.get(self.url, params or {})
        self.assertEqual(r.status_code, 200)
        return [c.name for c in r.context["categories"]]

    def test_filtra_por_nombre(self):
        self.assertEqual(self.names({"q": "agua"}), ["Bomba de agua", "Medidor de agua"])
        self.assertEqual(self.names({"q": "MEDIDOR"}), ["Medidor de agua", "Medidor eléctrico"])

    def test_sin_filtros_y_sin_resultados(self):
        self.assertEqual(len(self.names()), 4)
        r = self.client.get(self.url, {"q": "zzz"})
        self.assertContains(r, "Ninguna categoría coincide con los filtros.")

    def test_paginacion_conserva_el_filtro(self):
        for i in range(8):
            Category.objects.create(name=f"Agua extra {i}")
        r = self.client.get(self.url, {"q": "agua"})
        self.assertContains(r, "?q=agua&amp;page=2")
