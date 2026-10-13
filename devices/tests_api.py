from django.contrib.auth.models import Group, User
from rest_framework.test import APITestCase

from accounts.models import UserProfile
from devices.models import Category, Device, Manufacturer
from devices.permissions import GRUPO_ADMIN, GRUPO_OPERADOR
from organizations.models import Department, Organization, Zone

PASSWORD = "Prueba-Segura-123!"  # solo para pruebas locales


class DeviceApiJwtTests(APITestCase):
    """Clase 2: JWT + permisos por rol + alcance por organización."""

    @classmethod
    def setUpTestData(cls):
        cls.org_norte = Organization.objects.create(name="Norte")
        cls.org_sur = Organization.objects.create(name="Sur")
        dep_n = Department.objects.create(organization=cls.org_norte, name="Dep N")
        dep_s = Department.objects.create(organization=cls.org_sur, name="Dep S")
        cls.zone_n = Zone.objects.create(department=dep_n, name="Zona N", consumption_limit=100)
        cls.zone_s = Zone.objects.create(department=dep_s, name="Zona S", consumption_limit=100)
        cls.category = Category.objects.create(name="Sensores")
        cls.manufacturer = Manufacturer.objects.create(name="Fab")

        g_admin = Group.objects.create(name=GRUPO_ADMIN)
        g_oper = Group.objects.create(name=GRUPO_OPERADOR)

        def crear(username, org, grupo=None, code="X"):
            u = User.objects.create_user(username=username, password=PASSWORD)
            if grupo:
                u.groups.add(grupo)
            UserProfile.objects.create(user=u, organization=org, employee_code=code)
            return u

        cls.admin = crear("admin_api", cls.org_norte, g_admin, "E1")
        cls.operador = crear("operador_api", cls.org_norte, g_oper, "E2")
        cls.sin_grupo = crear("sin_grupo", cls.org_norte, None, "E3")

        cls.dev_norte = Device.objects.create(
            name="Sensor Norte", zone=cls.zone_n, category=cls.category, manufacturer=cls.manufacturer
        )
        cls.dev_sur = Device.objects.create(
            name="Sensor Sur", zone=cls.zone_s, category=cls.category, manufacturer=cls.manufacturer
        )

    # --- helpers -----------------------------------------------------------
    def tokens(self, username):
        r = self.client.post(
            "/api/token/", {"username": username, "password": PASSWORD}, format="json"
        )
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def auth(self, username):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.tokens(username)['access']}")

    def payload(self, **extra):
        data = {
            "name": "Sensor Patio",
            "category": self.category.pk,
            "manufacturer": self.manufacturer.pk,
            "zone": self.zone_n.pk,
            "is_active": True,
        }
        data.update(extra)
        return data

    # --- token -------------------------------------------------------------
    def test_token_devuelve_access_y_refresh(self):
        t = self.tokens("operador_api")
        self.assertIn("access", t)
        self.assertIn("refresh", t)

    def test_credenciales_malas_401(self):
        r = self.client.post("/api/token/", {"username": "operador_api", "password": "x"}, format="json")
        self.assertEqual(r.status_code, 401)

    def test_refresh_entrega_nuevo_access(self):
        refresh = self.tokens("operador_api")["refresh"]
        r = self.client.post("/api/token/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.json())

    # --- 401 ---------------------------------------------------------------
    def test_get_sin_token_401(self):
        self.assertEqual(self.client.get("/api/devices/").status_code, 401)

    def test_refresh_como_bearer_401(self):
        refresh = self.tokens("operador_api")["refresh"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh}")
        self.assertEqual(self.client.get("/api/devices/").status_code, 401)

    # --- operador ----------------------------------------------------------
    def test_operador_get_200(self):
        self.auth("operador_api")
        self.assertEqual(self.client.get("/api/devices/").status_code, 200)

    def test_operador_post_403(self):
        self.auth("operador_api")
        self.assertEqual(self.client.post("/api/devices/", self.payload(), format="json").status_code, 403)

    def test_operador_patch_y_delete_403(self):
        self.auth("operador_api")
        url = f"/api/devices/{self.dev_norte.pk}/"
        self.assertEqual(self.client.patch(url, {"name": "Otro"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(url).status_code, 403)

    # --- sin grupo ---------------------------------------------------------
    def test_sin_grupo_get_403(self):
        self.auth("sin_grupo")
        self.assertEqual(self.client.get("/api/devices/").status_code, 403)

    # --- administrador -----------------------------------------------------
    def test_admin_crud_completo(self):
        self.auth("admin_api")
        r = self.client.post("/api/devices/", self.payload(), format="json")
        self.assertEqual(r.status_code, 201, r.content)  # 201
        pk = r.json()["id"]
        r = self.client.patch(f"/api/devices/{pk}/", {"name": "Sensor Sala"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.delete(f"/api/devices/{pk}/").status_code, 204)
        self.assertEqual(self.client.get(f"/api/devices/{pk}/").status_code, 404)

    def test_admin_post_invalido_400(self):
        self.auth("admin_api")
        r = self.client.post("/api/devices/", self.payload(name="ab", zone=9999), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("name", r.json())
        self.assertIn("zone", r.json())

    def test_admin_id_inexistente_404(self):
        self.auth("admin_api")
        self.assertEqual(self.client.get("/api/devices/99999/").status_code, 404)

    def test_delete_es_borrado_logico(self):
        self.auth("admin_api")
        self.client.delete(f"/api/devices/{self.dev_norte.pk}/")
        self.assertTrue(Device.all_objects.get(pk=self.dev_norte.pk).is_deleted)

    # --- alcance por organización -----------------------------------------
    def test_lista_solo_muestra_su_organizacion(self):
        self.auth("operador_api")
        ids = [d["id"] for d in self.client.get("/api/devices/").json()["results"]]
        self.assertIn(self.dev_norte.pk, ids)
        self.assertNotIn(self.dev_sur.pk, ids)

    def test_detalle_de_otra_organizacion_404(self):
        self.auth("admin_api")
        self.assertEqual(self.client.get(f"/api/devices/{self.dev_sur.pk}/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/devices/{self.dev_sur.pk}/").status_code, 404)

    def test_admin_no_crea_en_zona_de_otra_organizacion(self):
        self.auth("admin_api")
        r = self.client.post("/api/devices/", self.payload(zone=self.zone_s.pk), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("zone", r.json())
