#!/usr/bin/env bash
# Script para obtener la contraseña de la base de datos desde el servidor
# Uso: ./scripts/get-db-password.sh [dev|demo]

set -e

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Validar argumentos
ENV=${1:-}
if [[ -z "$ENV" ]]; then
    echo -e "${RED}Error: Debes especificar el entorno (dev|demo)${NC}"
    echo "Uso: ./scripts/get-db-password.sh [dev|demo]"
    exit 1
fi

if [[ ! "$ENV" =~ ^(dev|demo)$ ]]; then
    echo -e "${RED}Error: Entorno inválido. Usa: dev o demo${NC}"
    exit 1
fi

# Configuración del servidor
SSH_HOST="5.196.245.4"
SSH_USER="ubuntu"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/atenea_ovh_key}"

# Verificar que existe la clave SSH
if [[ ! -f "$SSH_KEY" ]]; then
    echo -e "${RED}Error: No se encuentra la clave SSH en $SSH_KEY${NC}"
    exit 1
fi

echo -e "${GREEN}🔍 Obteniendo contraseña de la base de datos para $ENV...${NC}"

# Obtener la contraseña del archivo .env
PASSWORD=$(ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$SSH_HOST" \
    "cd ~/$ENV && grep POSTGRES_PASSWORD .env 2>/dev/null | cut -d '=' -f2- || echo ''")

if [[ -z "$PASSWORD" ]]; then
    echo -e "${RED}❌ No se pudo obtener la contraseña${NC}"
    echo -e "${YELLOW}Verifica que el archivo .env exista en ~/$ENV en el servidor${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Contraseña obtenida:${NC}"
echo -e "   ${YELLOW}$PASSWORD${NC}"
echo ""




