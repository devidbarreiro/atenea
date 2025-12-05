#!/bin/bash

# Script para verificar credenciales y revisar logs de videos en los servidores
# Uso: ./scripts/check-credentials-and-logs.sh [video_id]

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuración SSH (usar secrets de GitHub Actions o variables de entorno)
SSH_HOST="${SSH_HOST:-$1}"
SSH_USER="${SSH_USER:-$2}"
SSH_KEY="${SSH_KEY:-$3}"
VIDEO_ID="${4:-2}"

if [ -z "$SSH_HOST" ] || [ -z "$SSH_USER" ]; then
    echo -e "${RED}Error: SSH_HOST y SSH_USER deben estar configurados${NC}"
    echo "Uso: $0 <SSH_HOST> <SSH_USER> [SSH_KEY_PATH] [VIDEO_ID]"
    exit 1
fi

# Configurar SSH
if [ -n "$SSH_KEY" ]; then
    SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=no"
else
    SSH_OPTS="-o StrictHostKeyChecking=no"
fi

echo -e "${YELLOW}=== Verificando credenciales y logs en servidores ===${NC}\n"

# Función para verificar credenciales en un entorno
check_credentials() {
    local env=$1
    local env_dir="~/$env"
    
    echo -e "\n${YELLOW}--- Verificando entorno: $env ---${NC}"
    
    # Verificar si el archivo de credenciales existe
    echo "Verificando archivo de credenciales..."
    CREDS_CHECK=$(ssh $SSH_OPTS $SSH_USER@$SSH_HOST "
        cd $env_dir 2>/dev/null && {
            if [ -f './credentials.json' ]; then
                echo 'EXISTS'
                ls -lh ./credentials.json
                # Verificar que sea un JSON válido
                if python3 -m json.tool ./credentials.json > /dev/null 2>&1; then
                    echo 'VALID_JSON'
                    # Mostrar project_id sin exponer toda la clave
                    python3 -c \"import json; data=json.load(open('./credentials.json')); print('Project ID:', data.get('project_id', 'NOT_FOUND'))\"
                else
                    echo 'INVALID_JSON'
                fi
            else
                echo 'NOT_FOUND'
            fi
        } || echo 'DIR_NOT_FOUND'
    " 2>&1)
    
    if echo "$CREDS_CHECK" | grep -q "EXISTS"; then
        echo -e "${GREEN}✓ Archivo credentials.json existe${NC}"
        if echo "$CREDS_CHECK" | grep -q "VALID_JSON"; then
            echo -e "${GREEN}✓ Archivo JSON válido${NC}"
            echo "$CREDS_CHECK" | grep "Project ID:"
        else
            echo -e "${RED}✗ Archivo JSON inválido${NC}"
        fi
        echo "$CREDS_CHECK" | grep -E "^[^A-Z]" | head -1
    else
        echo -e "${RED}✗ Archivo credentials.json NO encontrado${NC}"
    fi
    
    # Verificar variable de entorno en docker-compose
    echo ""
    echo "Verificando configuración en docker-compose..."
    COMPOSE_CHECK=$(ssh $SSH_OPTS $SSH_USER@$SSH_HOST "
        cd $env_dir 2>/dev/null && {
            if [ -f 'docker-compose.yml' ]; then
                echo 'COMPOSE_EXISTS'
                grep -A 2 'GOOGLE_APPLICATION_CREDENTIALS' docker-compose.yml || echo 'VAR_NOT_FOUND'
                grep -A 2 'credentials.json' docker-compose.yml || echo 'MOUNT_NOT_FOUND'
            else
                echo 'COMPOSE_NOT_FOUND'
            fi
        } || echo 'DIR_NOT_FOUND'
    " 2>&1)
    
    if echo "$COMPOSE_CHECK" | grep -q "COMPOSE_EXISTS"; then
        echo -e "${GREEN}✓ docker-compose.yml existe${NC}"
        if echo "$COMPOSE_CHECK" | grep -q "GOOGLE_APPLICATION_CREDENTIALS"; then
            echo -e "${GREEN}✓ Variable GOOGLE_APPLICATION_CREDENTIALS configurada${NC}"
            echo "$COMPOSE_CHECK" | grep "GOOGLE_APPLICATION_CREDENTIALS" | head -1
        else
            echo -e "${RED}✗ Variable GOOGLE_APPLICATION_CREDENTIALS NO configurada${NC}"
        fi
    else
        echo -e "${RED}✗ docker-compose.yml NO encontrado${NC}"
    fi
    
    # Verificar dentro del contenedor
    echo ""
    echo "Verificando dentro del contenedor Docker..."
    CONTAINER_CHECK=$(ssh $SSH_OPTS $SSH_USER@$SSH_HOST "
        cd $env_dir 2>/dev/null && {
            CONTAINER=\$(docker compose ps -q web 2>/dev/null | head -1)
            if [ -n \"\$CONTAINER\" ]; then
                echo 'CONTAINER_RUNNING'
                docker exec \$CONTAINER sh -c '
                    if [ -f /app/credentials.json ]; then
                        echo \"FILE_EXISTS\"
                        ls -lh /app/credentials.json
                        if [ -n \"\$GOOGLE_APPLICATION_CREDENTIALS\" ]; then
                            echo \"ENV_SET:\$GOOGLE_APPLICATION_CREDENTIALS\"
                        else
                            echo \"ENV_NOT_SET\"
                        fi
                    else
                        echo \"FILE_NOT_FOUND\"
                    fi
                ' 2>&1
            else
                echo 'CONTAINER_NOT_RUNNING'
            fi
        } || echo 'DIR_NOT_FOUND'
    " 2>&1)
    
    if echo "$CONTAINER_CHECK" | grep -q "CONTAINER_RUNNING"; then
        echo -e "${GREEN}✓ Contenedor web está corriendo${NC}"
        if echo "$CONTAINER_CHECK" | grep -q "FILE_EXISTS"; then
            echo -e "${GREEN}✓ Archivo existe dentro del contenedor${NC}"
            echo "$CONTAINER_CHECK" | grep -E "^[^A-Z]" | head -1
            if echo "$CONTAINER_CHECK" | grep -q "ENV_SET"; then
                echo -e "${GREEN}✓ Variable de entorno configurada${NC}"
                echo "$CONTAINER_CHECK" | grep "ENV_SET"
            else
                echo -e "${RED}✗ Variable de entorno NO configurada${NC}"
            fi
        else
            echo -e "${RED}✗ Archivo NO existe dentro del contenedor${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ Contenedor web NO está corriendo${NC}"
    fi
}

# Verificar logs de un video específico
check_video_logs() {
    local env=$1
    local video_id=$2
    local env_dir="~/$env"
    
    echo -e "\n${YELLOW}--- Logs del video $video_id en entorno: $env ---${NC}"
    
    LOGS=$(ssh $SSH_OPTS $SSH_USER@$SSH_HOST "
        cd $env_dir 2>/dev/null && {
            CONTAINER=\$(docker compose ps -q web 2>/dev/null | head -1)
            if [ -n \"\$CONTAINER\" ]; then
                # Buscar logs relacionados con el video
                docker logs \$CONTAINER 2>&1 | grep -i \"video.*$video_id\\|$video_id.*video\" | tail -50
                # También buscar errores relacionados con Veo
                echo '--- Errores relacionados con Veo ---'
                docker logs \$CONTAINER 2>&1 | grep -i \"veo\\|gemini.*veo\\|credentials\\|google.auth\" | tail -30
            else
                echo 'CONTAINER_NOT_RUNNING'
            fi
        } || echo 'DIR_NOT_FOUND'
    " 2>&1)
    
    if echo "$LOGS" | grep -q "CONTAINER_NOT_RUNNING\|DIR_NOT_FOUND"; then
        echo -e "${RED}No se pudieron obtener logs${NC}"
    else
        if [ -z "$LOGS" ] || [ "$LOGS" = "" ]; then
            echo -e "${YELLOW}No se encontraron logs específicos para este video${NC}"
        else
            echo "$LOGS"
        fi
    fi
}

# Verificar en los tres entornos
for env in dev demo prod; do
    check_credentials $env
    
    # Si se especificó un video_id, también revisar logs
    if [ -n "$VIDEO_ID" ] && [ "$VIDEO_ID" != "0" ]; then
        check_video_logs $env $VIDEO_ID
    fi
done

echo -e "\n${YELLOW}=== Verificación completada ===${NC}"





