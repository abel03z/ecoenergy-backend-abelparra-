"""Evaluación sumativa 3: los seis recursos de la API (JWT, roles, validaciones, paginación)."""
from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import UserProfile
from devices.models import Category, Device, Manufacturer
from devices.permissions import GRUPO_ADMIN, GRUPO_OPERADOR
from monitoring.models import Alert, Measurement
from organizations.models import Department, Organization, Zone

PASSWORD = "Prueba-Segura-123!"  # solo para pruebas locales

PRINCIPALES = ["devices", "zones", "categories", "manufacturers"]
OPERACIONALES = ["measurements", "alerts"]


class SeisRecursosApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Norte")
        cls.org_sur = Organization.objects.create(name="Sur")
        cls.dep = Department.objects.create(organization=cls.org, name="Ops")
        cls.dep_sur = Department.objects.create(organization=cls.org_sur, name="Ops Sur")
        cls.zone = Zone.objects.create(department=cls.dep, name="Zona 1", consumption_limit=50)
        cls.zone_sur = Zone.objects.create(department=cls.dep_sur, name="Zona S", consumption_limit=50)
        cls.cat = Category.objects.create(name="Sensores")
        cls.man = Manufacturer.objects.create(name="ABB", country="Suiza")
        cls.device = Device.objects.create(name="Medidor 1", zone=cls.zone, category=cls.cat, manufacturer=cls.man)
        cls.device_sur = Device.objects.create(name="Medidor S", zone=cls.zone_sur, category=cls.cat, manufacturer=cls.man)
        now = timezone.now()
        Measurement.objects.bulk_create(
            [Measurement(device=cls.device, consumption_value=i, measured_at=now - timedelta(minutes=i)) for i in range(45)]
        )
        Measurement.objects.create(device=cls.device_sur, consumption_value=1, measured_at=now)
        cls.alert = Alert.objects.create(device=cls.device, level="INFO", status="OPEN", message="ok", generated_at=now)

        g_admin = Group.objects.create(name=GRUPO_ADMIN)
        g_oper = Group.objects.create(name=GRUPO_OPERADOR)

        def crear(username, grupo, code):
            u = User.objects.create_user(username=username, password=PASSWORD)
            if grupo:
                u.groups.add(grupo)
            UserProfile.objects.create(user=u, organization=cls.org, employee_code=code)

        crear("admin_x", g_admin, "A1")
        crear("operador_x", g_oper, "A2")
        crear("sin_rol_x", None, "A3")

    def auth(self, username):
        r = self.client.post("/api/token/", {"username": username, "password": PASSWORD}, format="json")
        self.assertEqual(r.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.json()['access']}")

    # --- 401 / 403 en las seis rutas -------------------------------------
    def test_sin_token_401_en_las_seis(self):
        for r in PRINCIPALES + OPERACIONALES:
            self.assertEqual(self.client.get(f"/api/{r}/").status_code, 401, r)

    def test_sin_rol_403_en_las_seis(self):
        self.auth("sin_rol_x")
        for r in PRINCIPALES + OPERACIONALES:
            self.assertEqual(self.client.get(f"/api/{r}/").status_code, 403, r)

    def test_operador_lee_las_seis_y_no_escribe(self):
        self.auth("operador_x")
        for r in PRINCIPALES + OPERACIONALES:
            self.assertEqual(self.client.get(f"/api/{r}/").status_code, 200, r)
        for r in PRINCIPALES:
            self.assertEqual(self.client.post(f"/api/{r}/", {}, format="json").status_code, 403, r)

    def test_admin_lee_el_detalle_de_las_seis(self):
        self.auth("admin_x")
        ids = {"devices": self.device.pk, "zones": self.zone.pk, "categories": self.cat.pk,
               "manufacturers": self.man.pk, "measurements": Measurement.objects.filter(device=self.device).first().pk,
               "alerts": self.alert.pk}
        for r, pk in ids.items():
            self.assertEqual(self.client.get(f"/api/{r}/{pk}/").status_code, 200, r)

    def test_operacionales_no_aceptan_escritura(self):
        self.auth("admin_x")
        for r in OPERACIONALES:
            self.assertEqual(self.client.post(f"/api/{r}/", {}, format="json").status_code, 405, r)

    # --- CRUD de las principales nuevas -----------------------------------
    def test_crud_zone(self):
        self.auth("admin_x")
        r = self.client.post("/api/zones/", {"name": "Zona Nueva", "department": self.dep.pk, "consumption_limit": 10}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        pk = r.json()["id"]
        self.assertEqual(self.client.get(f"/api/zones/{pk}/").status_code, 200)
        self.assertEqual(self.client.patch(f"/api/zones/{pk}/", {"consumption_limit": 20}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/zones/{pk}/").status_code, 204)
        self.assertEqual(self.client.get(f"/api/zones/{pk}/").status_code, 404)
        self.assertTrue(Zone.all_objects.get(pk=pk).is_deleted)

    def test_crud_category_y_manufacturer(self):
        self.auth("admin_x")
        for recurso, body in (("categories", {"name": "Inversor"}), ("manufacturers", {"name": "Siemens", "country": "Alemania"})):
            r = self.client.post(f"/api/{recurso}/", body, format="json")
            self.assertEqual(r.status_code, 201, r.content)
            pk = r.json()["id"]
            self.assertEqual(self.client.put(f"/api/{recurso}/{pk}/", {**body, "name": body["name"] + " 2"}, format="json").status_code, 200)
            self.assertEqual(self.client.delete(f"/api/{recurso}/{pk}/").status_code, 204)

    # --- validaciones y 404 ----------------------------------------------
    def test_zone_validaciones_400(self):
        self.auth("admin_x")
        r = self.client.post("/api/zones/", {"name": "Zona Z", "department": self.dep.pk, "consumption_limit": 0}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("consumption_limit", r.json())
        r = self.client.post("/api/zones/", {"name": "zona 1", "department": self.dep.pk, "consumption_limit": 5}, format="json")
        self.assertEqual(r.status_code, 400)  # nombre repetido en el departamento
        r = self.client.post("/api/zones/", {"name": "Zona X", "department": self.dep_sur.pk, "consumption_limit": 5}, format="json")
        self.assertEqual(r.status_code, 400)  # departamento de otra organización

    def test_id_inexistente_404(self):
        self.auth("admin_x")
        for r in PRINCIPALES + OPERACIONALES:
            self.assertEqual(self.client.get(f"/api/{r}/999999/").status_code, 404, r)

    def test_no_borra_zona_con_dispositivos(self):
        self.auth("admin_x")
        self.assertEqual(self.client.delete(f"/api/zones/{self.zone.pk}/").status_code, 409)

    # --- alcance por organización ------------------------------------------
    def test_operacionales_solo_de_mi_organizacion(self):
        self.auth("operador_x")
        for r in self.client.get("/api/measurements/?page_size=100").json()["results"]:
            self.assertEqual(r["device"], self.device.pk)

    # --- paginación ---------------------------------------------------------
    def test_paginacion_dos_paginas_distintas(self):
        self.auth("operador_x")
        p1 = self.client.get("/api/measurements/?page=1").json()
        p2 = self.client.get("/api/measurements/?page=2").json()
        self.assertEqual(p1["count"], 45)
        self.assertEqual(len(p1["results"]), 20)
        self.assertIsNotNone(p1["next"])
        ids1 = {m["id"] for m in p1["results"]}
        ids2 = {m["id"] for m in p2["results"]}
        self.assertFalse(ids1 & ids2)

    def test_page_size_maximo_100(self):
        self.auth("operador_x")
        r = self.client.get("/api/measurements/?page_size=1000").json()
        self.assertLessEqual(len(r["results"]), 100)

    def test_pagina_inexistente_404(self):
        self.auth("operador_x")
        self.assertEqual(self.client.get("/api/measurements/?page=99").status_code, 404)
