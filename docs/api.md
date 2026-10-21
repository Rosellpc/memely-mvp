# API

Todas las respuestas de error incluyen `error` y `message`. Todas las escrituras
requieren `X-Memely-Client: web`; POST y PATCH también Content-Type application/json.
No enviar contraseñas ni cookies a repositorios ni a logs. Todas las rutas salvo
registro/login/logout y health requieren sesión. Registro inicia sesión automáticamente.

| Método | Ruta | Función |
| --- | --- | --- |
| POST | /api/usuarios | nombre, email, password (15–128 caracteres) |
| POST | /api/login | email, password |
| POST | /api/logout | objeto JSON vacío; elimina cookie |
| GET | /api/me | usuario autenticado, sin hash |
| GET / POST | /api/profile | consultar / guardar perfil |
| GET / POST | /api/measurements | historial paginado / agregar medida |
| DELETE | /api/measurements/{id} | eliminar medición propia |
| GET / POST | /api/plans | historial paginado / crear plan |
| GET | /api/plans/latest | último plan o null |
| GET / DELETE | /api/plans/{id} | consultar / eliminar plan propio |
| PATCH | /api/plans/{id}/meals/{id} | completed: true/false |
| GET | /api/health | PostgreSQL y presencia de tablas |
| GET | /api/health/live | proceso Flask disponible |

Perfil:
```json
{"fecha_nacimiento":"1994-03-12","sexo_registrado":"no_indicado","actividad":"media","preferencia":"vegetarian"}
```
Sexo: null, no_indicado, femenino, masculino o intersexual. Actividad: baja,
media o alta. Preferencia: balanced o vegetarian. Nacimiento: 1900 a hoy.

Medición:
```json
{"peso_kg":"68.50","estatura_cm":"172.00"}
```
Valores positivos, hasta dos decimales, devueltos como strings para conservar
precisión decimal. Se guardan fecha/hora del servidor y zona UTC; el frontend
muestra el instante en la zona del navegador. GET acepta `?page=1`, 20 por página.

Plan:
```json
{"nombre":"Semana de ejemplo","fecha_inicio":"2026-10-19"}
```
Debe existir perfil; fecha de inicio debe ser lunes, entre 1900 y 2100. Devuelve
plan con siete days y tres meals por día. GET listado acepta `?page=1`, 10 por página.
La preferencia se copia del perfil, no se recibe desde un usuario ajeno.

HTTP: 201 creado; 204 eliminado/cierre de sesión; 400 validación; 401 sin sesión;
403 falta cabecera; 404 recurso ajeno/inexistente; 409 conflicto; 413 cuerpo grande;
415 formato incorrecto; 429 límite de intentos; 503 base no disponible.
