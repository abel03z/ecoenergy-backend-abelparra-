# EcoEnergy — Fase 1

Aplicación Django del lado del servidor para consultar zonas de consumo energético y sus dispositivos, usando archivos JSON como fuente de datos (sin Models ni base de datos).

## Requisitos

- Python 3.14
- Django 6.1 (ver `requirements.txt`)

## Instalación

```bash
git clone <URL-del-repositorio>
cd ecoenergy-backend-abelparra-
python -m venv .venv
source .venv/bin/activate      # Linux/Mac (bash)
# source .venv/bin/activate.fish   # si usas fish shell
pip install -r requirements.txt
```

## Ejecución

```bash
python manage.py runserver
```

Luego abrir en el navegador: `http://127.0.0.1:8000/`

## Rutas funcionales

| Ruta | Descripción |
|---|---|
| `/` | Página de inicio |
| `/dispositivos/` | Catálogo simple de dispositivos (ejemplo de clase) |
| `/zonas/` | Listado de todas las zonas de consumo |
| `/zonas/<id>/` | Detalle de una zona: dispositivos, categoría, consumo total y estado (NORMAL/ALERTA) |

## Datos

Los datos viven en `data/zonas.json`, `data/categorias.json` y `data/dispositivos.json`. Se leen dinámicamente en cada request desde `dispositivos/data_access.py`, por lo que agregar o modificar registros en los JSON se refleja automáticamente sin tocar código.

## Pruebas realizadas

- Listado de zonas con cantidad de dispositivos correcta.
- Detalle de zona con cálculo dinámico de consumo total y estado (NORMAL/ALERTA).
- Zona sin dispositivos: muestra mensaje y no rompe la app.
- Zona con id inexistente: responde 404 controlado.
- Agregar registros nuevos al JSON: se reflejan sin modificar código.
- `python manage.py check`: sin errores.

## Paquete externo utilizado

- **humanize**: formatea el consumo total con separador de miles para mejorar la legibilidad en la interfaz.
