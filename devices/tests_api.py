from rest_framework.test import APITestCase

from devices.models import Category, Device, Manufacturer
from organizations.models import Department, Organization, Zone


class DeviceApiTests(APITestCase):
    """Secuencia de la Clase 1: lista, crear, detalle, PATCH, 400, DELETE y 404."""

    @classmethod
    def setUpTestData(cls):
        org = Organization.objects.create(name="Org Test")
        dep = Department.objects.create(organization=org, name="Dep")
        cls.zone = Zone.objects.create(department=dep, name="Zona 1", consumption_limit=100)
        cls.category = Category.objects.create(name="Sensores")
        cls.manufacturer = Manufacturer.objects.create(name="Fab")

    def payload(self, **extra):
        data = {
            "name": "Sensor Patio",
            "category": self.category.pk,
            "manufacturer": self.manufacturer.pk,
            "zone": self.zone.pk,
            "is_active": True,
        }
        data.update(extra)
        return data

    def test_secuencia_crud(self):
        # 1. GET lista -> 200
        r = self.client.get("/api/devices/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [])

        # 2. POST válido -> 201
        r = self.client.post("/api/devices/", self.payload(), format="json")
        self.assertEqual(r.status_code, 201, r.content)
        pk = r.json()["id"]
        self.assertNotIn("deleted_at", r.json())

        # 3. GET detalle + PATCH parcial -> 200
        self.assertEqual(self.client.get(f"/api/devices/{pk}/").status_code, 200)
        r = self.client.patch(f"/api/devices/{pk}/", {"name": "Sensor Sala"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["name"], "Sensor Sala")

        # 4. POST inválido -> 400
        r = self.client.post("/api/devices/", self.payload(name="ab", zone=9999), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("name", r.json())
        self.assertIn("zone", r.json())

        # 5. DELETE -> 204 y luego 404
        self.assertEqual(self.client.delete(f"/api/devices/{pk}/").status_code, 204)
        self.assertEqual(self.client.get(f"/api/devices/{pk}/").status_code, 404)

    def test_delete_es_borrado_logico(self):
        d = Device.objects.create(
            name="Sensor X", zone=self.zone, category=self.category, manufacturer=self.manufacturer
        )
        self.client.delete(f"/api/devices/{d.pk}/")
        self.assertTrue(Device.all_objects.get(pk=d.pk).is_deleted)

    def test_id_no_lo_fija_el_cliente(self):
        r = self.client.post("/api/devices/", self.payload(id=500), format="json")
        self.assertEqual(r.status_code, 201)
        self.assertNotEqual(r.json()["id"], 500)

    def test_imagen_invalida_400(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        fake = SimpleUploadedFile("x.png", b"no soy una imagen", content_type="image/png")
        r = self.client.post("/api/devices/", self.payload(image=fake), format="multipart")
        self.assertEqual(r.status_code, 400)
        self.assertIn("image", r.json())
