# EcoEnergy — Fase 1 y 2

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
| `/resumen-zonas/` | Resumen de consumo por zona: totales generales (zonas, dispositivos, consumo) y tabla con dispositivos, consumo, límite y estado (DENTRO DEL LÍMITE/LÍMITE SUPERADO) por zona |

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

## Fase 2 — Resumen de consumo por zona

Se agregó una tercera interfaz, `/resumen-zonas/`, sin reemplazar el listado ni el detalle existentes. La vista (`dispositivos.views.resumen_zonas`) usa `dispositivos/data_access.py` para cargar y relacionar `zonas.json` y `dispositivos.json`, calcular por zona la cantidad de dispositivos, el consumo total y el estado según la regla de negocio, y construir los totales generales (zonas, dispositivos, consumo total). El template solo presenta esos valores, sin lógica de agregación.

**Regla de negocio (nueva, distinta a NORMAL/ALERTA del detalle de zona):**

| Condición | Estado |
|---|---|
| `consumo_total <= limite_kwh` | DENTRO DEL LÍMITE |
| `consumo_total > limite_kwh` | LÍMITE SUPERADO |

Una zona sin dispositivos asociados también aparece en la tabla, con cantidad 0, consumo 0 y estado DENTRO DEL LÍMITE.

### Pruebas realizadas (Fase 2)

- Nuevos registros: agregar zonas/dispositivos válidos en los JSON se refleja sin tocar código ni templates.
- Mayor volumen: al aumentar temporalmente la cantidad de zonas y dispositivos, los totales y la tabla se recalculan correctamente y la navegación sigue accesible.
- Zona sin dispositivos: aparece en la tabla con 0 dispositivos, 0 kWh de consumo y estado DENTRO DEL LÍMITE.
- Colección de zonas vacía: la página permanece operativa y muestra un mensaje ("No hay zonas disponibles").
- Estados: se probaron consumos bajo, igual y sobre el límite; el texto y el color (badge verde/rojo) corresponden a la regla.
- `python manage.py check`: sin errores.



## Unidad 2 — Modelos, identidad y autorización

Junto a la app `dispositivos` (Fase 1/2, basada en JSON), el proyecto incorpora apps Django reales con Models/ORM: `core`, `organizations`, `devices`, `monitoring` y `accounts`.

### Clase 4 — Usuarios, perfiles, grupos y permisos

Se agregó la app `accounts` con el modelo `UserProfile`, que conecta el `User` de Django (autenticación) con el dominio de negocio:

- `UserProfile`: `OneToOneField` a `settings.AUTH_USER_MODEL`, `ForeignKey` a `organizations.Organizacion` y `organizations.Departamento` (opcional), `employee_code` único, `phone`.
- Validación de coherencia (`clean()`): el `departamento` seleccionado debe pertenecer a la `organizacion` del perfil.
- Registrado en Django Admin con búsqueda y filtros por organización/departamento.

**Roles (Groups) y permisos definidos:**

| Grupo | Permisos |
|---|---|
| Administrador organizacional | add/change/view sobre Organizacion, Departamento, Zona, Categoria, Dispositivo |
| Operador | view sobre Dispositivo; add/view sobre Medicion; view/change sobre Alerta |
| Consulta | solo view sobre Dispositivo, Medicion, Alerta |

### Pruebas realizadas (Clase 4)

- Usuario de prueba `Operador1` (`is_staff=True`, sin superuser, grupo `Operador`, sin permisos individuales extra) con su `UserProfile` asociado.
- **Acción permitida:** `Operador1` creó una `Medicion` para un `Dispositivo` existente sin error.
- **Acción denegada:** `Operador1` recibió `403 Forbidden` al intentar acceder directo a `/admin/devices/dispositivo/add/`.
- `python manage.py makemigrations` / `migrate`: sin errores.