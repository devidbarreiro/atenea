#!/usr/bin/env bash
# Script para validar archivo .env antes del deploy
# Uso: ./scripts/validate-env.sh [dev|demo|prod] [ruta-al-.env]

set -e

ENV=${1:-}
ENV_FILE=${2:-}

if [[ -z "$ENV" ]]; then
    echo "❌ Error: Debes especificar el entorno (dev|demo|prod)"
    echo "Uso: $0 [dev|demo|prod] [ruta-al-.env]"
    exit 1
fi

# Si no se especifica ruta, usar la estándar
if [[ -z "$ENV_FILE" ]]; then
    ENV_FILE=".env"
fi

if [[ ! -f "$ENV_FILE" ]]; then
    echo "❌ Error: No se encuentra el archivo .env en: $ENV_FILE"
    exit 1
fi

echo "🔍 Validando .env para entorno: $ENV"
echo "📁 Archivo: $ENV_FILE"
echo ""

# Variables requeridas
REQUIRED_VARS=(
    "SECRET_KEY"
    "POSTGRES_PASSWORD"
    "POSTGRES_USER"
    "POSTGRES_DB"
    "GCS_BUCKET_NAME"
    "GCS_PROJECT_ID"
)

# Variables recomendadas
RECOMMENDED_VARS=(
    "DATABASE_URL"
    "CELERY_BROKER_URL"
    "CELERY_RESULT_BACKEND"
    "CHANNEL_REDIS_URL"
    "USE_SQLITE"
    "DEBUG"
)

MISSING_REQUIRED=()
MISSING_RECOMMENDED=()

# Verificar variables requeridas
echo "📋 Verificando variables requeridas..."
for var in "${REQUIRED_VARS[@]}"; do
    if grep -q "^${var}=" "$ENV_FILE" 2>/dev/null; then
        VALUE=$(grep "^${var}=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'")
        if [[ -z "$VALUE" ]] || [[ "$VALUE" == "change-me"* ]] || [[ "$VALUE" == "your-"* ]]; then
            MISSING_REQUIRED+=("$var (valor por defecto/no configurado)")
        else
            echo "  ✅ $var"
        fi
    else
        MISSING_REQUIRED+=("$var")
    fi
done

# Verificar variables recomendadas
echo ""
echo "📋 Verificando variables recomendadas..."
for var in "${RECOMMENDED_VARS[@]}"; do
    if grep -q "^${var}=" "$ENV_FILE" 2>/dev/null; then
        echo "  ✅ $var"
    else
        MISSING_RECOMMENDED+=("$var")
    fi
done

# Validaciones específicas por entorno
echo ""
echo "🔍 Validaciones específicas para $ENV..."

# Validar USE_SQLITE
if grep -q "^USE_SQLITE=" "$ENV_FILE" 2>/dev/null; then
    USE_SQLITE_VALUE=$(grep "^USE_SQLITE=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'" | tr '[:upper:]' '[:lower:]')
    if [[ "$USE_SQLITE_VALUE" == "true" ]] && [[ "$ENV" != "dev" ]]; then
        echo "  ⚠️  ADVERTENCIA: USE_SQLITE=True en entorno $ENV (debería ser False para demo/prod)"
    elif [[ "$USE_SQLITE_VALUE" == "false" ]]; then
        echo "  ✅ USE_SQLITE=False (correcto para PostgreSQL)"
    fi
fi

# Validar DEBUG
if grep -q "^DEBUG=" "$ENV_FILE" 2>/dev/null; then
    DEBUG_VALUE=$(grep "^DEBUG=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'" | tr '[:upper:]' '[:lower:]')
    if [[ "$DEBUG_VALUE" == "true" ]] && [[ "$ENV" == "prod" ]]; then
        echo "  ⚠️  ADVERTENCIA: DEBUG=True en PRODUCCIÓN (riesgo de seguridad)"
    elif [[ "$DEBUG_VALUE" == "false" ]] && [[ "$ENV" == "prod" ]]; then
        echo "  ✅ DEBUG=False (correcto para producción)"
    fi
fi

# Validar CELERY_BROKER_URL
if grep -q "^CELERY_BROKER_URL=" "$ENV_FILE" 2>/dev/null; then
    CELERY_BROKER=$(grep "^CELERY_BROKER_URL=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'")
    if [[ "$CELERY_BROKER" == redis://redis:* ]] || [[ "$CELERY_BROKER" == redis://localhost:* ]]; then
        echo "  ✅ CELERY_BROKER_URL configurado correctamente"
    else
        echo "  ⚠️  ADVERTENCIA: CELERY_BROKER_URL debería usar redis://redis:6379/0 para Docker"
    fi
fi

# Validar DATABASE_URL
if grep -q "^DATABASE_URL=" "$ENV_FILE" 2>/dev/null; then
    DATABASE_URL=$(grep "^DATABASE_URL=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'")
    if [[ "$DATABASE_URL" == postgresql://* ]]; then
        echo "  ✅ DATABASE_URL apunta a PostgreSQL"
    else
        echo "  ⚠️  ADVERTENCIA: DATABASE_URL no apunta a PostgreSQL"
    fi
fi

# Resultado final
echo ""
echo "═══════════════════════════════════════════════════════════"
if [[ ${#MISSING_REQUIRED[@]} -eq 0 ]]; then
    echo "✅ Todas las variables requeridas están presentes"
else
    echo "❌ Faltan variables requeridas:"
    printf '  - %s\n' "${MISSING_REQUIRED[@]}"
    echo ""
    echo "El deploy fallará sin estas variables."
    exit 1
fi

if [[ ${#MISSING_RECOMMENDED[@]} -gt 0 ]]; then
    echo ""
    echo "⚠️  Variables recomendadas faltantes:"
    printf '  - %s\n' "${MISSING_RECOMMENDED[@]}"
    echo ""
    echo "Estas variables se pueden configurar automáticamente durante el deploy."
fi

echo ""
echo "✅ Validación completada. El archivo .env está listo para el deploy."
echo "═══════════════════════════════════════════════════════════"
