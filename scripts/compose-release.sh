#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

docker compose \
  -f compose.yaml \
  -f compose.release.yaml \
  -f compose.resources.yaml \
  -f compose.proxy.yaml \
  "$@"

# # Desplegar las imágenes configuradas, sin reconstruir
# bash scripts/compose-release.sh up -d --no-build --wait

# # Consultar los registros recientes
# bash scripts/compose-release.sh logs --tail 30 web proxy

# # Comprobar las migraciones aplicadas
# bash scripts/compose-release.sh exec web alembic current