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

### Clase 5 — Seguridad en Django Admin y scoping por organización

Se implementó scoping por organización en `devices/admin.py` y `monitoring/admin.py` (Dispositivo, Medicion, Alerta y Mantenimiento): cada usuario no-superusuario solo ve y edita datos de su propia organización, resuelta vía `request.user.profile.organizacion` (`core/admin_utils.get_user_organization`). Se aplica con `get_queryset` (filtra el listado), `formfield_for_foreignkey` (limita los selectores de FK) y `has_change_permission`/`has_delete_permission` (bloquea edición/borrado cruzado). También se agregó un `DepartamentoInline` en `OrganizacionAdmin` y la acción personalizada `archive_dispositivos` (borrado lógico vía `deleted_at`).

## Evaluación Sumativa II — Puesta en marcha desde cero

```bash
git clone <URL-del-repositorio>
cd ecoenergy-backend-abelparra-
python -m venv .venv
source .venv/bin/activate           # Linux/Mac (bash)
# source .venv/bin/activate.fish    # fish shell
pip install -r requirements.txt

cp .env.example .env                # deja DB_ENGINE=sqlite para probar sin motor externo

python manage.py migrate
python manage.py seed_ecoenergy     # carga datos de prueba (usar --reset para recargar)
python manage.py runserver
```

Luego entrar a `http://127.0.0.1:8000/admin/`.

### Cuentas de prueba (creadas por `seed_ecoenergy`)

Todas son cuentas de prueba documentadas, no credenciales personales. Contraseña para todas: `Ecoenergy2026*`.

| Usuario | Rol / grupo | Organización | Qué demuestra |
|---|---|---|---|
| `ADMIN` | Superusuario | — | Acceso completo, ve datos de ambas organizaciones |
| `admin_norte` | Administrador organizacional | EcoEnergy Norte | Alta/edición de organización, departamentos, zonas, dispositivos — solo Norte |
| `Operador1` | Operador | EcoEnergy Norte | Ve dispositivos, carga mediciones, gestiona alertas — solo Norte |
| `Operador2` | Operador | EcoEnergy Sur | Mismo rol que Operador1, pero en Sur (para probar que no ve datos de Norte) |
| `consulta_sur` | Consulta | EcoEnergy Sur | Solo lectura sobre dispositivos/mediciones/alertas de Sur |
| `staff_sin_perfil` | Operador (sin `UserProfile`) | — | Caso límite: usuario staff sin organización asignada → `PermissionDenied` al entrar al Admin |

### Datos cargados

2 organizaciones (EcoEnergy Norte, EcoEnergy Sur) con sus propios departamentos, zonas, categorías, dispositivos, mediciones y alertas — suficientes para demostrar que un usuario de una organización no ve ni modifica datos de la otra.

### Clase 8 — Archivos, imágenes y confirmaciones

Se extendió el CRUD protegido de `Dispositivo` (app `devices`) con una imagen opcional y eliminación confirmada con SweetAlert2.

**Qué se agregó**

- `MEDIA_URL = "/media/"` y `MEDIA_ROOT = BASE_DIR / "media"` en `config/settings.py`; `config/urls.py` sirve `MEDIA` solo con `DEBUG=True`. `media/` ya está en `.gitignore`.
- `Dispositivo.image` (`ImageField`, `upload_to="devices/%Y/%m/"`, `blank=True`) + migración `0002_dispositivo_image`. Se agregó `pillow` a `requirements.txt`.
- `DispositivoForm` (`devices/forms.py`) con validación por capas: `accept` en el navegador (solo orienta), tamaño máx. 2 MB, extensión (`.jpg`, `.jpeg`, `.png`) y contenido real con Pillow (`devices/validators.py::validate_real_image`).
- Vistas `DispositivoCreateView`, `DispositivoUpdateView` y `DispositivoDeleteView` (`devices/views.py`), rutas `devices/dispositivos/new|<pk>/edit|<pk>/delete/`.
- El dashboard muestra la miniatura (o "Sin imagen") comprobando `dispositivo.image` antes de usar `.url`.
- `base.html` carga SweetAlert2 y expone `{% block scripts %}`; el botón "Eliminar" abre la confirmación y solo tras confirmar envía el formulario POST (con `csrf_token`). Si la librería no carga, se usa `confirm()`.
- `seed_ecoenergy`: el grupo "Administrador organizacional" ahora también tiene `delete_dispositivo` (sin ese permiso nadie, salvo superusuario, podría eliminar).

**Seguridad en el servidor (SweetAlert2 solo mejora la UX)**

- Eliminar acepta solo `POST` (`GET` responde 405), exige CSRF, login y `devices.delete_dispositivo`.
- Alcance por organización: el queryset filtra `zona__departamento__organizacion` (superusuario: global). Editar o eliminar un `pk` de otra organización responde 404. El selector de zona del formulario solo ofrece zonas de la organización del usuario.

**Política para archivos reemplazados o eliminados**

- Reemplazar o limpiar la imagen: el archivo anterior se borra del storage.
- Eliminar el dispositivo: se borra el registro y también su archivo.
- El borrado físico se hace con `transaction.on_commit`, para no perder el archivo si la transacción falla.
- Editar sin subir un archivo nuevo conserva la imagen actual.
- Si el dispositivo tiene registros protegidos (`PROTECT`), se informa con un mensaje y no se borra nada.
- Decisión asumida: no hay historial/auditoría de imágenes; si el proyecto lo necesitara, habría que conservar los archivos anteriores.

**Pruebas** (`python manage.py test devices`, 14 tests OK)

| Caso | Capa que lo rechaza | Resultado |
|---|---|---|
| PNG válido | — | Se guarda registro y archivo |
| PNG de más de 2 MB | `clean_image` (tamaño) | "La imagen no puede superar 2 MB."; sin registro ni archivo |
| Imagen con extensión `.exe` | `clean_image` (extensión) | "Formato no permitido. Use JPG o PNG."; sin registro ni archivo |
| Texto renombrado `evidencia.jpg` | Pillow (contenido) | "El archivo no es una imagen válida."; sin registro ni archivo |
| Eliminar por GET / sin permiso / sin CSRF / otra organización | Vista | 405 / 403 / 403 / 404; el registro sigue existiendo |
| Reemplazar imagen / eliminar dispositivo | Política | Queda 1 archivo / no queda ninguno |
