"""
Comando de carga de datos de prueba para EcoEnergy.

Uso:
    python manage.py seed_ecoenergy            # crea datos (falla si ya existen)
    python manage.py seed_ecoenergy --reset    # borra los datos de prueba anteriores y los vuelve a crear

Crea:
- 2 organizaciones (EcoEnergy Norte, EcoEnergy Sur) con sus departamentos, zonas,
  categorías, fabricantes, dispositivos, mediciones, alertas y mantenimientos.
- 5 usuarios de prueba con permisos/contextos distintos:
    ADMIN            -> superusuario (acceso completo, sin restricción de organización)
    admin_norte      -> grupo "Administrador organizacional", organización Norte
    Operador1        -> grupo "Operador", organización Norte
    Operador2        -> grupo "Operador", organización Sur
    consulta_sur     -> grupo "Consulta", organización Sur
    staff_sin_perfil -> staff sin UserProfile (caso límite: sin organización asignada)

Todas las contraseñas de las cuentas de prueba son "Ecoenergy2026*" (cuentas de
prueba documentadas en el README, no son credenciales personales).
"""
from datetime import timedelta

from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import UserProfile
from devices.models import Category, Device, DeviceAssignment, Manufacturer
from monitoring.models import Alert, Maintenance, Measurement
from organizations.models import Department, Organization, Zone

TEST_PASSWORD = "Ecoenergy2026*"

GROUP_PERMS = {
    "Administrador organizacional": [
        ("organizations", "organization", ["add", "change", "view"]),
        ("organizations", "department", ["add", "change", "view"]),
        ("organizations", "zone", ["add", "change", "view"]),
        ("devices", "category", ["add", "change", "view"]),
        ("devices", "device", ["add", "change", "delete", "view"]),
    ],
    "Operador": [
        ("devices", "device", ["view"]),
        ("monitoring", "measurement", ["add", "view"]),
        ("monitoring", "alert", ["view", "change"]),
    ],
    "Consulta": [
        ("devices", "device", ["view"]),
        ("monitoring", "measurement", ["view"]),
        ("monitoring", "alert", ["view"]),
    ],
}

TEST_USERNAMES = [
    "ADMIN",
    "admin_norte",
    "Operador1",
    "Operador2",
    "consulta_sur",
    "staff_sin_perfil",
]


