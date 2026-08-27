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
