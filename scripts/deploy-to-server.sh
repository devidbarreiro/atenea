#!/usr/bin/env bash
# Script de despliegue a servidor OVH
# Uso: ./scripts/deploy-to-server.sh [dev|demo|prod] [branch]

set -e  # Exit on error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Validar argumentos
ENV=${1:-}
BRANCH=${2:-}

if [[ -z "$ENV" ]]; then
    echo -e "${RED}Error: Debes especificar el entorno (dev|demo|prod)${NC}"
    exit 1
fi

# Mapeo de entorno a branch por defecto
if [[ -z "$BRANCH" ]]; then
    case "$ENV" in
        dev) BRANCH="dev" ;;
        demo) BRANCH="demo" ;;
        prod) BRANCH="main" ;;
        *)
            echo -e "${RED}Error: Entorno inválido. Usa: dev, demo o prod${NC}"
            exit 1
            ;;
    esac
fi

# Configuración del servidor
SSH_HOST="5.196.245.4"
SSH_USER="ubuntu"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/atenea_ovh_key}"
ENV_DIR="~/$ENV"
COMPOSE_FILE="docker-compose.$ENV.yml"

echo -e "${GREEN}🚀 Iniciando despliegue a ${ENV} (branch: ${BRANCH})${NC}"

# Verificar que existe la clave SSH
if [[ ! -f "$SSH_KEY" ]]; then
    echo -e "${RED}Error: No se encuentra la clave SSH en $SSH_KEY${NC}"
    echo -e "${YELLOW}Configura la variable SSH_KEY o coloca la clave en ~/.ssh/id_rsa${NC}"
    exit 1
fi

# Comando SSH base
SSH_CMD="ssh -i $SSH_KEY -o StrictHostKeyChecking=no $SSH_USER@$SSH_HOST"

# Ejecutar despliegue en el servidor
$SSH_CMD << EOF
set -e

echo "📁 Cambiando a directorio $ENV_DIR"
cd $ENV_DIR || { echo "Error: No existe el directorio $ENV_DIR"; exit 1; }

echo "📥 Actualizando código desde branch $BRANCH"
if [ -d "html/.git" ]; then
    cd html
    git fetch origin
    git checkout $BRANCH
    git pull origin $BRANCH
    cd ..
else
    echo "⚠️  El directorio html no es un repo git, clonando..."
    rm -rf html
    git clone -b $BRANCH https://github.com/$(git config --get remote.origin.url | sed 's/.*github.com[:/]\(.*\)\.git/\1/') html || {
        echo "Error: No se pudo clonar el repositorio"
        exit 1
    }
fi

echo "📋 Copiando docker-compose.yml a html/"
cp html/docker/$COMPOSE_FILE html/docker-compose.yml || {
    echo "Error: No se encontró docker/$COMPOSE_FILE en el repositorio"
    exit 1
}

echo "🔨 Construyendo y reiniciando contenedores (desde html/)"
cd html
docker compose down || true
docker compose build --no-cache
docker compose up -d

echo "⏳ Esperando a que los servicios estén listos..."
# Esperar a que la base de datos esté lista
echo "⏳ Esperando a que la base de datos esté lista..."
timeout=60
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if docker compose exec -T db pg_isready -U atenea > /dev/null 2>&1; then
        echo "✅ Base de datos lista"
        break
    fi
    echo "⏳ Esperando base de datos... ($elapsed/$timeout segundos)"
    sleep 2
    elapsed=$((elapsed + 2))
done

if [ $elapsed -ge $timeout ]; then
    echo "❌ Error: La base de datos no está lista después de $timeout segundos"
    exit 1
fi

echo "🔄 Ejecutando migraciones"
if ! docker compose --profile tools run --rm migrate; then
    echo "❌ Error: Falló la ejecución de migraciones"
    exit 1
fi

echo "📦 Recolectando archivos estáticos"
if ! docker compose --profile tools run --rm collectstatic; then
    echo "❌ Error: Falló la recolección de archivos estáticos"
    exit 1
fi
cd ..

echo "✅ Despliegue completado!"
echo "🌐 URL: https://$([ "$ENV" == "prod" ] && echo "atenea.nxhumans.com" || echo "$ENV.atenea.nxhumans.com")"

EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Despliegue a ${ENV} completado exitosamente${NC}"
else
    echo -e "${RED}❌ Error durante el despliegue${NC}"
    exit 1
fi

