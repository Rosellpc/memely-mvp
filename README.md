# Memely · Tu bienestar, con perspectiva

Aplicación de práctica para aprender Docker avanzado con un flujo real:
registro e inicio de sesión, perfil, historial de medidas y menús semanales.
Frontend HTML/CSS/JavaScript, API Flask, SQLAlchemy, PostgreSQL 17 y Alembic.
Los menús son ejemplos deterministas: no hay IA, prescripción ni personalización
nutricional por peso, sexo o edad. Usa datos ficticios para los ejercicios.

## Ejecutar (Git Bash, desde la raíz del proyecto)

Si ya tienes `.env`, consérvalo. Para una instalación nueva:

```bash
cp -n .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

Completa `SECRET_KEY` y `POSTGRES_PASSWORD` en `.env` con valores aleatorios
distintos; la clave de sesión debe tener al menos 32 caracteres. Define también
`POSTGRES_USER=memely` y `POSTGRES_DB=memely`. No cambies las credenciales de una
base existente solo editando `.env`: PostgreSQL las inicializa únicamente al
crear un volumen vacío. Mantén `COOKIE_SECURE=false` para HTTP local.

```bash
docker compose config --quiet
docker compose up -d --build --wait
```

Abre http://localhost:8080 (o el puerto `MEMELY_PORT` de `.env`). Crea una cuenta,
completa el perfil, registra una medición y crea un menú con fecha de inicio
en lunes. Marca comidas realizadas y vuelve a iniciar sesión: tus datos persisten.
Una cuenta existente en PostgreSQL sigue funcionando con su contraseña anterior.

## Qué ejecuta Docker

```text
Navegador → localhost:8080 → web (Gunicorn + Flask)
                                  ↓ red interna de Compose
                                 db (PostgreSQL) → postgres_data
                                  ↑
                           migrate (Alembic, termina en código 0)
```

`db` debe estar saludable; `migrate` aplica las migraciones; después arranca
`web`. Es normal que `migrate` aparezca como `Exited (0)`. Los workers nunca
crean tablas al iniciar. Cada actualización vuelve a ejecutar las migraciones
pendientes al ejecutar `compose up`.

La imagen usa varias etapas, caché de wheels y UID 10001. La aplicación tiene
raíz de solo lectura, `/tmp` temporal y privilegios restringidos. PostgreSQL no
publica un puerto al equipo. `/api/health` comprueba conexión y tablas; un estado
`unhealthy` no reinicia automáticamente un contenedor cuyo proceso sigue activo.

## Desarrollo

```bash
docker compose -f compose.yaml -f compose.dev.yaml up -d --build
docker compose logs -f web
```

El override monta frontend, backend y migraciones y activa la recarga de Flask.
Para volver a Gunicorn: `docker compose up -d --force-recreate --wait`.
Para detener conservando PostgreSQL: `docker compose down`.
No uses `down -v` si necesitas conservar los datos.

## Pruebas aisladas con PostgreSQL real

```bash
docker compose -p memely-test -f compose.test.yaml up --build --abort-on-container-exit --exit-code-from test
docker compose -p memely-test -f compose.test.yaml down -v
```

Esta configuración es independiente: usa otra red y un PostgreSQL temporal sin
volúmenes persistentes ni puertos publicados. Ejecuta migraciones, pruebas de
integración y `alembic check` para detectar diferencias entre modelos y esquema.
La fixture se niega a limpiar bases cuyo nombre no termine en `_test`.
El workflow de GitHub Actions ejecuta estas comprobaciones y construye la imagen;
no publica ni despliega nada.

## Datos y seguridad

- PostgreSQL es la única base utilizada por la aplicación actual.
- `usuarios`: correo normalizado y único, contraseña con hash scrypt.
- `perfiles`: nacimiento, sexo opcional, actividad y preferencia; uno por usuario.
- `mediciones`: peso kg y estatura cm en NUMERIC positivo, con historial de fechas.
- `planes` y `comidas`: 7 días, 21 comidas y seguimiento individual.
- La sesión firmada caduca a las 8 horas. No almacena contraseñas.
- Todas las rutas personales filtran por el usuario autenticado; los identificadores
  ajenos devuelven 404. No se habilita CORS. Las escrituras requieren cabecera
  personalizada y JSON para proteger frente a formularios de otros sitios.
- Login/registro comparten un límite persistente de 30 solicitudes por IP en
  ventanas de 15 minutos, válido entre workers. No confía en X-Forwarded-For.
- Las API devuelven errores JSON, nunca detalles SQL ni hashes.

Es una base de aprendizaje local, no un servicio público terminado: faltan TLS,
verificación de correo, recuperación de contraseña, borrado de cuenta y políticas
de privacidad/retención. Detrás de un proxy, configura IPs confiables y adapta el
rate limit antes de exponerlo. Bajo HTTPS usa `COOKIE_SECURE=true`.

## Compatibilidad con los ejercicios anteriores

La migración inicial `c4b08eaaf62f` se conserva intacta. La nueva revisión
`d92a310b1200` agrega tablas y preferencias sin borrar usuarios ni mediciones.
El volumen SQLite antiguo `memely_data` y `database/foods.db` no se modifican.
Los perfiles anónimos y menús SQLite no se importan automáticamente: no tienen
una identidad verificable para asociarlos a una cuenta PostgreSQL.

Las antiguas rutas registro.html/perfil.html/menu.html sirven la aplicación
integrada. Sus archivos originales se conservan como referencia histórica.

Consulta [la arquitectura](docs/arquitectura.md), [la API](docs/api.md) y
[el laboratorio Docker avanzado](docs/docker-avanzado.md).
