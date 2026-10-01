"""
Comando de carga de datos de prueba para EcoEnergy.

Uso:
    python manage.py seed_ecoenergy            # crea datos (falla si ya existen)
    python manage.py seed_ecoenergy --reset    # borra los datos de prueba anteriores y los vuelve a crear

Crea (más de 1.000 registros de negocio, reproducibles con semilla fija):
- 2 organizaciones (EcoEnergy Norte, EcoEnergy Sur) con sus departamentos, zonas,
  categorías, fabricantes, dispositivos, mediciones, alertas, mantenciones y
  asignaciones, repartidos entre ambas organizaciones para probar scoping,
  permisos y paginación. Incluye algunos registros eliminados lógicamente
  (deleted_at) para verificar que no aparecen en listados ni en el Excel.
- 5 usuarios de prueba con permisos/contextos distintos:
    ADMIN            -> superusuario (acceso completo, sin restricción de organización)
    admin_norte      -> grupo "Administrador organizacional", organización Norte
    Operador1        -> grupo "Operador", organización Norte
    Operador2        -> grupo "Operador", organización Sur
    consulta_sur     -> grupo "Consulta", organización Sur
    staff_sin_perfil -> staff sin UserProfile (caso límite: sin organización asignada)

Contraseña de las cuentas de prueba: NO está escrita en el código ni en el README.
Se toma de la variable de entorno SEED_PASSWORD (debe cumplir la política de
contraseñas) o, si no está definida, se genera una aleatoria y se muestra al final
de la ejecución para entregarla en la demostración.
"""
import os
import random
import secrets
import string
from datetime import timedelta

from django.contrib.auth.models import Group, Permission, User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import UserProfile
from devices.models import Category, Device, DeviceAssignment, Manufacturer
from monitoring.models import Alert, Maintenance, Measurement
from organizations.models import Department, Organization, Zone



def generate_password():
    """Contraseña aleatoria de 16 caracteres que cumple la política (mayús, minús, número, especial)."""
    chars = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%*"),
    ] + [secrets.choice(string.ascii_letters + string.digits) for _ in range(12)]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


GROUP_PERMS = {
    "Administrador organizacional": [
        ("organizations", "organization", ["add", "change", "view"]),
        ("organizations", "department", ["add", "change", "view"]),
        ("organizations", "zone", ["add", "change", "delete", "view"]),
        ("devices", "category", ["add", "change", "delete", "view"]),
        ("devices", "device", ["add", "change", "delete", "view"]),
        ("monitoring", "maintenance", ["add", "change", "delete", "view"]),
    ],
    "Operador": [
        ("devices", "device", ["view"]),
        ("monitoring", "measurement", ["add", "view"]),
        ("monitoring", "alert", ["view", "change"]),
        ("monitoring", "maintenance", ["add", "change", "view"]),
    ],
    "Consulta": [
        ("devices", "device", ["view"]),
        ("monitoring", "measurement", ["view"]),
        ("monitoring", "alert", ["view"]),
        ("monitoring", "maintenance", ["view"]),
    ],
}

SEED = 2026  # semilla fija: misma estructura de datos en cada ejecución

BASE_CATEGORIES = ["Medidor eléctrico", "Sensor de temperatura"]
BASE_MANUFACTURERS = ["Schneider Electric", "Siemens"]
EXTRA_CATEGORIES = [
    "Medidor de agua", "Sensor de humedad", "Panel solar",
    "Inversor", "Luminaria LED", "Bomba de agua",
]
EXTRA_MANUFACTURERS = [
    ("ABB", "Suiza"), ("Legrand", "Francia"), ("Huawei", "China"), ("Bosch", "Alemania"),
]
EXTRA_DEPARTMENTS = ["Mantenimiento", "Sustentabilidad", "Planta 1", "Planta 2"]
ALERT_MESSAGES = {
    "INFO": ["Consumo dentro de lo esperado", "Lectura registrada correctamente", "Dispositivo reconectado"],
    "WARNING": ["Consumo sobre el promedio", "Lectura irregular detectada", "Batería baja del sensor"],
    "CRITICAL": ["Límite de zona superado", "Sin señal del dispositivo", "Sobrecarga detectada"],
}

