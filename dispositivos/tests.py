from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from devices.models import Category, Device, Manufacturer
from monitoring.models import Measurement
from organizations.models import Department, Organization, Zone


class ZoneSummaryTests(TestCase):
    """Zonas y Resumen leen la base de datos (no los JSON) con scoping y soft delete."""

    @classmethod
    def setUpTestData(cls):
        cls.norte = Organization.objects.create(name="Norte")
        cls.sur = Organization.objects.create(name="Sur")
        d_norte = Department.objects.create(organization=cls.norte, name="Ops N")
        d_sur = Department.objects.create(organization=cls.sur, name="Ops S")
        cls.zone_ok = Zone.objects.create(department=d_norte, name="Zona OK", consumption_limit=100)
        cls.zone_over = Zone.objects.create(department=d_norte, name="Zona Excedida", consumption_limit=10)
        cls.zone_sur = Zone.objects.create(department=d_sur, name="Zona Sur", consumption_limit=50)
        category = Category.objects.create(name="Medidor")
        maker = Manufacturer.objects.create(name="Acme")

        def device(name, zone):
            return Device.objects.create(name=name, zone=zone, category=category, manufacturer=maker)

        now = timezone.now()
        cls.dev_a = device("Dev A", cls.zone_ok)
        cls.dev_b = device("Dev B", cls.zone_over)
        cls.dev_c = device("Dev C", cls.zone_over)
        cls.dev_sur = device("Dev Sur", cls.zone_sur)
        cls.dev_gone = device("Dev Borrado", cls.zone_over)
        for dev, value in ((cls.dev_a, 20), (cls.dev_b, 8), (cls.dev_c, 7), (cls.dev_sur, 999), (cls.dev_gone, 500)):
            Measurement.objects.create(device=dev, consumption_value=value, measured_at=now)
        # medición eliminada lógicamente: no debe sumar
        Measurement.objects.create(device=cls.dev_a, consumption_value=1000, measured_at=now).soft_delete()
        cls.dev_gone.soft_delete()

        cls.user = User.objects.create_user("u_norte", password="x")
        UserProfile.objects.create(user=cls.user, organization=cls.norte, employee_code="E1")
        cls.user_sur = User.objects.create_user("u_sur", password="x")
        UserProfile.objects.create(user=cls.user_sur, organization=cls.sur, employee_code="E2")
        cls.root = User.objects.create_superuser("root", password="x")

    def setUp(self):
        self.client.force_login(self.user)

    def test_requieren_login(self):
        self.client.logout()
        for name, args in (("dispositivos:zonas", []), ("dispositivos:resumen_zonas", []),
                           ("dispositivos:zona_detalle", [self.zone_ok.pk])):
            r = self.client.get(reverse(name, args=args))
            self.assertEqual(r.status_code, 302, name)
            self.assertIn("/accounts/login/", r.url)

    def test_zonas_muestra_las_zonas_reales_de_mi_organizacion(self):
        r = self.client.get(reverse("dispositivos:zonas"))
        self.assertContains(r, "Zona OK")
        self.assertContains(r, "Zona Excedida")
        self.assertNotContains(r, "Zona Sur")
        self.assertNotContains(r, "Zona Administrativa")  # dato de los JSON antiguos

    def test_resumen_calcula_desde_la_base_de_datos(self):
        r = self.client.get(reverse("dispositivos:resumen_zonas"))
        self.assertEqual(r.context["total_zonas"], 2)
        # Dev A, Dev B, Dev C (el dispositivo eliminado no cuenta)
        self.assertEqual(r.context["total_dispositivos"], 3)
        # 20 + 8 + 7: sin la medición eliminada, sin el dispositivo eliminado y sin la otra organización
        self.assertEqual(r.context["consumo_total_general"], 35)

    def test_resumen_marca_el_estado_segun_el_limite(self):
        r = self.client.get(reverse("dispositivos:resumen_zonas"))
        estados = {row["zona"].name: row["estado"] for row in r.context["zonas"]}
        self.assertEqual(estados["Zona OK"], "DENTRO DEL LÍMITE")
        self.assertEqual(estados["Zona Excedida"], "LÍMITE SUPERADO")  # 15 > 10
        self.assertContains(r, "LÍMITE SUPERADO")

    def test_resumen_no_menciona_los_json(self):
        self.assertNotContains(self.client.get(reverse("dispositivos:resumen_zonas")), ".json")

    def test_otra_organizacion_ve_solo_lo_suyo(self):
        self.client.force_login(self.user_sur)
        r = self.client.get(reverse("dispositivos:resumen_zonas"))
        self.assertEqual(r.context["total_zonas"], 1)
        self.assertEqual(r.context["consumo_total_general"], 999)

    def test_superusuario_ve_todas_las_organizaciones(self):
        self.client.force_login(self.root)
        r = self.client.get(reverse("dispositivos:resumen_zonas"))
        self.assertEqual(r.context["total_zonas"], 3)

    def test_detalle_de_zona(self):
        r = self.client.get(reverse("dispositivos:zona_detalle", args=[self.zone_over.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["consumo_total"], 15)
        self.assertEqual(r.context["estado"], "ALERTA")
        self.assertEqual(r.context["cantidad_dispositivos"], 2)
        names = [d.name for d in r.context["dispositivos"]]
        self.assertEqual(names, ["Dev B", "Dev C"])
        self.assertNotContains(r, "Dev Borrado")

    def test_detalle_de_zona_de_otra_organizacion_da_404(self):
        r = self.client.get(reverse("dispositivos:zona_detalle", args=[self.zone_sur.pk]))
        self.assertEqual(r.status_code, 404)

    def test_zona_eliminada_logicamente_no_aparece(self):
        self.zone_ok.soft_delete()
        self.assertNotContains(self.client.get(reverse("dispositivos:zonas")), "Zona OK")
        self.assertEqual(
            self.client.get(reverse("dispositivos:zona_detalle", args=[self.zone_ok.pk])).status_code, 404
        )


class ThemeToggleTests(TestCase):
    def test_pagina_incluye_el_boton_de_modo_oscuro(self):
        r = self.client.get(reverse("dispositivos:inicio"))
        self.assertContains(r, 'id="theme-toggle"')
        self.assertContains(r, "data-bs-theme")
