# Laboratorio Docker avanzado

La aplicación está lista para centrar el aprendizaje en infraestructura.

## 1. Arranque y diagnóstico

```bash
docker compose up -d --build --wait
docker compose ps -a
docker compose logs --tail 50 migrate web
curl -f http://localhost:8080/api/health
```

`migrate` termina con código 0; `web` y `db` deben estar saludables. El web espera
PostgreSQL saludable y migraciones terminadas. `read_only` y USER no-root protegen
el proceso de aplicación; PostgreSQL necesita escribir en su volumen.

## 2. Redes

No existe puerto publicado de PostgreSQL. Inspecciona la red del proyecto y
comprueba DNS desde web:

```bash
docker compose exec web python -c "import socket; print(socket.gethostbyname('db'))"
```

## 3. Persistencia

Crea una cuenta, un perfil, una medida y un menú. Ejecuta `docker compose down`,
levanta de nuevo e inicia sesión con la misma cuenta. Los datos deben permanecer.
`docker compose down -v` los elimina: úsalo solo en stacks desechables.

## 4. Backups PostgreSQL (Git Bash)

```bash
mkdir -p backups
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > backups/memely.dump
```

Ejecutar el comando anterior en Git Bash, no con redirección binaria de Windows
PowerShell 5. Conserva diferentes nombres/fechas, restringe acceso y guarda una
copia fuera del equipo. No versionar backups: contienen información personal.

Restaura primero en una base separada, nunca sobre datos originales:

```bash
docker compose exec -T db sh -c 'createdb -U "$POSTGRES_USER" memely_restore'
docker compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d memely_restore --no-owner --exit-on-error' < backups/memely.dump
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d memely_restore -c "SELECT count(*) FROM usuarios;"'
```

Verifica también perfiles, medidas, planes, comidas y versión Alembic. Una copia
no está validada hasta practicar su restauración y comprobar los datos.

## 5. Migraciones

```bash
docker compose -f compose.yaml -f compose.dev.yaml exec web alembic current
docker compose -f compose.yaml -f compose.dev.yaml exec web alembic check
```

Cambios futuros: editar modelos, generar revision --autogenerate en desarrollo,
leer upgrade/downgrade, probar sobre backup y construir nueva imagen. No ejecutar
downgrade en una base con datos que quieras conservar sin revisar su efecto.

## 6. Pruebas

```bash
docker compose -p memely-test -f compose.test.yaml up --build --abort-on-container-exit --exit-code-from test
docker compose -p memely-test -f compose.test.yaml down -v
```

El PostgreSQL de prueba es temporal y tiene otro nombre/red. No conectar esta
suite a tu base de trabajo; la fixture limpia registros entre pruebas.

## 7. Siguientes ejercicios

1. Medir caché y tamaño de la imagen con varias etapas y wheels.
2. Separar redes y roles de DB; añadir límites de CPU/memoria y observar fallos.
3. Simular caída de PostgreSQL: live sigue respondiendo, health debe devolver 503;
   restablecer la base y confirmar recuperación sin perder datos.
4. Incorporar Nginx y TLS, IPs de proxy confiables, COOKIE_SECURE y rate limits
   adaptados a esa topología. El límite actual identifica al peer directo.
5. Etiquetas inmutables/digests, escaneo de imagen, despliegue y rollback.
6. Ejecutar backups programados y restauraciones comprobadas.

El workflow CI incluido prueba y construye; no publica ni despliega.
