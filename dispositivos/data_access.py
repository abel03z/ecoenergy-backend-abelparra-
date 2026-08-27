import json
from pathlib import Path
from django.conf import settings

DATA_DIR = Path(settings.BASE_DIR) / "data"


def _cargar_json(nombre_archivo):
    ruta = DATA_DIR / nombre_archivo
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def obtener_zonas():
    return _cargar_json("zonas.json")


def obtener_categorias():
    return _cargar_json("categorias.json")


def obtener_dispositivos():
    return _cargar_json("dispositivos.json")


def obtener_zona_por_id(zona_id):
    for zona in obtener_zonas():
        if zona["id"] == zona_id:
            return zona
    return None


def dispositivos_de_zona(zona_id):
    return [d for d in obtener_dispositivos() if d["zona_id"] == zona_id]


def categoria_por_id(categoria_id):
    for c in obtener_categorias():
        if c["id"] == categoria_id:
            return c
    return None


def calcular_consumo_total(dispositivos):
    return sum(d["consumo_kwh"] for d in dispositivos)


def calcular_estado(consumo_total, limite_kwh):
    return "ALERTA" if consumo_total > limite_kwh else "NORMAL"


def calcular_estado_limite(consumo_total, limite_kwh):
    """Regla de negocio de la Fase 2 (sección 3.3): distinta a calcular_estado,
    que se usa en el detalle de zona con las etiquetas NORMAL/ALERTA."""
    return "LÍMITE SUPERADO" if consumo_total > limite_kwh else "DENTRO DEL LÍMITE"


def resumen_por_zona():
    """Arma, para cada zona, cantidad de dispositivos, consumo total,
    límite y estado. Una zona sin dispositivos igual aparece con
    cantidad 0, consumo 0 y estado DENTRO DEL LÍMITE."""
    resumen = []
    for zona in obtener_zonas():
        disp = dispositivos_de_zona(zona["id"])
        consumo_total = calcular_consumo_total(disp)
        resumen.append({
            "id": zona["id"],
            "nombre": zona["nombre"],
            "cantidad_dispositivos": len(disp),
            "consumo_total": consumo_total,
            "limite_kwh": zona["limite_kwh"],
            "estado": calcular_estado_limite(consumo_total, zona["limite_kwh"]),
        })
    return resumen