# Cantidades de la carga masiva (por todas las organizaciones)
BULK_DEVICES_PER_ORG = 75
BULK_MEASUREMENTS = 600
BULK_ALERTS = 200
BULK_MAINTENANCES = 150
BULK_ASSIGNMENTS = 60
SOFT_DELETED_PER_TABLE = 10

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
        self.password_from_env = bool(os.getenv("SEED_PASSWORD"))
        self.password = os.getenv("SEED_PASSWORD") or generate_password()
        try:
            validate_password(self.password)
        except ValidationError as error:
            raise CommandError(
                "SEED_PASSWORD no cumple la política de contraseñas: " + " ".join(error.messages)
            )

        if options["reset"]:
            self._reset()

        with transaction.atomic():
            groups = self._ensure_groups()
            orgs = self._create_orgs()
            self._create_users(groups, orgs)
            self._create_bulk(orgs)

        self._print_summary()
        self.stdout.write(self.style.SUCCESS("Datos de prueba de EcoEnergy cargados correctamente."))
        origin = "definida en SEED_PASSWORD" if self.password_from_env else "generada para esta ejecución"
        self.stdout.write(f"Contraseña de todas las cuentas de prueba ({origin}): {self.password}")

    def _reset(self):
        self.stdout.write("Borrando datos de prueba anteriores...")
        # Los FK usan on_delete=PROTECT, así que hay que borrar de hijos a padres.
        orgs = Organization.all_objects.filter(name__in=["EcoEnergy Norte", "EcoEnergy Sur"])
        departments = Department.all_objects.filter(organization__in=orgs)
        zones = Zone.all_objects.filter(department__in=departments)
        devices = Device.all_objects.filter(zone__in=zones)
        Measurement.all_objects.filter(device__in=devices).delete()
        Alert.all_objects.filter(device__in=devices).delete()
        Maintenance.all_objects.filter(device__in=devices).delete()
        DeviceAssignment.all_objects.filter(device__in=devices).delete()
        User.objects.filter(username__in=TEST_USERNAMES).delete()
        devices.delete()
        Category.all_objects.filter(name__in=BASE_CATEGORIES + EXTRA_CATEGORIES).delete()
        Manufacturer.all_objects.filter(
            name__in=BASE_MANUFACTURERS + [name for name, _ in EXTRA_MANUFACTURERS]
        ).delete()
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
            username="ADMIN",
            defaults={"is_staff": True, "is_superuser": True, "email": "admin@ecoenergy.test"},
        )
        if created:
            admin.set_password(self.password)
            admin.save()
        UserProfile.objects.create(
            user=admin,
            organization=orgs["norte"]["org"],
            department=orgs["norte"]["dept_admin"],
            employee_code="EMP-001",
        )

        admin_norte = User.objects.create_user(
            username="admin_norte", email="admin_norte@ecoenergy.test",
            password=self.password, is_staff=True
        )
        admin_norte.groups.add(groups["Administrador organizacional"])
        UserProfile.objects.create(
            user=admin_norte,
            organization=orgs["norte"]["org"],
            department=orgs["norte"]["dept_admin"],
            employee_code="EMP-002",
        )

        operador1 = User.objects.create_user(
            username="Operador1", email="operador1@ecoenergy.test",
            password=self.password, is_staff=True
        )
        operador1.groups.add(groups["Operador"])
        UserProfile.objects.create(
            user=operador1,
            organization=orgs["norte"]["org"],
            department=orgs["norte"]["dept_ops"],
            employee_code="EMP-003",
        )

        operador2 = User.objects.create_user(
            username="Operador2", email="operador2@ecoenergy.test",
            password=self.password, is_staff=True
        )
        operador2.groups.add(groups["Operador"])
        UserProfile.objects.create(
            user=operador2,
            organization=orgs["sur"]["org"],
            department=orgs["sur"]["dept_ops"],
            employee_code="EMP-004",
        )

        consulta_sur = User.objects.create_user(
            username="consulta_sur", email="consulta_sur@ecoenergy.test",
            password=self.password, is_staff=True
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
            username="staff_sin_perfil", email="staff_sin_perfil@ecoenergy.test",
            password=self.password, is_staff=True
        )
        staff_sin_perfil.groups.add(groups["Operador"])

        # Operación: responsables asignados a dispositivos de su organización.
        DeviceAssignment.objects.create(
            device=orgs["norte"]["device"], user=operador1, notes="Responsable de Norte"
        )
        DeviceAssignment.objects.create(
            device=orgs["sur"]["device"], user=operador2, notes="Responsable de Sur"
        )

    # ------------------------------------------------------------------
    # Carga masiva (más de 1.000 registros de negocio)
    # ------------------------------------------------------------------
    def _create_bulk(self, orgs):
        rng = random.Random(SEED)
        now = timezone.now()
        operators = {
            "norte": User.objects.get(username="Operador1"),
            "sur": User.objects.get(username="Operador2"),
        }

        categories = list(Category.objects.filter(name__in=BASE_CATEGORIES))
        categories += [Category.objects.create(name=name) for name in EXTRA_CATEGORIES]
        manufacturers = list(Manufacturer.objects.filter(name__in=BASE_MANUFACTURERS))
        manufacturers += [
            Manufacturer.objects.create(name=name, country=country)
            for name, country in EXTRA_MANUFACTURERS
        ]

        devices_by_org = {}
        counter = 0
        for key in ("norte", "sur"):
            org = orgs[key]["org"]
            for dept_name in EXTRA_DEPARTMENTS:
                Department.objects.create(organization=org, name=dept_name)
            zones = []
            for dept in Department.objects.filter(organization=org).order_by("pk"):
                for i in (1, 2):
                    zones.append(Zone.objects.create(
                        department=dept,
                        name=f"{dept.name} · Zona {i}",
                        consumption_limit=round(rng.uniform(30, 300), 1),
                    ))

            devices = []
            for _ in range(BULK_DEVICES_PER_ORG):
                counter += 1
                category = rng.choice(categories)
                devices.append(Device(
                    zone=rng.choice(zones),
                    category=category,
                    manufacturer=rng.choice(manufacturers),
                    name=f"{category.name} {counter:03d}",
                    is_active=rng.random() < 0.9,
                ))
            Device.objects.bulk_create(devices, batch_size=500)
            # Dispositivos retirados (eliminados lógicamente y sin registros asociados).
            for n in (1, 2):
                counter += 1
                Device.objects.create(
                    zone=rng.choice(zones),
                    category=rng.choice(categories),
                    manufacturer=rng.choice(manufacturers),
                    name=f"Dispositivo retirado {counter:03d}",
                    is_active=False,
                    deleted_at=now - timedelta(days=rng.randint(1, 30)),
                )
            devices_by_org[key] = list(
                Device.objects.filter(zone__department__organization=org)
                .exclude(name__startswith="Dispositivo retirado")
                .order_by("pk")
            )

        all_devices = [d for key in ("norte", "sur") for d in devices_by_org[key]]
        org_key = {d.pk: key for key in ("norte", "sur") for d in devices_by_org[key]}

        # Mediciones
        measurements = []
        for _ in range(BULK_MEASUREMENTS):
            measurements.append(Measurement(
                device=rng.choice(all_devices),
                consumption_value=round(rng.uniform(0.5, 120), 2),
                measured_at=now - timedelta(minutes=rng.randint(1, 30 * 24 * 60)),
            ))
        self._soft_delete_some(measurements, rng, now)
        Measurement.objects.bulk_create(measurements, batch_size=500)

        # Alertas
        alerts = []
        for _ in range(BULK_ALERTS):
            level = rng.choices(
                [Alert.Level.INFO, Alert.Level.WARNING, Alert.Level.CRITICAL], weights=[5, 3.5, 1.5]
            )[0]
            alerts.append(Alert(
                device=rng.choice(all_devices),
                level=level,
                status=rng.choice(list(Alert.Status)),
                message=rng.choice(ALERT_MESSAGES[level]),
                generated_at=now - timedelta(minutes=rng.randint(1, 30 * 24 * 60)),
            ))
        self._soft_delete_some(alerts, rng, now)
        Alert.objects.bulk_create(alerts, batch_size=500)

        # Mantenciones (coherentes con las reglas del formulario)
        maintenances, used = [], set()
        while len(maintenances) < BULK_MAINTENANCES:
            device = rng.choice(all_devices)
            type_ = rng.choice(list(Maintenance.Type))
            scheduled = (now + timedelta(minutes=rng.randint(-60 * 24 * 60, 45 * 24 * 60))).replace(
                second=0, microsecond=0
            )
            if (device.pk, type_, scheduled) in used:
                continue
            used.add((device.pk, type_, scheduled))
            completed = None
            if scheduled > now:
                status = Maintenance.Status.PENDING
            elif rng.random() < 0.7:
                status = Maintenance.Status.DONE
                completed = min(scheduled + timedelta(hours=rng.randint(1, 72)), now - timedelta(minutes=1))
            else:
                status = Maintenance.Status.IN_PROGRESS
            maintenances.append(Maintenance(
                device=device,
                technician=operators[org_key[device.pk]] if rng.random() < 0.7 else None,
                type=type_,
                status=status,
                scheduled_at=scheduled,
                completed_at=completed,
            ))
        self._soft_delete_some(maintenances, rng, now)
        Maintenance.objects.bulk_create(maintenances, batch_size=500)

        # Asignaciones de responsables (siempre dentro de la misma organización)
        assignments = []
        for _ in range(BULK_ASSIGNMENTS):
            device = rng.choice(all_devices)
            assigned = now - timedelta(days=rng.randint(10, 200))
            released = assigned + timedelta(days=rng.randint(1, 9)) if rng.random() < 0.4 else None
            assignments.append(DeviceAssignment(
                device=device,
                user=operators[org_key[device.pk]],
                assigned_at=assigned,
                released_at=released,
                notes="Asignación de prueba",
            ))
        DeviceAssignment.objects.bulk_create(assignments, batch_size=500)

    @staticmethod
    def _soft_delete_some(objects, rng, now):
        """Marca algunos registros como eliminados lógicamente (no deben verse en listados)."""
        for obj in rng.sample(objects, SOFT_DELETED_PER_TABLE):
            obj.deleted_at = now - timedelta(days=rng.randint(1, 10))

    def _print_summary(self):
        models_ = [
            Organization, Department, Zone, Category, Manufacturer, Device,
            DeviceAssignment, Measurement, Alert, Maintenance,
        ]
        total = 0
        self.stdout.write("Registros cargados (vigentes / eliminados lógicamente):")
        for model in models_:
            alive = model.objects.count()
            deleted = model.all_objects.count() - alive
            total += alive
            self.stdout.write(f"  {model.__name__:<16} {alive:>5} / {deleted}")
        self.stdout.write(self.style.SUCCESS(f"  TOTAL vigentes   {total:>5}"))
