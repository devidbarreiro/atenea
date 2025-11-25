#!/usr/bin/env bash
# Script de setup inicial del servidor OVH
# Crea la estructura de directorios y configuración básica
# Ejecutar UNA SOLA VEZ en el servidor

set -e

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 Configurando servidor OVH para Atenea${NC}"

# Configuración
SSH_HOST="5.196.245.4"
SSH_USER="ubuntu"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/atenea_ovh_key}"

# Verificar que existe la clave SSH
if [[ ! -f "$SSH_KEY" ]]; then
    echo -e "${RED}Error: No se encuentra la clave SSH en $SSH_KEY${NC}"
    exit 1
fi

# Comando SSH base
SSH_CMD="ssh -i $SSH_KEY -o StrictHostKeyChecking=no $SSH_USER@$SSH_HOST"

echo -e "${YELLOW}⚠️  Este script configurará el servidor. ¿Continuar? (s/N)${NC}"
read -r response
if [[ ! "$response" =~ ^[Ss]$ ]]; then
    echo "Cancelado."
    exit 0
fi

# Ejecutar setup en el servidor
$SSH_CMD << 'SETUP_SCRIPT'
set -e

echo "📁 Creando estructura de directorios..."

# Crear directorios para cada entorno
for env in dev demo prod; do
    echo "  → Creando ~/$env/"
    mkdir -p ~/$env/html
    mkdir -p ~/$env/backups
done

# Crear directorio para NPM (si no existe)
mkdir -p ~/npm

echo "✅ Estructura de directorios creada"
echo ""
echo "📋 Próximos pasos:"
echo "1. Crear archivos .env en cada directorio (~/dev/.env, ~/demo/.env, ~/prod/.env)"
echo "2. Colocar credentials.json en cada directorio"
echo "3. Configurar Nginx Proxy Manager para los dominios:"
echo "   - dev.atenea.nxhumans.com → 172.17.0.1:8080"
echo "   - demo.atenea.nxhumans.com → 172.17.0.1:8081"
echo "   - atenea.nxhumans.com → 172.17.0.1:8082"
echo ""
echo "💡 Los docker-compose.yml se copiarán automáticamente en el primer despliegue"

SETUP_SCRIPT

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Setup del servidor completado${NC}"
    echo ""
    echo -e "${YELLOW}📝 Recuerda:${NC}"
    echo "  - Crear archivos .env en el servidor para cada entorno"
    echo "  - Configurar Nginx Proxy Manager"
    echo "  - El primer despliegue creará los docker-compose.yml automáticamente"
else
    echo -e "${RED}❌ Error durante el setup${NC}"
    exit 1
fi

