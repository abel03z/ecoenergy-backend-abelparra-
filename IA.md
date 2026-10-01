# IA.md — Uso de Inteligencia Artificial

**Herramienta utilizada:** Claude (Anthropic), vía chat.

**Prompts / apoyo solicitado:**
- Explicación del enunciado de la Fase 1 y priorización de tareas.
- Estructura sugerida para `dispositivos/data_access.py` (funciones de carga y relación de JSON).
- Estructura sugerida para las vistas `zonas` y `zona_detalle`.
- Plantilla base de los templates Bootstrap (`zonas.html`, `zona_detalle.html`, `base.html`).
- Ayuda para depurar errores de consola (activación de entorno virtual en fish shell, JSONDecodeError por JSON mal formado, orden de línea en `views.py` al integrar `humanize`).

**Cambios propios / verificación:**
- Se escribieron y probaron manualmente los 3 archivos JSON de datos (zonas, categorías, dispositivos), incluyendo valores elegidos a propósito para cubrir los casos NORMAL y ALERTA.
- Se probó cada vista en el navegador con `runserver` antes de continuar al siguiente paso.
- Se verificó el comportamiento con `python manage.py shell` antes de integrar la lógica en las vistas.
- Se corrigieron manualmente errores propios al copiar código (por ejemplo, línea faltante al integrar `humanize`, JSON duplicado al agregar una zona nueva).
- Se ejecutó `python manage.py check` en cada etapa para confirmar que el proyecto seguía funcionando.

Todo el código fue revisado, ejecutado y comprendido antes de continuar a la siguiente etapa.

---

## Evaluación Formativa Unidad II (Django con base de datos, seguridad y CRUD)

**Herramienta utilizada:** Claude (Anthropic), vía chat.

**Apoyo solicitado:**
- Revisión del enunciado y de la rúbrica, y comparación contra el estado del repositorio para ordenar el trabajo pendiente.
- Propuesta de código para: renombrar los modelos a inglés y completar las tablas maestras y operacionales, borrado lógico, paginación 5/15/30 en sesión, CRUD de Zone y Maintenance, política de contraseña y recuperación con código de 6 dígitos, seed de más de 1.000 registros, exportación a Excel con openpyxl, filtros en los listados, modo oscuro y el README.
- Ayuda para interpretar errores de consola (por ejemplo, migraciones antiguas que quedaron en el proyecto y un `ProtectedError` al usar `seed_ecoenergy --reset` con un usuario creado a mano).

**Trabajo propio y verificación:**
- Apliqué cada cambio en una rama propia, ejecuté `migrate`, el seed y `python manage.py test` en cada paso, revisé el `git status` antes de commitear y fusioné con Pull Requests.
- Probé las pantallas en el navegador con distintos usuarios y detecté problemas que se corrigieron después: la columna «Acciones» vacía para usuarios sin permisos, y las páginas de Zonas y Resumen que seguían usando los JSON de la Fase 1 en vez de la base de datos.
- Pedí agregar los filtros en los listados y el modo oscuro.

*(Completar o ajustar este texto según lo que efectivamente hizo cada integrante.)*

