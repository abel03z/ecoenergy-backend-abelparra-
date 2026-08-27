import humanize
from django.http import HttpResponse
from django.shortcuts import render


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

from django.http import Http404
from dispositivos.data_access import (
    obtener_zonas,
    obtener_zona_por_id,
    dispositivos_de_zona,
    categoria_por_id,
    calcular_consumo_total,
    calcular_estado,
    resumen_por_zona,
)


def zonas(request):
    lista_zonas = []
    for zona in obtener_zonas():
        disp = dispositivos_de_zona(zona["id"])
        lista_zonas.append({
            "id": zona["id"],
            "nombre": zona["nombre"],
            "limite_kwh": zona["limite_kwh"],
            "cantidad_dispositivos": len(disp),
        })

    return render(request, "dispositivos/zonas.html", {"zonas": lista_zonas})

def zona_detalle(request, zona_id):
    zona = obtener_zona_por_id(zona_id)
    if zona is None:
        raise Http404("La zona solicitada no existe.")

    disp = dispositivos_de_zona(zona_id)
    consumo_total = calcular_consumo_total(disp)
    estado = calcular_estado(consumo_total, zona["limite_kwh"])

    dispositivos_con_categoria = []
    for d in disp:
        categoria = categoria_por_id(d["categoria_id"])
        dispositivos_con_categoria.append({
            "nombre": d["nombre"],
            "categoria": categoria["nombre"] if categoria else "Sin categoría",
            "consumo_kwh": d["consumo_kwh"],
        })

    contexto = {
        "zona": zona,
        "dispositivos": dispositivos_con_categoria,
        "consumo_total": humanize.intcomma(consumo_total),
        "estado": estado,
        "cantidad_dispositivos": len(disp),
    }
    return render(request, "dispositivos/zona_detalle.html", contexto)


def resumen_zonas(request):
    zonas_resumen = resumen_por_zona()

    total_zonas = len(zonas_resumen)
    total_dispositivos = sum(z["cantidad_dispositivos"] for z in zonas_resumen)
    consumo_total_general = sum(z["consumo_total"] for z in zonas_resumen)

    contexto = {
        "zonas": zonas_resumen,
        "total_zonas": total_zonas,
        "total_dispositivos": total_dispositivos,
        "consumo_total_general": humanize.intcomma(consumo_total_general),
    }
    return render(request, "dispositivos/resumen_zonas.html", contexto)
