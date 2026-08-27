# ANALISIS.md — EcoEnergy Fase 1

## 1. Relaciones y multiplicidades

- **Zona (1) — Dispositivo (0..*)**: una zona puede tener cero o muchos dispositivos; cada dispositivo pertenece a exactamente una zona (`zona_id`).
- **Categoria (1) — Dispositivo (0..*)**: una categoría puede clasificar cero o muchos dispositivos; cada dispositivo pertenece a exactamente una categoría (`categoria_id`).

## 2. Claves de conexión

| Archivo | Clave primaria | Claves foráneas |
|---|---|---|
| `zonas.json` | `id` | — |
| `categorias.json` | `id` | — |
| `dispositivos.json` | `id` | `zona_id` → `zonas.id`, `categoria_id` → `categorias.id` |

La relación se resuelve en Python en `dispositivos/data_access.py`, filtrando y buscando por estas claves (no hay ORM ni claves foráneas de base de datos).

## 3. Matriz Criterio de aceptación | Archivo/Componente | Prueba

| Criterio | Archivo/Componente | Prueba realizada |
|---|---|---|
| CA-01 | `views.zonas`, `zonas.html` | Se listan las 4 zonas de `zonas.json` |
| CA-02 | `views.zonas`, `zonas.html` | Cada card muestra nombre, límite, cantidad de dispositivos y botón "Ver detalle" |
| CA-03 | `views.zona_detalle`, `zona_detalle.html` | Detalle muestra dispositivos, categoría, consumo y estado |
| CA-04 | `data_access.py`, `views.zona_detalle` | Consumo total y estado se calculan en Python, no están escritos en el HTML |
| CA-05 | `data_access.calcular_estado` | Zona Producción (1380 > 1200) → ALERTA; Zona Administrativa (310 ≤ 500) → NORMAL |
| CA-06 | `data_access.py` (lectura de JSON en cada request) | Se agregó "Zona Exterior" al JSON y apareció sin modificar código |
| CA-07 | `zona_detalle.html` (bloque `{% else %}`) | Zona Exterior sin dispositivos muestra mensaje y no rompe la app |
| CA-08 | `views.zona_detalle` (`raise Http404`) | `/zonas/99/` responde 404 controlado |
| CA-09 | `base.html` (herencia y navegación) | Estructura y navegación se mantienen al aumentar zonas |
| CA-10 | `zona_detalle.html` (`table-responsive`) | Tabla permite scroll horizontal sin desbordar la página |
| CA-11 | `base.html`, Bootstrap | Header, navegación, cards, tablas y botones con jerarquía visual coherente |
| CA-12 | `zona_detalle.html` (badges con texto + ícono) | Estado usa texto ("NORMAL"/"ALERTA") + color + ícono, no solo color |
| CA-13 | Proyecto completo | `python manage.py check` sin errores |

## 4. Decisiones de diseño

- Se separó el acceso a datos (`data_access.py`) de las vistas para mantener responsabilidades claras (MVT) y que las vistas solo orquesten datos ya procesados.
- Los cálculos (consumo total, estado) se hacen siempre en la vista/módulo de datos, nunca en el template, cumpliendo CA-04.
