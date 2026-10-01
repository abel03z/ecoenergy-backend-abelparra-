from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from devices.models import Category, Device, Manufacturer

from .models import Department, Organization, Zone


def make_user(username, org, group):
    user = User.objects.create_user(username, password="x")
    user.groups.add(group)
    UserProfile.objects.create(user=user, organization=org, employee_code=f"E-{username}")
    return user


def make_group(name, model, actions):
    group = Group.objects.create(name=name)
    for action in actions:
        group.permissions.add(Permission.objects.get(codename=f"{action}_{model}"))
    return group


class ZoneCrudTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.norte = Organization.objects.create(name="Norte")
        cls.sur = Organization.objects.create(name="Sur")
        cls.dept_norte = Department.objects.create(organization=cls.norte, name="Ops N")
        cls.dept_sur = Department.objects.create(organization=cls.sur, name="Ops S")
        cls.zone_norte = Zone.objects.create(department=cls.dept_norte, name="Zona N1", consumption_limit=10)
        cls.zone_sur = Zone.objects.create(department=cls.dept_sur, name="Zona S1", consumption_limit=10)

        full = make_group("Admin zonas", "zone", ("add", "change", "delete", "view"))
        read_only = make_group("Lector zonas", "zone", ("view",))
        cls.admin = make_user("admin_n", cls.norte, full)
        cls.reader = make_user("reader_n", cls.norte, read_only)

    def setUp(self):
        self.client.force_login(self.admin)

    def _payload(self, **extra):
        data = {"department": self.dept_norte.pk, "name": "Zona Nueva", "consumption_limit": "25.5"}
        data.update(extra)
        return data

    # --- acceso
    def test_requiere_login(self):
        self.client.logout()
        r = self.client.get(reverse("organizations:zone_list"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/accounts/login/", r.url)

    def test_lector_puede_listar_pero_no_crear_editar_ni_eliminar(self):
        self.client.force_login(self.reader)
        self.assertEqual(self.client.get(reverse("organizations:zone_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("organizations:zone_create")).status_code, 403)
        self.assertEqual(self.client.post(reverse("organizations:zone_create"), self._payload()).status_code, 403)
        self.assertEqual(self.client.get(reverse("organizations:zone_update", args=[self.zone_norte.pk])).status_code, 403)
        r = self.client.post(reverse("organizations:zone_delete", args=[self.zone_norte.pk]))
        self.assertEqual(r.status_code, 403)
        self.assertTrue(Zone.objects.filter(pk=self.zone_norte.pk).exists())

    # --- create / update
    def test_crear_zona(self):
        r = self.client.post(reverse("organizations:zone_create"), self._payload())
        self.assertRedirects(r, reverse("organizations:zone_list"))
        self.assertTrue(Zone.objects.filter(name="Zona Nueva", department=self.dept_norte).exists())

    def test_actualizar_zona(self):
        r = self.client.post(
            reverse("organizations:zone_update", args=[self.zone_norte.pk]),
            self._payload(name="Renombrada"),
        )
        self.assertRedirects(r, reverse("organizations:zone_list"))
        self.zone_norte.refresh_from_db()
        self.assertEqual(self.zone_norte.name, "Renombrada")

    # --- validaciones
    def test_limite_de_consumo_fuera_de_rango(self):
        for bad in ("0", "-3", "100001"):
            r = self.client.post(reverse("organizations:zone_create"), self._payload(consumption_limit=bad))
            self.assertEqual(r.status_code, 200, bad)
            self.assertIn("consumption_limit", r.context["form"].errors, bad)
        self.assertFalse(Zone.objects.filter(name="Zona Nueva").exists())

    def test_nombre_muy_corto(self):
        r = self.client.post(reverse("organizations:zone_create"), self._payload(name=" ab "))
        self.assertIn("name", r.context["form"].errors)

    def test_nombre_duplicado_en_el_mismo_departamento(self):
        r = self.client.post(reverse("organizations:zone_create"), self._payload(name="zona n1"))
        self.assertIn("name", r.context["form"].errors)
        self.assertEqual(Zone.objects.filter(department=self.dept_norte).count(), 1)

    def test_editar_sin_cambiar_el_nombre_no_es_duplicado(self):
        r = self.client.post(
            reverse("organizations:zone_update", args=[self.zone_norte.pk]),
            self._payload(name="Zona N1", consumption_limit="99"),
        )
        self.assertRedirects(r, reverse("organizations:zone_list"))

    # --- scoping
    def test_listado_solo_muestra_zonas_de_mi_organizacion(self):
        r = self.client.get(reverse("organizations:zone_list"))
        self.assertContains(r, "Zona N1")
        self.assertNotContains(r, "Zona S1")

    def test_no_puede_editar_ni_eliminar_zona_de_otra_organizacion(self):
        r = self.client.get(reverse("organizations:zone_update", args=[self.zone_sur.pk]))
        self.assertEqual(r.status_code, 404)
        r = self.client.post(reverse("organizations:zone_delete", args=[self.zone_sur.pk]))
        self.assertEqual(r.status_code, 404)
        self.assertTrue(Zone.objects.filter(pk=self.zone_sur.pk).exists())

    def test_no_puede_crear_zona_en_departamento_de_otra_organizacion(self):
        r = self.client.post(
            reverse("organizations:zone_create"), self._payload(department=self.dept_sur.pk)
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("department", r.context["form"].errors)

    # --- borrado lógico
    def test_eliminar_es_borrado_logico(self):
        r = self.client.post(reverse("organizations:zone_delete", args=[self.zone_norte.pk]))
        self.assertRedirects(r, reverse("organizations:zone_list"))
        self.assertFalse(Zone.objects.filter(pk=self.zone_norte.pk).exists())
        self.assertIsNotNone(Zone.all_objects.get(pk=self.zone_norte.pk).deleted_at)
        self.assertNotContains(self.client.get(reverse("organizations:zone_list")), "Zona N1")

    def test_eliminar_por_get_no_esta_permitido(self):
        r = self.client.get(reverse("organizations:zone_delete", args=[self.zone_norte.pk]))
        self.assertEqual(r.status_code, 405)
        self.assertTrue(Zone.objects.filter(pk=self.zone_norte.pk).exists())

    def test_no_elimina_zona_con_dispositivos_vivos(self):
        Device.objects.create(
            name="D1", zone=self.zone_norte,
            category=Category.objects.create(name="Cat"),
            manufacturer=Manufacturer.objects.create(name="Acme"),
        )
        self.client.post(reverse("organizations:zone_delete", args=[self.zone_norte.pk]))
        self.assertTrue(Zone.objects.filter(pk=self.zone_norte.pk).exists())

    def test_nombre_de_zona_eliminada_se_puede_reutilizar(self):
        self.client.post(reverse("organizations:zone_delete", args=[self.zone_norte.pk]))
        r = self.client.post(reverse("organizations:zone_create"), self._payload(name="Zona N1"))
        self.assertRedirects(r, reverse("organizations:zone_list"))

    # --- paginación
    def test_listado_paginado_con_tamano_en_sesion(self):
        for i in range(20):
            Zone.objects.create(department=self.dept_norte, name=f"Extra {i:02d}", consumption_limit=5)
        self.assertEqual(len(self.client.get(reverse("organizations:zone_list")).context["page_obj"]), 5)
        r = self.client.get(reverse("organizations:zone_list"), {"page_size": 15})
        self.assertEqual(len(r.context["page_obj"]), 15)
        r = self.client.get(reverse("organizations:zone_list"), {"page_size": 7})
        self.assertEqual(len(r.context["page_obj"]), 15)


class ZoneFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.norte = Organization.objects.create(name="Norte")
        cls.sur = Organization.objects.create(name="Sur")
        cls.ops = Department.objects.create(organization=cls.norte, name="Operaciones")
        cls.adm = Department.objects.create(organization=cls.norte, name="Administración")
        cls.ops_sur = Department.objects.create(organization=cls.sur, name="Operaciones")
        Zone.objects.create(department=cls.ops, name="Planta A", consumption_limit=10)
        Zone.objects.create(department=cls.ops, name="Bodega", consumption_limit=10)
        Zone.objects.create(department=cls.adm, name="Planta B", consumption_limit=10)
        Zone.objects.create(department=cls.ops_sur, name="Planta Sur", consumption_limit=10)
        group = make_group("Lector zonas filtro", "zone", ("view",))
        cls.user = make_user("z_filter", cls.norte, group)
        cls.root = User.objects.create_superuser("z_root", password="x")

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("organizations:zone_list")

    def names(self, params=None):
        r = self.client.get(self.url, params or {})
        self.assertEqual(r.status_code, 200)
        return [z.name for z in r.context["page_obj"]]

    def test_filtra_por_nombre(self):
        self.assertEqual(self.names({"q": "planta"}), ["Planta A", "Planta B"])

    def test_filtra_por_departamento(self):
        self.assertEqual(self.names({"department": self.ops.pk}), ["Bodega", "Planta A"])

    def test_combina_nombre_y_departamento(self):
        self.assertEqual(self.names({"q": "planta", "department": self.adm.pk}), ["Planta B"])

    def test_no_se_puede_filtrar_por_departamento_de_otra_organizacion(self):
        # inválido para este usuario: se ignora y no aparecen zonas de Sur
        result = self.names({"department": self.ops_sur.pk})
        self.assertNotIn("Planta Sur", result)
        self.assertEqual(len(result), 3)

    def test_superusuario_ve_departamentos_con_su_organizacion(self):
        self.client.force_login(self.root)
        r = self.client.get(self.url)
        labels = [label for _, label in r.context["filter_form"].fields["department"].choices]
        self.assertIn("Operaciones · Norte", labels)
        self.assertIn("Operaciones · Sur", labels)

    def test_sin_resultados(self):
        self.assertContains(self.client.get(self.url, {"q": "zzz"}), "Ninguna zona coincide con los filtros.")
