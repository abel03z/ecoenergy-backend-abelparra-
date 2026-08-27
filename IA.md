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
