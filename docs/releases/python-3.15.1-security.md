# Validacion de Python 3.15.1 y seguridad (2026-10-23)

- Dockerfile: Python 3.15.1 Slim fijado por digest.
- Dockerfile.alpine: Python 3.15.1 Alpine 3.23 fijado por digest en wheels y runtime.
- Alpine 3.23 contiene musl 1.2.5-r24; Scout no reporta CVE-2026-107891 en la candidata.
- No se mezclan repositorios edge con las ramas estables.
- production elimina pip y ensurepip; test conserva pip para pytest.
- Compose y ambos workflows seleccionan production para la aplicacion.
- .python-version selecciona 3.15.1 para herramientas locales; no modifica un entorno virtual ya creado.

## Comprobaciones realizadas

- Construccion production Alpine y Slim: correctas.
- Pruebas Alpine con PostgreSQL aislado: 28 passed; Alembic sin diferencias; salida 0.
- Imports Flask, SQLAlchemy, Psycopg, Alembic y Gunicorn: correctos en ambas variantes.
- pip y ensurepip ausentes en production Alpine.
- Configuracion Compose normal y Alpine: valida.
- Scout completo Alpine: 0 criticas, 0 altas, 1 media, 0 bajas, 0 sin especificar.

## Hallazgo pendiente

Scout identifica CVE-2025-60876 en BusyBox 1.37.0-r30 de Alpine 3.23 y lo marca como MEDIUM, sin version corregida disponible. No se suprime ni se declara una imagen sin vulnerabilidades. Reevaluar cuando Alpine publique una correccion y antes de publicar la imagen.

La rama Alpine 3.24 consultada solo ofrecia musl 1.2.6-r3; ejecutar apk upgrade no instalaba la revision r6 que exigia Scout. Se eligio la base oficial Alpine 3.23 con parche reconocido por el analizador y se repitieron las pruebas. Las revisiones de paquetes se interpretan dentro de cada rama, no entre ramas distintas.

Referencia oficial: https://www.alpinelinux.org/posts/Alpine-3.21.9-3.22.7-3.23.7-3.24.3-released.html

No se publicaron imagenes ni se modifico el despliegue activo. Los cambios previos del usuario en compose.release.yaml y compose.release.previous.yaml se conservaron.
