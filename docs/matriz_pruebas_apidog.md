# Matriz de pruebas Apidog — Evaluación sumativa 3 (API RESTful con JWT)

| Campo | Dato |
|---|---|
| Asignatura | Programación Back End (TI3041) · sección vespertina |
| Proyecto | EcoEnergy (`ecoenergy-backend-abelparra-`) |
| Estudiante | Abel Parra |
| Rama / commit | u3-sumativa3-api 
| hash:| fbb20e988f87994dd3d1076f94ddd3ab5271c4ea |
| Fecha de ejecución | 13-10-2026 |
| Entorno | Servidor local `http://127.0.0.1:8000` (`python manage.py runserver`), Apidog de escritorio |
| Datos | `python manage.py seed_ecoenergy --reset` → 2.197 registros de dominio vigentes |
| Colección | `docs/apidog/ecoenergy-sumativa3.postman_collection.json` (54 requests, 7 carpetas) |
| Pruebas automáticas | `python manage.py test` → 176 tests, OK |

Los JWT (`access`/`refresh`) y la contraseña de las cuentas de prueba están ocultos (`<oculto>`). Todos los datos son ficticios.

## 1. Resumen por comprobación de la pauta

| Comprobación | Pruebas | Identidad | Esperado | Observado | Resultado |
|---|---|---|---|---|---|
| Cobertura de modelos (CRUD de 4 principales; GET lista y detalle de 2 operacionales) | Carpetas 4 y 6 | Administrador / operador | 200, 201, 204 según método | 200, 201, 204 según método | Cumple |
| JWT: obtener token y renovar access | #1 a #4 | Administrador | 200 | 200 | Cumple |
| Sin autenticación: GET de recurso protegido | #5 a #10 (los 6 recursos) | Sin token | 401 | 401 | Cumple |
| Solo lectura: GET y POST de una principal | #11 y #12 | Operador | 200 y 403 | 200 y 403 | Cumple |
| Sin rol API: GET de recurso protegido | #15 a #20 (los 6 recursos) | Tercer usuario | 403 | 403 | Cumple |
| CRUD completo: POST, GET detalle, PATCH, DELETE | Carpeta 4 (4 entidades) | Administrador | 201, 200, 200, 204 | 201, 200, 200, 204 | Cumple |
| Errores: dos validaciones e id inexistente | Carpeta 5 | Administrador | 400, 400, 404 | 400, 400, 400, 404 | Cumple |
| Paginación: dos páginas de recurso voluminoso | Carpeta 6 (#53 y #54) | Operador | 200 y resultados distintos | 200 y resultados distintos | Cumple |

## 2. Detalle de las 54 pruebas

`{id}` = id del registro creado en la prueba de creación de la misma entidad (o guardado desde la lista). Estado observado: coincide con el esperado en las 54 pruebas.

| # | Carpeta | Prueba | Método | URL | Identidad | Esperado | Observado | Respuesta representativa |
|---|---|---|---|---|---|---|---|---|
| 1 | 0 Autenticación | Login administrador | POST | `/api/token/` | admin_norte (admin) | 200 | 200 | `{"refresh":"<oculto>","access":"<oculto>"}` |
| 2 | 0 Autenticación | Renovar access (refresh) | POST | `/api/token/refresh/` | admin_norte (admin) | 200 | 200 | `{"access":"<oculto>"}` |
| 3 | 0 Autenticación | Login operador | POST | `/api/token/` | Operador1 (operador) | 200 | 200 | `{"refresh":"<oculto>","access":"<oculto>"}` |
| 4 | 0 Autenticación | Login sin rol API | POST | `/api/token/` | sin_rol_api (sin rol) | 200 | 200 | `{"refresh":"<oculto>","access":"<oculto>"}` |
| 5 | 1 Sin autenticación | GET lista devices sin token | GET | `/api/devices/` | Sin token | 401 | 401 | `{"detail":"Las credenciales de autenticación no se proveyeron."}` |
| 6 | 1 Sin autenticación | GET lista zones sin token | GET | `/api/zones/` | Sin token | 401 | 401 | `{"detail":"Las credenciales de autenticación no se proveyeron."}` |
| 7 | 1 Sin autenticación | GET lista categories sin token | GET | `/api/categories/` | Sin token | 401 | 401 | `{"detail":"Las credenciales de autenticación no se proveyeron."}` |
| 8 | 1 Sin autenticación | GET lista manufacturers sin token | GET | `/api/manufacturers/` | Sin token | 401 | 401 | `{"detail":"Las credenciales de autenticación no se proveyeron."}` |
| 9 | 1 Sin autenticación | GET lista measurements sin token | GET | `/api/measurements/` | Sin token | 401 | 401 | `{"detail":"Las credenciales de autenticación no se proveyeron."}` |
| 10 | 1 Sin autenticación | GET lista alerts sin token | GET | `/api/alerts/` | Sin token | 401 | 401 | `{"detail":"Las credenciales de autenticación no se proveyeron."}` |
| 11 | 2 Roles | Operador consulta categorías | GET | `/api/categories/` | Operador1 (operador) | 200 | 200 | `{"count":8,"next":null,"previous":null,"results":[...]}` |
| 12 | 2 Roles | Operador intenta crear categoría | POST | `/api/categories/` | Operador1 (operador) | 403 | 403 | `{"detail":"Tu rol no permite esta operación."}` |
| 13 | 2 Roles | Operador intenta modificar dispositivo | PATCH | `/api/devices/1/` | Operador1 (operador) | 403 | 403 | `{"detail":"Tu rol no permite esta operación."}` |
| 14 | 2 Roles | Operador intenta eliminar zona | DELETE | `/api/zones/1/` | Operador1 (operador) | 403 | 403 | `{"detail":"Tu rol no permite esta operación."}` |
| 15 | 2 Roles | Sin rol consulta devices | GET | `/api/devices/` | sin_rol_api (sin rol) | 403 | 403 | `{"detail":"Tu rol no permite esta operación."}` |
| 16 | 2 Roles | Sin rol consulta zones | GET | `/api/zones/` | sin_rol_api (sin rol) | 403 | 403 | `{"detail":"Tu rol no permite esta operación."}` |
| 17 | 2 Roles | Sin rol consulta categories | GET | `/api/categories/` | sin_rol_api (sin rol) | 403 | 403 | `{"detail":"Tu rol no permite esta operación."}` |
| 18 | 2 Roles | Sin rol consulta manufacturers | GET | `/api/manufacturers/` | sin_rol_api (sin rol) | 403 | 403 | `{"detail":"Tu rol no permite esta operación."}` |
| 19 | 2 Roles | Sin rol consulta measurements | GET | `/api/measurements/` | sin_rol_api (sin rol) | 403 | 403 | `{"detail":"Tu rol no permite esta operación."}` |
| 20 | 2 Roles | Sin rol consulta alerts | GET | `/api/alerts/` | sin_rol_api (sin rol) | 403 | 403 | `{"detail":"Tu rol no permite esta operación."}` |
| 21 | 3 Ids de referencia | Primera zona (guarda id) | GET | `/api/zones/` | admin_norte (admin) | 200 | 200 | `{"count":13,...,"results":[{"id":177,"name":"Zona Norte 1",...}]}` |
| 22 | 3 Ids de referencia | Primera categoría (guarda id) | GET | `/api/categories/` | admin_norte (admin) | 200 | 200 | `{"count":8,...,"results":[{"id":65,"name":"Medidor eléctrico"},...]}` |
| 23 | 3 Ids de referencia | Primer fabricante (guarda id) | GET | `/api/manufacturers/` | admin_norte (admin) | 200 | 200 | `{"count":6,...,"results":[{"id":51,"name":"Schneider Electric","country":"Francia"},...]}` |
| 24 | 4 CRUD administrador | Category: crear | POST | `/api/categories/` | admin_norte (admin) | 201 | 201 | `{"id":73,"name":"Categoría Apidog"}` |
| 25 | 4 CRUD administrador | Category: detalle | GET | `/api/categories/{id}/` | admin_norte (admin) | 200 | 200 | `{"id":73,"name":"Categoría Apidog"}` |
| 26 | 4 CRUD administrador | Category: actualizar | PATCH | `/api/categories/{id}/` | admin_norte (admin) | 200 | 200 | `{"id":73,"name":"Categoría Apidog editada"}` |
| 27 | 4 CRUD administrador | Category: eliminar (lógico) | DELETE | `/api/categories/{id}/` | admin_norte (admin) | 204 | 204 | (sin cuerpo) |
| 28 | 4 CRUD administrador | Category: detalle tras eliminar | GET | `/api/categories/{id}/` | admin_norte (admin) | 404 | 404 | `{"detail":"No Category matches the given query."}` |
| 29 | 4 CRUD administrador | Manufacturer: crear | POST | `/api/manufacturers/` | admin_norte (admin) | 201 | 201 | `{"id":57,"name":"Fabricante Apidog","country":"Chile"}` |
| 30 | 4 CRUD administrador | Manufacturer: detalle | GET | `/api/manufacturers/{id}/` | admin_norte (admin) | 200 | 200 | `{"id":57,"name":"Fabricante Apidog","country":"Chile"}` |
| 31 | 4 CRUD administrador | Manufacturer: actualizar | PATCH | `/api/manufacturers/{id}/` | admin_norte (admin) | 200 | 200 | `{"id":57,"name":"Fabricante Apidog","country":"Perú"}` |
| 32 | 4 CRUD administrador | Manufacturer: eliminar (lógico) | DELETE | `/api/manufacturers/{id}/` | admin_norte (admin) | 204 | 204 | (sin cuerpo) |
| 33 | 4 CRUD administrador | Manufacturer: detalle tras eliminar | GET | `/api/manufacturers/{id}/` | admin_norte (admin) | 404 | 404 | `{"detail":"No Manufacturer matches the given query."}` |
| 34 | 4 CRUD administrador | Zone: crear | POST | `/api/zones/` | admin_norte (admin) | 201 | 201 | `{"id":201,"name":"Zona Apidog","department":90,"consumption_limit":500.0}` |
| 35 | 4 CRUD administrador | Zone: detalle | GET | `/api/zones/{id}/` | admin_norte (admin) | 200 | 200 | `{"id":201,"name":"Zona Apidog","department":90,"consumption_limit":500.0}` |
| 36 | 4 CRUD administrador | Zone: actualizar | PATCH | `/api/zones/{id}/` | admin_norte (admin) | 200 | 200 | `{"id":201,...,"consumption_limit":750.0}` |
| 37 | 4 CRUD administrador | Zone: eliminar (lógico) | DELETE | `/api/zones/{id}/` | admin_norte (admin) | 204 | 204 | (sin cuerpo) |
| 38 | 4 CRUD administrador | Zone: detalle tras eliminar | GET | `/api/zones/{id}/` | admin_norte (admin) | 404 | 404 | `{"detail":"No Zone matches the given query."}` |
| 39 | 4 CRUD administrador | Device: crear | POST | `/api/devices/` | admin_norte (admin) | 201 | 201 | `{"id":1286,"name":"Sensor Apidog","category":65,"manufacturer":51,"zone":177,"is_active":true,"image":null}` |
| 40 | 4 CRUD administrador | Device: detalle | GET | `/api/devices/{id}/` | admin_norte (admin) | 200 | 200 | `{"id":1286,"name":"Sensor Apidog",...,"is_active":true,"image":null}` |
| 41 | 4 CRUD administrador | Device: actualizar | PATCH | `/api/devices/{id}/` | admin_norte (admin) | 200 | 200 | `{"id":1286,...,"is_active":false,"image":null}` |
| 42 | 4 CRUD administrador | Device: eliminar (lógico) | DELETE | `/api/devices/{id}/` | admin_norte (admin) | 204 | 204 | (sin cuerpo) |
| 43 | 4 CRUD administrador | Device: detalle tras eliminar | GET | `/api/devices/{id}/` | admin_norte (admin) | 404 | 404 | `{"detail":"No Device matches the given query."}` |
| 44 | 5 Errores y validaciones | Validación de campo: nombre muy corto (Device) | POST | `/api/devices/` | admin_norte (admin) | 400 | 400 | `{"name":["Ingrese al menos 3 caracteres."]}` |
| 45 | 5 Errores y validaciones | Validación de campo: límite de consumo 0 (Zone) | POST | `/api/zones/` | admin_norte (admin) | 400 | 400 | `{"consumption_limit":["El límite de consumo debe ser mayor que 0."]}` |
| 46 | 5 Errores y validaciones | Regla de negocio: categoría duplicada | POST | `/api/categories/` | admin_norte (admin) | 400 | 400 | `{"name":["Ya existe una categoría con ese nombre."]}` |
| 47 | 5 Errores y validaciones | Id inexistente | GET | `/api/devices/999999/` | admin_norte (admin) | 404 | 404 | `{"detail":"No Device matches the given query."}` |
| 48 | 6 Operacionales y paginación | Mediciones: lista | GET | `/api/measurements/` | admin_norte (admin) | 200 | 200 | `{"count":790,"next":".../?page=2","results":[{"id":7267,"device":1128,...}]}` |
| 49 | 6 Operacionales y paginación | Mediciones: detalle | GET | `/api/measurements/{id}/` | Operador1 (operador) | 200 | 200 | `{"id":7267,"device":1128,"device_name":"PC","consumption_value":12.5,"measured_at":"2026-10-13T06:00:59Z"}` |
| 50 | 6 Operacionales y paginación | Alertas: lista | GET | `/api/alerts/` | Operador1 (operador) | 200 | 200 | `{"count":107,"next":".../?page=2","results":[{"id":1423,"level":"INFO",...}]}` |
| 51 | 6 Operacionales y paginación | Alertas: detalle | GET | `/api/alerts/{id}/` | Operador1 (operador) | 200 | 200 | `{"id":1423,"device":1129,"level":"INFO","status":"RESOLVED","message":"Consumo normal",...}` |
| 52 | 6 Operacionales y paginación | Escritura sobre operacional (solo lectura) | POST | `/api/measurements/` | admin_norte (admin) | 405 | 405 | `{"detail":"Método \"POST\" no permitido."}` |
| 53 | 6 Operacionales y paginación | Paginación: página 1 | GET | `/api/measurements/?page=1` | Operador1 (operador) | 200 | 200 | `count: 790`, 20 resultados (primer id 7267), `next` → página 2 |
| 54 | 6 Operacionales y paginación | Paginación: página 2 | GET | `/api/measurements/?page=2` | Operador1 (operador) | 200 | 200 | 20 resultados distintos a la página 1 (primer id 8647), con `previous` y `next` |

## 3. Notas

- **Eliminación lógica:** `DELETE` marca `deleted_at` y responde 204 sin cuerpo; el registro deja de figurar en consultas normales (el detalle posterior responde 404). Se explica en el README.
- **Validaciones:** de campo (nombre mínimo de 3 caracteres, límite de consumo mayor que 0) y de regla de negocio (nombre de categoría no repetido; zona/departamento de la organización del usuario; nombre de zona único por departamento).
- **Duplicado:** repetir el POST de una categoría con el mismo nombre devuelve 400, que corresponde a la regla de negocio (no es una falla).
- **Alcance por organización:** las listas muestran solo datos de la organización del usuario (por eso `measurements` cuenta 790 y no el total de la base).
- **Eliminar con dependencias:** una zona, categoría o fabricante con dispositivos asociados responde 409.
- **Tokens:** el `access` dura 30 minutos; si una prueba responde 401 con *Token is expired*, se repite el login.
