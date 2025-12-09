#!/bin/bash
# Script para agregar POSTGRES_PASSWORD al .env si falta
# Uso: ./scripts/add-postgres-password.sh [password]

set -e

ENV_DIR="${1:-~/dev}"
ENV_FILE="$ENV_DIR/html/.env"
PASSWORD="${2:-}"

# Si no se proporciona contraseña, generar una aleatoria
if [ -z "$PASSWORD" ]; then
    PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    echo "🔑 Generando contraseña aleatoria para PostgreSQL..."
fi

echo "📁 Verificando .env en: $ENV_FILE"

# Verificar si el archivo existe
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: No se encuentra $ENV_FILE"
    echo "💡 Asegúrate de que el archivo .env existe"
    exit 1
fi

# Verificar si POSTGRES_PASSWORD ya existe
if grep -q "^POSTGRES_PASSWORD=" "$ENV_FILE" 2>/dev/null; then
    echo "✅ POSTGRES_PASSWORD ya está definido en $ENV_FILE"
    echo "📋 Valor actual (primeros caracteres):"
    grep "^POSTGRES_PASSWORD=" "$ENV_FILE" | sed 's/=.*/=***/' 
    echo ""
    read -p "¿Deseas actualizar POSTGRES_PASSWORD? (s/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        echo "❌ Operación cancelada"
        exit 0
    fi
    # Eliminar la línea existente
    sed -i.bak '/^POSTGRES_PASSWORD=/d' "$ENV_FILE"
fi

# Agregar POSTGRES_PASSWORD al final del archivo
echo "" >> "$ENV_FILE"
echo "# PostgreSQL password (agregado automáticamente)" >> "$ENV_FILE"
echo "POSTGRES_PASSWORD=$PASSWORD" >> "$ENV_FILE"

echo "✅ POSTGRES_PASSWORD agregado a $ENV_FILE"
echo "🔑 Contraseña generada: $PASSWORD"
echo ""
echo "⚠️  IMPORTANTE: Guarda esta contraseña en un lugar seguro"
echo "⚠️  Si cambias la contraseña, asegúrate de actualizar también la base de datos"

