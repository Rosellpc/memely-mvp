#!/usr/bin/env bash
set -euo pipefail

echo "Contexto Docker seleccionado:"
docker context show

echo "Espacio antes de limpiar:"
docker system df

echo "Limpiar caché de construcción sin uso:"
docker builder prune

echo "Limpiar imágenes sin etiqueta y sin uso:"
docker image prune

echo "Espacio después de limpiar:"
docker system df