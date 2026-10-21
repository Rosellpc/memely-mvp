# Arquitectura

## Backend

- `backend/app.py`: factory, configuración, seguridad HTTP, errores, frontend y salud.
- `backend/database.py`: engine/pool y una sesión SQLAlchemy por petición, cerrada
  al terminar. Las rutas confirman explícitamente las escrituras.
- `backend/auth.py`: registro, login, logout, identidad y límite de intentos en DB.
- `backend/api.py`: perfiles, medidas y planes; autorización por propietario.
- `backend/models.py`: esquema relacional, claves foráneas, NUMERIC y constraints.
- `backend/validation.py`: tipos, fechas, opciones y decimales con dos cifras.
- `backend/diet_engine.py`: catálogo determinista de comidas de ejemplo.
- `migrations/`: única fuente para actualizar tablas. Nunca se usa create_all.

## Frontend

Aplicación sin framework ni dependencias de red. El login/registro da acceso al
resumen, perfil, medidas y menús. Cookies HttpOnly conservan la sesión. Los datos
dinámicos se insertan mediante textContent, no HTML concatenado. Las medidas y
los planes tienen paginación; eliminar requiere confirmación. Las comidas
permiten marcar seguimiento y conservarlo en PostgreSQL.

## Relaciones

```text
usuarios ── 0..1 perfiles
         ├─ 0..N mediciones
         └─ 0..N planes ── 21 comidas por plan generado
```

El esquema impide medidas sin usuario o valores no positivos. La API evita
fechas de nacimiento futuras y calcula edad al consultar. Los planes son
instantáneas: cambiar preferencias no altera menús anteriores. Eliminar un plan
elimina sus comidas mediante cascade; eliminar una medida no toca otras.
No existe borrado de usuario en esta versión.

## Operación

La instancia web no escribe datos locales; puede reemplazarse sin pérdida.
PostgreSQL requiere un volumen y backups consistentes. Las migraciones corren
una sola vez en un servicio dedicado antes del web; las futuras migraciones deben
seguir siendo compatibles con el despliegue que se quiera usar.
El contenedor PostgreSQL usa el usuario del laboratorio también para migraciones;
separar roles de aplicación/migración es un siguiente ejercicio de hardening.

Referencias de implementación: [sesiones SQLAlchemy](https://docs.sqlalchemy.org/en/20/orm/session_basics.html),
[orden de arranque Compose](https://docs.docker.com/compose/how-tos/startup-order/) y
[revisión de migraciones Alembic](https://alembic.sqlalchemy.org/en/latest/autogenerate.html).
