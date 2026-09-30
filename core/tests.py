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
