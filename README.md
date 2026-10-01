# EcoEnergy

Aplicación web en Django para monitorear el consumo energético de dos organizaciones: zonas, dispositivos, mediciones, alertas y mantenciones, con autenticación, roles, permisos y datos separados por organización.

Proyecto de **Programación Back End** (INACAP La Serena) · Evaluación Formativa, Unidad II.

## Requisitos

- Python 3.12 o superior (probado con 3.12 y 3.13)
- Los paquetes de `requirements.txt`: Django 6.1, Pillow, openpyxl, humanize y python-dotenv
- No necesita un motor de base de datos externo: por defecto usa SQLite (también se puede usar MySQL, ver más abajo)

## Instalación y puesta en marcha

```bash
git clone <URL-del-repositorio>
cd ecoenergy-backend-abelparra-

python -m venv .venv
source .venv/bin/activate            # Linux/Mac (bash)
# source .venv/bin/activate.fish     # si usas fish
# .venv\Scripts\activate             # Windows
pip install -r requirements.txt

cp .env.example .env                 # variables de entorno (ver tabla más abajo)

python manage.py migrate             # crea las tablas
python manage.py seed_ecoenergy      # carga los datos de prueba (más de 1.000 registros)
python manage.py runserver
```

Luego abrir `http://127.0.0.1:8000/` e ingresar con alguno de los usuarios de prueba.

Para ejecutar las pruebas automáticas:

```bash
python manage.py test
```

## Variables de entorno

Se definen en el archivo `.env` (que **no** se versiona). `.env.example` trae la lista completa con comentarios.

| Variable | Para qué sirve | Valor por defecto |
|---|---|---|
| `SECRET_KEY` | Clave secreta de Django. Generar una propia con `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` | Si está vacía, usa una temporal solo para desarrollo |
| `DEBUG` | Modo desarrollo | `True` |
| `ALLOWED_HOSTS` | Hosts permitidos, separados por coma (obligatorio si `DEBUG=False`) | vacío |
| `SEED_PASSWORD` | Contraseña de las cuentas de prueba que crea el seed | Si está vacía, se genera una aleatoria |
| `DB_ENGINE` | `sqlite` o `mysql` | `sqlite` |
| `DB_NAME` | Archivo SQLite o nombre de la base MySQL | `db.sqlite3` |
| `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Solo si `DB_ENGINE=mysql` (requiere instalar además el driver `mysqlclient`) | — |
| `EMAIL_BACKEND` | Cómo se envía el correo con el código de recuperación | Imprime el correo en la consola del servidor |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL` | Solo si se usa SMTP real | — |
| `PASSWORD_RESET_CODE_TTL` | Segundos de vigencia del código de recuperación | `300` |
| `PASSWORD_RESET_DEMO_MODE` | Solo para demostraciones sin correo: muestra el código en pantalla. Dejar en `False` | `False` |

## Base de datos y migraciones

La conexión se configura solo con variables de entorno (`DB_*`). Las migraciones están versionadas y son reproducibles:

```bash
python manage.py migrate                 # aplica las migraciones
python manage.py makemigrations --check  # verifica que los modelos y las migraciones coinciden
```

## Carga de datos de prueba (seed)

```bash
python manage.py seed_ecoenergy           # carga los datos (falla si ya existen)
python manage.py seed_ecoenergy --reset   # borra los datos de prueba anteriores y los vuelve a cargar
```

El comando usa una semilla fija, así que cada ejecución produce la misma estructura de datos. Carga **1.197 registros de negocio vigentes**, repartidos entre las dos organizaciones para probar relaciones, permisos y paginación:

| Tabla | Registros |
|---|---|
| Organization | 2 |
| Department | 11 |
| Zone | 24 |
| Category | 8 |
| Manufacturer | 6 |
| Device | 154 |
| DeviceAssignment | 62 |
| Measurement | 596 |
| Alert | 192 |
| Maintenance | 142 |

Además crea algunos registros **eliminados lógicamente** (con `deleted_at`) para comprobar que no aparecen en listados, resúmenes ni en el Excel. Al terminar imprime el detalle de lo cargado.

### Contraseña de las cuentas de prueba

La contraseña **no está escrita en el repositorio**. Se obtiene de una de estas dos formas:

- Definiendo `SEED_PASSWORD` en el `.env` antes de correr el seed (debe cumplir la política de contraseñas), o
- Dejándola vacía: el seed genera una aleatoria y la **muestra al final de la ejecución**.

Con `--reset` y sin `SEED_PASSWORD` se genera una contraseña nueva cada vez.

## Usuarios de prueba

Los crea `seed_ecoenergy`. Todos usan la misma contraseña (ver la sección anterior) y un correo `<usuario en minúsculas>@ecoenergy.test`.

| Usuario | Rol | Organización | Qué demuestra |
|---|---|---|---|
| `ADMIN` | Superusuario | — | Acceso completo, ve datos de ambas organizaciones |
| `admin_norte` | Administrador organizacional | EcoEnergy Norte | CRUD completo, solo sobre datos de Norte |
| `Operador1` | Operador | EcoEnergy Norte | Ve dispositivos, crea y edita mantenciones, no elimina |
| `Operador2` | Operador | EcoEnergy Sur | Mismo rol que `Operador1`, pero en Sur (no ve datos de Norte) |
| `consulta_sur` | Consulta | EcoEnergy Sur | Solo lectura sobre datos de Sur |
| `staff_sin_perfil` | Operador sin `UserProfile` | — | Caso límite: sin organización asignada, se le deniega el acceso |

