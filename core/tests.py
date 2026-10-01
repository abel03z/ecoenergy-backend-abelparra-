from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from accounts.models import UserProfile
from devices.models import Category, Device, DeviceAssignment, Manufacturer
from monitoring.models import Alert, Maintenance, Measurement
from organizations.models import Department, Organization, Zone

BUSINESS_MODELS = [
    Organization, Department, Zone, Category, Manufacturer, Device,
    DeviceAssignment, Measurement, Alert, Maintenance,
]


def business_counts():
    return {m.__name__: m.objects.count() for m in BUSINESS_MODELS}


class SeedTests(TestCase):
    """seed_ecoenergy: >= 1.000 registros de negocio, reproducibles y coherentes."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_ecoenergy", stdout=StringIO())

    def test_carga_al_menos_1000_registros_de_negocio_vigentes(self):
        self.assertGreaterEqual(sum(business_counts().values()), 1000)

    def test_cumple_6_maestras_y_4_operacionales(self):
        counts = business_counts()
        for name in ("Organization", "Department", "Zone", "Category", "Manufacturer", "Device"):
            self.assertGreater(counts[name], 0, name)
        for name in ("DeviceAssignment", "Measurement", "Alert", "Maintenance"):
            self.assertGreater(counts[name], 0, name)

    def test_hay_volumen_suficiente_para_paginar(self):
        # más de 30 dispositivos y mantenciones por organización (5/15/30 por página)
        for org in Organization.objects.all():
            self.assertGreater(Device.objects.filter(zone__department__organization=org).count(), 30)
            self.assertGreater(
                Maintenance.objects.filter(device__zone__department__organization=org).count(), 30
            )

    def test_hay_registros_eliminados_logicamente_que_no_se_ven(self):
        self.assertGreater(Maintenance.all_objects.count(), Maintenance.objects.count())
        self.assertGreater(Device.all_objects.count(), Device.objects.count())
        self.assertFalse(Maintenance.objects.filter(deleted_at__isnull=False).exists())

    def test_las_relaciones_son_coherentes_entre_organizaciones(self):
        for assignment in DeviceAssignment.objects.select_related("device__zone__department", "user__profile"):
            self.assertEqual(
                assignment.user.profile.organization_id,
                assignment.device.zone.department.organization_id,
            )
        for m in Maintenance.objects.exclude(technician=None).select_related(
            "technician__profile", "device__zone__department"
        ):
            self.assertEqual(
                m.technician.profile.organization_id, m.device.zone.department.organization_id
            )

    def test_mantenciones_respetan_las_reglas_del_formulario(self):
        for m in Maintenance.objects.all():
            if m.status == Maintenance.Status.DONE:
                self.assertIsNotNone(m.completed_at)
                self.assertGreaterEqual(m.completed_at, m.scheduled_at)
            else:
                self.assertIsNone(m.completed_at)

    def test_es_reproducible_con_reset(self):
        before = business_counts()
        call_command("seed_ecoenergy", "--reset", stdout=StringIO())
        self.assertEqual(business_counts(), before)
        self.assertEqual(UserProfile.objects.count(), 5)


class SeedPasswordTests(TestCase):
    """La contraseña de las cuentas de prueba no está en el código: viene del entorno o se genera."""

    def run_seed(self, **env):
        import os
        from unittest import mock
        out = StringIO()
        with mock.patch.dict(os.environ, env, clear=False):
            if "SEED_PASSWORD" not in env:
                os.environ.pop("SEED_PASSWORD", None)
            call_command("seed_ecoenergy", "--reset", stdout=out)
        return out.getvalue()

    def test_usa_la_contrasena_del_entorno(self):
        from django.contrib.auth.models import User
        output = self.run_seed(SEED_PASSWORD="ClaveDemo#2026x")
        self.assertIn("ClaveDemo#2026x", output)
        self.assertTrue(User.objects.get(username="admin_norte").check_password("ClaveDemo#2026x"))
        self.assertTrue(User.objects.get(username="ADMIN").check_password("ClaveDemo#2026x"))

    def test_sin_variable_genera_una_aleatoria_que_cumple_la_politica(self):
        import re
        from django.contrib.auth.models import User
        from django.contrib.auth.password_validation import validate_password
        output = self.run_seed()
        match = re.search(r"generada para esta ejecución\): (\S+)", output)
        self.assertIsNotNone(match)
        password = match.group(1)
        validate_password(password)  # cumple 10+, mayús, minús, número y especial
        self.assertTrue(User.objects.get(username="Operador1").check_password(password))

    def test_cada_ejecucion_genera_una_contrasena_distinta(self):
        import re
        pattern = r"generada para esta ejecución\): (\S+)"
        first = re.search(pattern, self.run_seed()).group(1)
        second = re.search(pattern, self.run_seed()).group(1)
        self.assertNotEqual(first, second)

    def test_rechaza_una_contrasena_debil_del_entorno(self):
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            self.run_seed(SEED_PASSWORD="123456")

    def test_la_contrasena_no_esta_escrita_en_el_codigo_ni_en_el_readme(self):
        from pathlib import Path
        from django.conf import settings
        for relative in ("core/management/commands/seed_ecoenergy.py", "README.md", ".env.example"):
            self.assertNotIn("Ecoenergy2026", (Path(settings.BASE_DIR) / relative).read_text(encoding="utf-8"))