class Command(BaseCommand):
    help = "Carga datos de prueba reproducibles para EcoEnergy (2 organizaciones, usuarios con roles distintos, dispositivos, mediciones y alertas)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Borra los datos de prueba anteriores (organizaciones, dispositivos, usuarios de prueba) antes de recrearlos.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()

        with transaction.atomic():
            groups = self._ensure_groups()
            orgs = self._create_orgs()
            self._create_users(groups, orgs)

        self.stdout.write(self.style.SUCCESS("Datos de prueba de EcoEnergy cargados correctamente."))
        self.stdout.write(f"Contraseña de todas las cuentas de prueba: {TEST_PASSWORD}")

    def _reset(self):
        self.stdout.write("Borrando datos de prueba anteriores...")
        # Los FK usan on_delete=PROTECT, así que hay que borrar de hijos a padres.
        orgs = Organization.objects.filter(name__in=["EcoEnergy Norte", "EcoEnergy Sur"])
        departments = Department.objects.filter(organization__in=orgs)
        zones = Zone.objects.filter(department__in=departments)
        devices = Device.objects.filter(zone__in=zones)
        Measurement.objects.filter(device__in=devices).delete()
        Alert.objects.filter(device__in=devices).delete()
        Maintenance.objects.filter(device__in=devices).delete()
        DeviceAssignment.objects.filter(device__in=devices).delete()
        User.objects.filter(username__in=TEST_USERNAMES).delete()
        devices.delete()
        Category.objects.filter(name__in=["Medidor eléctrico", "Sensor de temperatura"]).delete()
        Manufacturer.objects.filter(name__in=["Schneider Electric", "Siemens"]).delete()
        zones.delete()
        departments.delete()
        orgs.delete()

    def _ensure_groups(self):
        groups = {}
        for name, perms in GROUP_PERMS.items():
            group, _ = Group.objects.get_or_create(name=name)
            group.permissions.clear()
            for app_label, model_name, actions in perms:
                for action in actions:
                    codename = f"{action}_{model_name}"
                    try:
                        perm = Permission.objects.get(
                            content_type__app_label=app_label, codename=codename
                        )
                        group.permissions.add(perm)
                    except Permission.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f"Permiso no encontrado: {app_label}.{codename}")
                        )
            groups[name] = group
        return groups

    def _create_orgs(self):
        data = {}

        norte = Organization.objects.create(name="EcoEnergy Norte")
        dept_ops_norte = Department.objects.create(organization=norte, name="Operaciones")
        dept_admin_norte = Department.objects.create(organization=norte, name="Administración")
        zone_norte = Zone.objects.create(
            department=dept_ops_norte, name="Zona Norte 1", consumption_limit=40.0
        )

        sur = Organization.objects.create(name="EcoEnergy Sur")
        dept_ops_sur = Department.objects.create(organization=sur, name="Operaciones Sur")
        zone_sur = Zone.objects.create(
            department=dept_ops_sur, name="Zona Sur 1", consumption_limit=150.0
        )

        cat_meter, _ = Category.objects.get_or_create(name="Medidor eléctrico")
        cat_sensor, _ = Category.objects.get_or_create(name="Sensor de temperatura")
        maker_a, _ = Manufacturer.objects.get_or_create(name="Schneider Electric", defaults={"country": "Francia"})
        maker_b, _ = Manufacturer.objects.get_or_create(name="Siemens", defaults={"country": "Alemania"})

        dev_pc = Device.objects.create(zone=zone_norte, category=cat_meter, manufacturer=maker_a, name="PC")
        dev_sensor_norte = Device.objects.create(zone=zone_norte, category=cat_sensor, manufacturer=maker_b, name="Sensor Sala Norte")
        dev_sensor_sur = Device.objects.create(zone=zone_sur, category=cat_meter, manufacturer=maker_a, name="Sensor sur")
        dev_compressor_sur = Device.objects.create(zone=zone_sur, category=cat_sensor, manufacturer=maker_b, name="Compresor Sur")

        now = timezone.now()
        for device, values in [
            (dev_pc, [12.5, 15.2]),
            (dev_sensor_norte, [8.0]),
            (dev_sensor_sur, [90.0, 160.0]),
            (dev_compressor_sur, [45.3]),
        ]:
            for i, value in enumerate(values):
                Measurement.objects.create(
                    device=device,
                    consumption_value=value,
                    measured_at=now - timedelta(hours=i),
                )

        Alert.objects.create(
            device=dev_sensor_norte, level=Alert.Level.INFO,
            status=Alert.Status.RESOLVED, message="Consumo normal", generated_at=now,
        )
        Alert.objects.create(
            device=dev_sensor_sur, level=Alert.Level.CRITICAL,
            status=Alert.Status.OPEN, message="Límite de zona superado", generated_at=now,
        )

        Maintenance.objects.create(
            device=dev_pc, type=Maintenance.Type.PREVENTIVE,
            status=Maintenance.Status.PENDING, scheduled_at=now + timedelta(days=7),
        )
        Maintenance.objects.create(
            device=dev_compressor_sur, type=Maintenance.Type.CORRECTIVE,
            status=Maintenance.Status.PENDING, scheduled_at=now + timedelta(days=2),
        )

        data["norte"] = {"org": norte, "dept_ops": dept_ops_norte, "dept_admin": dept_admin_norte, "device": dev_pc}
        data["sur"] = {"org": sur, "dept_ops": dept_ops_sur, "device": dev_sensor_sur}
        return data

    def _create_users(self, groups, orgs):
        admin, created = User.objects.get_or_create(
            username="ADMIN", defaults={"is_staff": True, "is_superuser": True}
        )
        if created:
            admin.set_password(TEST_PASSWORD)
            admin.save()
        UserProfile.objects.create(
            user=admin,
            organization=orgs["norte"]["org"],
            department=orgs["norte"]["dept_admin"],
            employee_code="EMP-001",
        )

        admin_norte = User.objects.create_user(
            username="admin_norte", password=TEST_PASSWORD, is_staff=True
        )
        admin_norte.groups.add(groups["Administrador organizacional"])
        UserProfile.objects.create(
            user=admin_norte,
            organization=orgs["norte"]["org"],
            department=orgs["norte"]["dept_admin"],
            employee_code="EMP-002",
        )

        operador1 = User.objects.create_user(
            username="Operador1", password=TEST_PASSWORD, is_staff=True
        )
        operador1.groups.add(groups["Operador"])
        UserProfile.objects.create(
            user=operador1,
            organization=orgs["norte"]["org"],
            department=orgs["norte"]["dept_ops"],
            employee_code="EMP-003",
        )

        operador2 = User.objects.create_user(
            username="Operador2", password=TEST_PASSWORD, is_staff=True
        )
        operador2.groups.add(groups["Operador"])
        UserProfile.objects.create(
            user=operador2,
            organization=orgs["sur"]["org"],
            department=orgs["sur"]["dept_ops"],
            employee_code="EMP-004",
        )

        consulta_sur = User.objects.create_user(
            username="consulta_sur", password=TEST_PASSWORD, is_staff=True
        )
        consulta_sur.groups.add(groups["Consulta"])
        UserProfile.objects.create(
            user=consulta_sur,
            organization=orgs["sur"]["org"],
            department=orgs["sur"]["dept_ops"],
            employee_code="EMP-005",
        )

        # Caso límite: staff sin UserProfile (sin organización asignada).
        staff_sin_perfil = User.objects.create_user(
            username="staff_sin_perfil", password=TEST_PASSWORD, is_staff=True
        )
        staff_sin_perfil.groups.add(groups["Operador"])

        # Operación: responsables asignados a dispositivos de su organización.
        DeviceAssignment.objects.create(
            device=orgs["norte"]["device"], user=operador1, notes="Responsable de Norte"
        )
        DeviceAssignment.objects.create(
            device=orgs["sur"]["device"], user=operador2, notes="Responsable de Sur"
        )