**Permisos por rol**

| Grupo | Permisos |
|---|---|
| Administrador organizacional | add/change/view sobre Organization y Department · add/change/delete/view sobre Zone, Category, Device y Maintenance |
| Operador | view sobre Device · add/view sobre Measurement · view/change sobre Alert · add/change/view sobre Maintenance |
| Consulta | solo view sobre Device, Measurement, Alert y Maintenance |

## Funcionalidades y dónde están

| Funcionalidad | Ruta | Código principal |
|---|---|---|
| Login / logout (sistema de autenticación de Django) | `/accounts/login/` | `config/urls.py`, `templates/registration/` |
| Recuperación de contraseña con código de 6 dígitos | `/accounts/password-reset/` | `accounts/views.py`, `accounts/models.py` |
| Política de contraseña (10+ caracteres, mayúscula, minúscula, número y especial) | — | `accounts/validators.py`, `AUTH_PASSWORD_VALIDATORS` en `config/settings.py` |
| CRUD de dispositivos (con imagen) | `/devices/` | `devices/views.py`, `devices/forms.py`, `devices/validators.py` |
| CRUD de categorías | `/devices/categories/` | `devices/views.py` |
| CRUD de zonas | `/organizations/zones/` | `organizations/views.py`, `organizations/forms.py` |
| CRUD de mantenciones | `/monitoring/maintenances/` | `monitoring/views.py`, `monitoring/forms.py` |
| Exportación a Excel (.xlsx) | `/monitoring/maintenances/export/` | `monitoring/exports.py` |
| Zonas y resumen de consumo (desde la base de datos) | `/zonas/`, `/resumen-zonas/` | `dispositivos/views.py` |
| Django Admin con scoping por organización | `/admin/` | `*/admin.py`, `core/admin_utils.py` |

### Modelo de datos

- **6 tablas maestras:** `Organization`, `Department`, `Zone`, `Category`, `Manufacturer`, `Device`
- **4 tablas operacionales:** `DeviceAssignment`, `Measurement`, `Alert`, `Maintenance`
- **Autenticación:** `UserProfile` (une al usuario con su organización y departamento) y `PasswordResetCode`
- Los nombres de modelos, tablas y campos están en inglés; las relaciones usan `ForeignKey` y `OneToOneField`.

### Estructura del proyecto

| App | Responsabilidad |
|---|---|
| `core` | Modelo base con borrado lógico, paginación, filtros, utilidades de scoping y el comando `seed_ecoenergy` |
| `accounts` | Perfiles de usuario, recuperación de contraseña y validadores |
| `organizations` | Organizaciones, departamentos y zonas |
| `devices` | Categorías, fabricantes y dispositivos |
| `monitoring` | Mediciones, alertas y mantenciones; exportación a Excel |
| `dispositivos` | Página de inicio y vistas de zonas y resumen |

### Decisiones de diseño

- **Borrado lógico:** todas las entidades de negocio heredan de `core.models.BaseModel` y tienen `deleted_at`. El manager `objects` solo devuelve registros vigentes y `all_objects` incluye los eliminados. Eliminar marca `deleted_at`; no hay eliminación física en el flujo normal.
- **Eliminación segura:** solo por `POST` con CSRF, con confirmación de SweetAlert2. El servidor verifica autenticación, permiso y organización antes de ejecutar la acción; la confirmación visual no reemplaza esa validación.
- **Scoping por organización:** los listados, formularios, el Excel y las vistas de zonas y resumen solo muestran datos de la organización del usuario (el superusuario ve todo). Un registro de otra organización responde 404.
- **Paginación:** 5, 15 o 30 registros por página (5 por defecto). La elección se guarda en `request.session` y los valores no permitidos se ignoran.
- **Filtros:** los listados de dispositivos, categorías, zonas y mantenciones se pueden filtrar; los filtros se conservan al paginar y el Excel respeta los filtros activos.
- **Imágenes:** se validan por tamaño (máx. 2 MB), extensión (JPG/PNG) y contenido real con Pillow. Los archivos subidos van a `media/`, que no se versiona.
- **Recuperación de contraseña:** código de 6 dígitos generado con `secrets`, guardado hasheado, con vigencia limitada (`PASSWORD_RESET_CODE_TTL`), máximo 5 intentos fallidos y de un solo uso. Por defecto el correo se imprime en la consola del servidor. Para probarlo: `/accounts/password-reset/` con, por ejemplo, `operador1@ecoenergy.test`, y mirar la terminal donde corre `runserver`.
- **Idioma y tema:** interfaz en español (`es-cl`) con modo claro y oscuro (botón en la barra superior; recuerda la preferencia).

## Pruebas

```bash
python manage.py test
```

La suite cubre autenticación y recuperación de contraseña, política de contraseñas, permisos y scoping de cada CRUD, borrado lógico, validaciones de formularios y de imágenes, paginación con sesión, filtros, exportación a Excel y el seed.

## Flujo de trabajo con Git

Después del primer push, el trabajo se hizo en ramas (`feature/...`, `refactor/...`) integradas a `main` mediante Pull Requests con commits descriptivos. `.env`, `db.sqlite3`, `media/` y los entornos virtuales están en `.gitignore`.

## Documentación adicional

- `ANALISIS.md`: análisis de relaciones y reglas de la Fase 1.
- `IA.md`: declaración del uso de inteligencia artificial en el proyecto.
