#!/usr/bin/env bash
# Script de inicialización para Docker que ejecuta migraciones antes de iniciar Daphne
# Exit on error
set -o errexit

echo "🔄 Ejecutando migraciones de Django..."
python manage.py migrate --noinput

echo "✅ Migraciones completadas. Iniciando servidor Daphne..."
# Ejecutar el comando pasado como argumentos
exec "$@"
