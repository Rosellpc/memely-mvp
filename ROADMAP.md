# Roadmap

## Aplicación implementada
- Cuentas PostgreSQL, hash de contraseña, login/logout y sesiones de ocho horas.
- Perfil con nacimiento, sexo opcional, actividad y preferencia.
- Historial de peso/estatura, paginación y eliminación.
- Planes semanales de ejemplo, historial y seguimiento de comidas.
- Interfaz responsive, estados vacíos, validación y errores.
- Migraciones, pruebas PostgreSQL y workflow CI.

## Infraestructura para practicar Docker
- Imagen de varias etapas con wheels y usuario sin privilegios.
- Compose web + migrate + db, salud, volumen y override de desarrollo.
- Stack de pruebas aislado y guía de backup/restore.

## Ejercicios siguientes
- Proxy TLS, redes separadas y roles PostgreSQL.
- Límites de recursos, métricas, fallos y recuperación.
- Backups programados, digests y despliegue reproducible.

Antes de público: recuperación/verificación de cuentas, eliminación y retención
de datos, TLS y operación del rate limit detrás del proxy. Nutrición personalizada
requiere otro desarrollo y revisión profesional; no forma parte de esta demo.
