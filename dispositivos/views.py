from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, render

from core.admin_utils import get_user_organization
from devices.models import Device
from organizations.models import Zone


def inicio(request):
    contexto = {
        "sistema": "EcoEnergy",
        "mensaje": "Monitoreo energético responsable",
        "asignatura": "Programacion Back End",
    }
    return render(request, "dispositivos/inicio.html", contexto)


def catalogo(request):
    dispositivos = [
        {"nombre": "Medidor inteligente", "estado": "Activo"},
        {"nombre": "Sensor de temperatura", "estado": "Activo"},
        {"nombre": "Climatizador", "estado": "Revisión"},
    ]
    return render(request, "dispositivos/catalogo.html", {"dispositivos": dispositivos})


# ---------------------------------------------------------------------------
# Zonas y resumen de consumo: datos reales de la base de datos, con scoping por
# organización y sin registros eliminados lógicamente (Zone/Device/Measurement
# .objects ya los excluyen; en los agregados se filtra de forma explícita).
# ---------------------------------------------------------------------------
ESTADO_NORMAL = "DENTRO DEL LÍMITE"
ESTADO_SUPERADO = "LÍMITE SUPERADO"


def _zones_for(request):
    qs = Zone.objects.select_related("department__organization")
    if not request.user.is_superuser:
        qs = qs.filter(department__organization=get_user_organization(request))
    return qs


def _with_stats(queryset):
    """Agrega cantidad de dispositivos y consumo total (suma de mediciones vigentes)."""
    return queryset.annotate(
        device_count=Count(
            "devices", filter=Q(devices__deleted_at__isnull=True), distinct=True
        ),
        total_consumption=Sum(
            "devices__measurements__consumption_value",
            filter=Q(
                devices__deleted_at__isnull=True,
                devices__measurements__deleted_at__isnull=True,
            ),
        ),
    )


def _status(consumption, limit):
    return ESTADO_SUPERADO if consumption > limit else ESTADO_NORMAL


@login_required
def zonas(request):
    zones = _with_stats(_zones_for(request)).order_by("department__organization__name", "name")
    return render(request, "dispositivos/zonas.html", {"zonas": zones})


@login_required
def zona_detalle(request, zona_id):
    zone = get_object_or_404(_with_stats(_zones_for(request)), pk=zona_id)
    consumption = zone.total_consumption or 0

    devices = (
        Device.objects.filter(zone=zone)
        .select_related("category", "manufacturer")
        .annotate(
            total_consumption=Sum(
                "measurements__consumption_value",
                filter=Q(measurements__deleted_at__isnull=True),
            )
        )
        .order_by("name")
    )

    contexto = {
        "zona": zone,
        "dispositivos": devices,
        "consumo_total": consumption,
        "estado": "ALERTA" if consumption > zone.consumption_limit else "NORMAL",
        "cantidad_dispositivos": zone.device_count,
    }
    return render(request, "dispositivos/zona_detalle.html", contexto)


@login_required
def resumen_zonas(request):
    zones = _with_stats(_zones_for(request)).order_by("department__organization__name", "name")
    rows = []
    for zone in zones:
        consumption = zone.total_consumption or 0
        rows.append({
            "zona": zone,
            "cantidad_dispositivos": zone.device_count,
            "consumo_total": consumption,
            "estado": _status(consumption, zone.consumption_limit),
        })

    contexto = {
        "zonas": rows,
        "total_zonas": len(rows),
        "total_dispositivos": sum(r["cantidad_dispositivos"] for r in rows),
        "consumo_total_general": sum(r["consumo_total"] for r in rows),
    }
    return render(request, "dispositivos/resumen_zonas.html", contexto)
