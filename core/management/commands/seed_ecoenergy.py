"""
Comando de carga de datos de prueba para EcoEnergy.

Uso:
    python manage.py seed_ecoenergy            # crea datos (falla si ya existen)
    python manage.py seed_ecoenergy --reset    # borra los datos de prueba anteriores y los vuelve a crear

Crea:
- 2 organizaciones (EcoEnergy Norte, EcoEnergy Sur) con sus departamentos, zonas,
  categorías, dispositivos, mediciones, alertas y mantenimientos.
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
from devices.models import Categoria, Dispositivo
from monitoring.models import Alerta, Medicion, Mantenimiento
from organizations.models import Departamento, Organizacion, Zona

TEST_PASSWORD = "Ecoenergy2026*"

GROUP_PERMS = {
    "Administrador organizacional": [
        ("organizations", "organizacion", ["add", "change", "view"]),
        ("organizations", "departamento", ["add", "change", "view"]),
        ("organizations", "zona", ["add", "change", "view"]),
        ("devices", "categoria", ["add", "change", "view"]),
        ("devices", "dispositivo", ["add", "change", "view"]),
    ],
    "Operador": [
        ("devices", "dispositivo", ["view"]),
        ("monitoring", "medicion", ["add", "view"]),
        ("monitoring", "alerta", ["view", "change"]),
    ],
    "Consulta": [
        ("devices", "dispositivo", ["view"]),
        ("monitoring", "medicion", ["view"]),
        ("monitoring", "alerta", ["view"]),
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
        User.objects.filter(username__in=TEST_USERNAMES).delete()
        orgs = Organizacion.objects.filter(nombre__in=["EcoEnergy Norte", "EcoEnergy Sur"])
        deptos = Departamento.objects.filter(organizacion__in=orgs)
        zonas = Zona.objects.filter(departamento__in=deptos)
        dispositivos = Dispositivo.objects.filter(zona__in=zonas)
        Medicion.objects.filter(dispositivo__in=dispositivos).delete()
        Alerta.objects.filter(dispositivo__in=dispositivos).delete()
        Mantenimiento.objects.filter(dispositivo__in=dispositivos).delete()
        dispositivos.delete()
        Categoria.objects.filter(nombre__in=["Medidor eléctrico", "Sensor de temperatura"]).delete()
        zonas.delete()
        deptos.delete()
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

        norte = Organizacion.objects.create(nombre="EcoEnergy Norte")
        depto_ops_norte = Departamento.objects.create(organizacion=norte, nombre="Operaciones")
        depto_admin_norte = Departamento.objects.create(organizacion=norte, nombre="Administración")
        zona_norte = Zona.objects.create(
            departamento=depto_ops_norte, nombre="Zona Norte 1", limite_consumo=40.0
        )

        sur = Organizacion.objects.create(nombre="EcoEnergy Sur")
        depto_ops_sur = Departamento.objects.create(organizacion=sur, nombre="Operaciones Sur")
        zona_sur = Zona.objects.create(
            departamento=depto_ops_sur, nombre="Zona Sur 1", limite_consumo=150.0
        )

        cat_medidor, _ = Categoria.objects.get_or_create(nombre="Medidor eléctrico")
        cat_sensor, _ = Categoria.objects.get_or_create(nombre="Sensor de temperatura")

        disp_pc = Dispositivo.objects.create(
            zona=zona_norte, categoria=cat_medidor, nombre="PC"
        )
        disp_sensor_norte = Dispositivo.objects.create(
            zona=zona_norte, categoria=cat_sensor, nombre="Sensor Sala Norte"
        )
        disp_sensor_sur = Dispositivo.objects.create(
            zona=zona_sur, categoria=cat_medidor, nombre="Sensor sur"
        )
        disp_compresor_sur = Dispositivo.objects.create(
            zona=zona_sur, categoria=cat_sensor, nombre="Compresor Sur"
        )

        ahora = timezone.now()
        for disp, valores in [
            (disp_pc, [12.5, 15.2]),
            (disp_sensor_norte, [8.0]),
            (disp_sensor_sur, [90.0, 160.0]),
            (disp_compresor_sur, [45.3]),
        ]:
            for i, valor in enumerate(valores):
                Medicion.objects.create(
                    dispositivo=disp,
                    valor_consumo=valor,
                    fecha_hora=ahora - timedelta(hours=i),
                )

        Alerta.objects.create(
            dispositivo=disp_sensor_norte, estado="NORMAL", fecha_generada=ahora
        )
        Alerta.objects.create(
            dispositivo=disp_sensor_sur, estado="ALERTA", fecha_generada=ahora
        )

        Mantenimiento.objects.create(
            dispositivo=disp_pc,
            tipo="Preventivo",
            estado="PENDIENTE",
            fecha_programada=ahora + timedelta(days=7),
        )
        Mantenimiento.objects.create(
            dispositivo=disp_compresor_sur,
            tipo="Correctivo",
            estado="PENDIENTE",
            fecha_programada=ahora + timedelta(days=2),
        )

        data["norte"] = {"org": norte, "depto_ops": depto_ops_norte, "depto_admin": depto_admin_norte}
        data["sur"] = {"org": sur, "depto_ops": depto_ops_sur}
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
            organizacion=orgs["norte"]["org"],
            departamento=orgs["norte"]["depto_admin"],
            employee_code="EMP-001",
        )

        admin_norte = User.objects.create_user(
            username="admin_norte", password=TEST_PASSWORD, is_staff=True
        )
        admin_norte.groups.add(groups["Administrador organizacional"])
        UserProfile.objects.create(
            user=admin_norte,
            organizacion=orgs["norte"]["org"],
            departamento=orgs["norte"]["depto_admin"],
            employee_code="EMP-002",
        )

        operador1 = User.objects.create_user(
            username="Operador1", password=TEST_PASSWORD, is_staff=True
        )
        operador1.groups.add(groups["Operador"])
        UserProfile.objects.create(
            user=operador1,
            organizacion=orgs["norte"]["org"],
            departamento=orgs["norte"]["depto_ops"],
            employee_code="EMP-003",
        )

        operador2 = User.objects.create_user(
            username="Operador2", password=TEST_PASSWORD, is_staff=True
        )
        operador2.groups.add(groups["Operador"])
        UserProfile.objects.create(
            user=operador2,
            organizacion=orgs["sur"]["org"],
            departamento=orgs["sur"]["depto_ops"],
            employee_code="EMP-004",
        )

        consulta_sur = User.objects.create_user(
            username="consulta_sur", password=TEST_PASSWORD, is_staff=True
        )
        consulta_sur.groups.add(groups["Consulta"])
        UserProfile.objects.create(
            user=consulta_sur,
            organizacion=orgs["sur"]["org"],
            departamento=orgs["sur"]["depto_ops"],
            employee_code="EMP-005",
        )

        # Caso límite: staff sin UserProfile (sin organización asignada).
        staff_sin_perfil = User.objects.create_user(
            username="staff_sin_perfil", password=TEST_PASSWORD, is_staff=True
        )
        staff_sin_perfil.groups.add(groups["Operador"])
