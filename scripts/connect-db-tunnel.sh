#!/usr/bin/env bash
# Script para crear túnel SSH a las bases de datos de producción
# Uso: ./scripts/connect-db-tunnel.sh [dev|demo]
#
# Forma sencilla: SSH port forwarding al contenedor Docker
# El puerto se expone solo en localhost del servidor (seguro)

set -e

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Validar argumentos
ENV=${1:-}
if [[ -z "$ENV" ]]; then
    echo -e "${RED}Error: Debes especificar el entorno (dev|demo)${NC}"
    echo "Uso: ./scripts/connect-db-tunnel.sh [dev|demo]"
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

# Puerto local y configuración
if [[ "$ENV" == "dev" ]]; then
    LOCAL_PORT=5432
    REMOTE_PORT=5432  # Puerto en el servidor (exponer en docker-compose)
    DB_NAME="atenea_dev"
elif [[ "$ENV" == "demo" ]]; then
    LOCAL_PORT=5433
    REMOTE_PORT=5433  # Puerto en el servidor (exponer en docker-compose)
    DB_NAME="atenea_demo"
fi

echo ""
echo -e "${BLUE}📡 Creando túnel SSH...${NC}"
echo -e "   Entorno: ${GREEN}$ENV${NC}"
echo -e "   Puerto local: ${GREEN}$LOCAL_PORT${NC} → Servidor: ${GREEN}$REMOTE_PORT${NC}"
echo ""

# Verificar si el puerto local ya está en uso
if lsof -Pi :$LOCAL_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  El puerto $LOCAL_PORT ya está en uso${NC}"
    read -p "¿Continuar? (s/N): " response
    if [[ ! "$response" =~ ^[Ss]$ ]]; then
        exit 0
    fi
fi

echo -e "${GREEN}🚀 Iniciando túnel...${NC}"
echo -e "${YELLOW}   Presiona Ctrl+C para cerrar${NC}"
echo ""

# Crear túnel SSH simple y directo
# -L: local port forwarding
# -N: no ejecutar comandos, solo forwarding
ssh -i "$SSH_KEY" \
    -o StrictHostKeyChecking=no \
    -L $LOCAL_PORT:localhost:$REMOTE_PORT \
    -N \
    "$SSH_USER@$SSH_HOST" &

TUNNEL_PID=$!
sleep 1

if ps -p $TUNNEL_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Túnel activo (PID: $TUNNEL_PID)${NC}"
    echo ""
    echo -e "${BLUE}📋 Configuración para TablePlus:${NC}"
    echo -e "   Host: ${GREEN}localhost${NC}"
    echo -e "   Puerto: ${GREEN}$LOCAL_PORT${NC}"
    echo -e "   Base de datos: ${GREEN}$DB_NAME${NC}"
    echo -e "   Usuario: ${GREEN}atenea${NC}"
    echo -e "   Contraseña: ${YELLOW}(la que tienes)${NC}"
    echo ""
    
    trap "kill $TUNNEL_PID 2>/dev/null; echo -e '\n${GREEN}✅ Túnel cerrado${NC}'; exit 0" INT TERM
    wait $TUNNEL_PID
else
    echo -e "${RED}❌ Error al crear el túnel${NC}"
    echo -e "${YELLOW}💡 Asegúrate de que el puerto $REMOTE_PORT esté expuesto en el servidor${NC}"
    exit 1
fi
