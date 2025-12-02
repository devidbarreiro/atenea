#!/bin/bash
# Script para migrar secretos desde .env a Doppler
# Uso: ./scripts/migrate-to-doppler.sh [config]
# Ejemplo: ./scripts/migrate-to-doppler.sh dev

set -e

CONFIG="${1:-dev}"
ENV_FILE=".env"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "🚀 Migrando secretos a Doppler..."
echo "📁 Archivo: $ENV_FILE"
echo "⚙️  Config: $CONFIG"
echo ""

cd "$PROJECT_DIR"

# Verificar que Doppler está instalado
if ! command -v doppler &> /dev/null; then
    echo "❌ Doppler CLI no está instalado"
    echo ""
    echo "📦 Instalar con:"
    echo "   brew install dopplerhq/cli/doppler"
    echo ""
    echo "🔗 O visita: https://docs.doppler.com/docs/install-cli"
    exit 1
fi

# Verificar autenticación
if ! doppler me &> /dev/null; then
    echo "❌ No estás autenticado en Doppler"
    echo ""
    echo "🔐 Autentica con:"
    echo "   doppler login"
    exit 1
fi

# Verificar que el archivo existe
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Archivo $ENV_FILE no encontrado"
    echo "💡 Crea el archivo .env primero"
    exit 1
fi

# Verificar configuración de proyecto
echo "📋 Verificando configuración de Doppler..."
if ! doppler setup --project atenea --config "$CONFIG" --no-interactive &>/dev/null; then
    echo "⚠️  Proyecto 'atenea' o config '$CONFIG' no encontrado"
    echo ""
    echo "💡 Crea el proyecto en Doppler primero:"
    echo "   1. Ve a https://dashboard.doppler.com"
    echo "   2. Crea un proyecto llamado 'atenea'"
    echo "   3. Crea configs: dev, staging, prod"
    echo ""
    read -p "¿Quieres crear el proyecto ahora? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        doppler setup --project atenea --config "$CONFIG"
    else
        exit 1
    fi
fi

echo ""
echo "⬆️  Subiendo secretos a Doppler..."
echo ""

# Subir secretos
doppler secrets upload "$ENV_FILE" --config "$CONFIG" --no-interactive

echo ""
echo "✅ Secretos migrados exitosamente a Doppler!"
echo ""
echo "📋 Verificar secretos:"
echo "   doppler secrets --config $CONFIG"
echo ""
echo "💡 Para usar secretos localmente:"
echo "   doppler run -- python manage.py runserver"
echo ""
echo "💡 O sincronizar a .env:"
echo "   doppler secrets download --config $CONFIG --no-file --format env > .env"
echo ""
echo "⚠️  IMPORTANTE:"
echo "   - El archivo .env local puede eliminarse después de migrar"
echo "   - Usa 'doppler run' para desarrollo en lugar de .env"
echo "   - Para producción, configura sincronización en Render/GCP"

