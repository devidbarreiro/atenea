#!/usr/bin/env bash
# Script para promover código de demo a producción
# Hace merge de demo → main y despliega automáticamente

set -e

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🔄 Promoviendo demo → prod (main)${NC}"

# Verificar que estamos en el repo
if [ ! -d ".git" ]; then
    echo -e "${RED}Error: No estás en un repositorio git${NC}"
    exit 1
fi

# Obtener el nombre del repo remoto
REMOTE_URL=$(git config --get remote.origin.url)
if [[ -z "$REMOTE_URL" ]]; then
    echo -e "${RED}Error: No se encontró el remote origin${NC}"
    exit 1
fi

# Extraer owner/repo de la URL
if [[ $REMOTE_URL =~ github\.com[:/]([^/]+)/([^/]+)\.git ]]; then
    REPO_OWNER="${BASH_REMATCH[1]}"
    REPO_NAME="${BASH_REMATCH[2]%.git}"
else
    echo -e "${RED}Error: No se pudo extraer owner/repo de $REMOTE_URL${NC}"
    exit 1
fi

echo "📥 Actualizando branches..."
git fetch origin

# Verificar que existen los branches
if ! git show-ref --verify --quiet refs/remotes/origin/demo; then
    echo -e "${RED}Error: No existe el branch demo${NC}"
    exit 1
fi

# Cambiar a main y hacer merge
echo "🔀 Haciendo merge de demo → main..."
git checkout main
git pull origin main
git merge origin/demo --no-edit

# Push a main
echo "📤 Haciendo push a main..."
git push origin main

echo -e "${GREEN}✅ Promoción completada. El despliegue a producción se iniciará automáticamente vía GitHub Actions${NC}"
echo -e "${YELLOW}💡 Puedes ver el progreso en: https://github.com/$REPO_OWNER/$REPO_NAME/actions${NC}"

