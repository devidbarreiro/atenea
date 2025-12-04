# Guía de Despliegue - Atenea

## 📋 Resumen Rápido

- **`dev`** → Despliega automáticamente a **DEV** (puerto 8080)
- **`demo`** → Despliega automáticamente a **DEMO** (puerto 8081)  
- **`main`** → Despliega automáticamente a **PROD** (puerto 8082)

**URLs:**
- Dev: `http://5.196.245.4:8080` o `https://dev.atenea.nxhumans.com`
- Demo: `http://5.196.245.4:8081` o `https://demo.atenea.nxhumans.com`
- Prod: `http://5.196.245.4:8082` o `https://atenea.nxhumans.com`

---

## 🔄 Flujo de Trabajo Semanal

### Lunes - Jueves (Desarrollo)

**Para desarrolladores:**
```bash
# Crear feature branch desde dev
git checkout dev
git pull origin dev
git checkout -b feature/nueva-funcionalidad

# Trabajar en la feature
# ... hacer cambios ...
git add .
git commit -m "feat: nueva funcionalidad"
git push origin feature/nueva-funcionalidad

# Crear PR en GitHub: feature/nueva-funcionalidad → dev
```

**Para maintainers (después de revisar PRs):**
```bash
# Merge del PR en GitHub (o manualmente)
git checkout dev
git pull origin dev
# El despliegue a DEV es automático
```
✅ **Automático:** GitHub Actions despliega a DEV después del merge

### Viernes (Demo para Clientes)
```bash
# Promover dev → demo
git checkout demo
git merge dev
git push origin demo
```
✅ **Automático:** GitHub Actions despliega a DEMO

### Después de Validar Demo (Producción)
```bash
# Promover demo → main
git checkout main
git merge demo
git push origin main
```
✅ **Automático:** GitHub Actions despliega a PROD

---

## 🗄️ Bases de Datos

**Cada entorno tiene su propia base de datos PostgreSQL:**

- **DEV:** `atenea_dev` (puerto 8080)
- **DEMO:** `atenea_demo` (puerto 8081)
- **PROD:** `atenea_prod` (puerto 8082)

**Acceso a las bases de datos:**
```bash
# Conectarse al servidor
ssh atenea-ovh

# Acceder a la base de datos de DEV
cd ~/dev
docker compose exec db psql -U atenea -d atenea_dev

# Acceder a la base de datos de DEMO
cd ~/demo
docker compose exec db psql -U atenea -d atenea_demo

# Acceder a la base de datos de PROD
cd ~/prod
docker compose exec db psql -U atenea -d atenea_prod
```

**⚠️ Importante:** Los datos NO se comparten entre entornos. Cada uno es independiente.

---

## 🛠️ Tareas Administrativas

### Añadir Créditos a Usuarios

**Opción 1: Desde tu ordenador local (recomendado)**

```bash
# DEV - Añadir créditos
docker exec dev-web-1 python manage.py add_credits <username> <cantidad> --description "Descripción"

# DEMO - Añadir créditos
docker exec demo-web-1 python manage.py add_credits <username> <cantidad> --description "Descripción"

# PROD - Añadir créditos
docker exec prod-web-1 python manage.py add_credits <username> <cantidad> --description "Descripción"

# Ejemplo: añadir 100,000 créditos al usuario "admin" en dev
docker exec dev-web-1 python manage.py add_credits admin 100000 --description "Asignación inicial de créditos"
```

**Opción 2: Desde el servidor directamente**

```bash
# Conectarse al servidor
ssh atenea-ovh

# Ir al entorno deseado
cd ~/dev  # o ~/demo o ~/prod

# Ejecutar el comando
docker compose exec web python manage.py add_credits <username> <cantidad> --description "Descripción"

# Ejemplo
docker compose exec web python manage.py add_credits admin 100000 --description "Asignación inicial"
```

**Opción 3: Desde tu ordenador usando SSH (sin conectarte al servidor)**

```bash
# Ejecutar comando directamente vía SSH
ssh atenea-ovh "cd ~/dev && docker compose exec web python manage.py add_credits <username> <cantidad> --description 'Descripción'"

# Ejemplo
ssh atenea-ovh "cd ~/dev && docker compose exec web python manage.py add_credits admin 100000 --description 'Asignación inicial'"
```

### Establecer Límite Mensual

**Desde tu ordenador:**
```bash
# DEV
docker exec dev-web-1 python manage.py set_monthly_limit <username> <límite> --description "Descripción"

# DEMO
docker exec demo-web-1 python manage.py set_monthly_limit <username> <límite> --description "Descripción"

# PROD
docker exec prod-web-1 python manage.py set_monthly_limit <username> <límite> --description "Descripción"

# Ejemplo: establecer límite de 100,000 créditos mensuales
docker exec dev-web-1 python manage.py set_monthly_limit admin 100000 --description "Límite mensual"
```

**Desde el servidor:**
```bash
ssh atenea-ovh
cd ~/dev  # o ~/demo o ~/prod
docker compose exec web python manage.py set_monthly_limit <username> <límite> --description "Descripción"
```

### Ver Créditos de un Usuario

**Desde tu ordenador:**
```bash
# DEV
docker exec dev-web-1 python manage.py show_user_credits <username>

# DEMO
docker exec demo-web-1 python manage.py show_user_credits <username>

# PROD
docker exec prod-web-1 python manage.py show_user_credits <username>

# Ejemplo
docker exec dev-web-1 python manage.py show_user_credits admin
```

**Desde el servidor:**
```bash
ssh atenea-ovh
cd ~/dev  # o ~/demo o ~/prod
docker compose exec web python manage.py show_user_credits <username>
```

### Otros Comandos Útiles

**Listar todos los usuarios con créditos:**
```bash
# Desde tu ordenador
docker exec dev-web-1 python manage.py list_users_credits
docker exec demo-web-1 python manage.py list_users_credits
docker exec prod-web-1 python manage.py list_users_credits

# Desde el servidor
ssh atenea-ovh
cd ~/dev && docker compose exec web python manage.py list_users_credits
```

**Ver estadísticas de créditos:**
```bash
# Desde tu ordenador
docker exec dev-web-1 python manage.py stats_credits

# Desde el servidor
ssh atenea-ovh
cd ~/dev && docker compose exec web python manage.py stats_credits
```

**Resetear créditos mensuales (ejecutar el 1 de cada mes):**
```bash
# Desde tu ordenador
docker exec dev-web-1 python manage.py reset_monthly_credits
docker exec demo-web-1 python manage.py reset_monthly_credits
docker exec prod-web-1 python manage.py reset_monthly_credits

# Desde el servidor
ssh atenea-ovh
cd ~/dev && docker compose exec web python manage.py reset_monthly_credits
```

### Cargar Prompt Templates

**Cargar o actualizar prompt templates desde archivos Markdown:**

**Opción 1: Desde el servidor directamente (recomendado)**

```bash
# Conectarse al servidor
ssh atenea-ovh

# Ir al entorno deseado
cd ~/dev/html  # o ~/demo/html o ~/prod/html

# Cargar templates (solo crea nuevos)
docker compose exec web python manage.py load_default_prompt_templates

# Actualizar templates existentes (incluyendo preview_url)
docker compose exec web python manage.py load_default_prompt_templates --update
```

**Opción 2: Desde tu ordenador usando SSH**

```bash
# DEV - Cargar templates
ssh atenea-ovh "cd ~/dev/html && docker compose exec web python manage.py load_default_prompt_templates --update"

# DEMO - Cargar templates
ssh atenea-ovh "cd ~/demo/html && docker compose exec web python manage.py load_default_prompt_templates --update"

# PROD - Cargar templates
ssh atenea-ovh "cd ~/prod/html && docker compose exec web python manage.py load_default_prompt_templates --update"
```

**Opción 3: Desde tu ordenador usando docker exec**

```bash
# DEV
docker exec dev-web-1 python manage.py load_default_prompt_templates --update

# DEMO
docker exec demo-web-1 python manage.py load_default_prompt_templates --update

# PROD
docker exec prod-web-1 python manage.py load_default_prompt_templates --update
```

**⚠️ Nota importante:**
- El comando lee los archivos `.md` de `core/prompt_templates/default/`
- Con `--update` actualiza templates existentes (incluyendo `preview_url` si cambió)
- Sin `--update` solo crea templates nuevos (no actualiza existentes)
- Los templates se marcan como públicos y activos automáticamente

### Ejemplo Completo: Configurar Usuario Nuevo

**Desde tu ordenador:**
```bash
# 1. Agregar 100,000 créditos
docker exec dev-web-1 python manage.py add_credits nuevo_usuario 100000 --description "Asignación inicial de créditos"

# 2. Establecer límite mensual de 100,000
docker exec dev-web-1 python manage.py set_monthly_limit nuevo_usuario 100000 --description "Límite mensual"

# 3. Verificar
docker exec dev-web-1 python manage.py show_user_credits nuevo_usuario
```

**Desde el servidor:**
```bash
ssh atenea-ovh
cd ~/dev

# 1. Agregar créditos
docker compose exec web python manage.py add_credits nuevo_usuario 100000 --description "Asignación inicial"

# 2. Establecer límite
docker compose exec web python manage.py set_monthly_limit nuevo_usuario 100000 --description "Límite mensual"

# 3. Verificar
docker compose exec web python manage.py show_user_credits nuevo_usuario
```

### ⚠️ Nota Importante

**Nombres de contenedores:**
- **DEV:** `dev-web-1`
- **DEMO:** `demo-web-1`
- **PROD:** `prod-web-1`

Si no estás seguro del nombre exacto del contenedor, puedes verificar:
```bash
# Desde tu ordenador
ssh atenea-ovh "docker ps | grep -E '(dev|demo|prod)-web'"

# O desde el servidor
docker ps | grep web
```

---

## 👨‍💻 Flujo de Trabajo para Desarrolladores

### Crear una Feature Branch

**Los desarrolladores siempre crean branches desde `dev` y hacen PRs a `dev`:**

```bash
# 1. Asegurarse de estar en dev y actualizado
git checkout dev
git pull origin dev

# 2. Crear nueva branch de feature
git checkout -b feature/skeletons

# 3. Trabajar en la feature
# ... hacer cambios ...
git add .
git commit -m "feat: implementar skeletons"

# 4. Push de la branch
git push origin feature/skeletons
```

### Crear Pull Request

1. **Ir a GitHub** → Repositorio → "Pull requests" → "New pull request"
2. **Base:** `dev` (siempre)
3. **Compare:** `feature/skeletons` (tu branch)
4. **Título y descripción** del PR
5. **Crear el PR**

### ⚠️ Regla Importante

**TODOS los PRs de desarrolladores van a `dev`, NUNCA directamente a `demo` o `main`**

- ✅ `feature/xxx` → PR a `dev`
- ✅ `fix/xxx` → PR a `dev`
- ✅ `hotfix/xxx` → PR a `dev`
- ❌ NUNCA PRs directos a `demo` o `main`

---

## 📝 Revisar PRs y Hacer Merges (Para Maintainers)

### Proceso de Revisión

1. **Revisar el PR en GitHub**
   - Ver los cambios
   - Comentar si hay problemas
   - Aprobar si está bien

2. **Hacer Merge en GitHub**
   - Click en "Merge pull request"
   - Confirmar el merge
   - **El despliegue a DEV es automático** después del merge

3. **Opcional: Merge Manual (si GitHub no permite auto-merge)**
   ```bash
   # Desde tu ordenador
   git checkout dev
   git pull origin dev
   git merge origin/feature/skeletons
   git push origin dev
   ```

### Después del Merge

- ✅ **Automático:** GitHub Actions despliega a DEV
- ✅ **Verificar:** Ir a http://5.196.245.4:8080 para probar
- ✅ **Si está bien:** Promover a demo el viernes
- ❌ **Si hay problemas:** Revertir el merge o hacer hotfix

---

## 🚀 Despliegue Manual (si es necesario)

Si necesitas desplegar manualmente sin hacer push:

```bash
# Desde tu ordenador local
./scripts/deploy-to-server.sh dev    # Despliega a dev
./scripts/deploy-to-server.sh demo   # Despliega a demo
./scripts/deploy-to-server.sh prod  # Despliega a prod
```

**Requisitos:**
- Tener la clave SSH en `~/.ssh/atenea_ovh_key`
- O configurar `SSH_KEY` como variable de entorno

---

## 🔍 Verificar Estado de los Entornos

### Ver logs en tiempo real
```bash
ssh atenea-ovh

# Logs de DEV
cd ~/dev && docker compose logs -f web

# Logs de DEMO
cd ~/demo && docker compose logs -f web

# Logs de PROD
cd ~/prod && docker compose logs -f web
```

### Ver estado de contenedores
```bash
ssh atenea-ovh

# Estado de todos los entornos
docker ps | grep -E '(dev|demo|prod)'

# Estado específico
cd ~/dev && docker compose ps
```

### Verificar que las apps responden
```bash
# Desde tu ordenador
curl http://5.196.245.4:8080  # Dev
curl http://5.196.245.4:8081  # Demo
curl http://5.196.245.4:8082  # Prod
```

---

## 🐛 Troubleshooting Común

### Error: "DisallowedHost"
**Solución:** Verificar que `ALLOWED_HOSTS` en el `.env` incluya la IP o dominio:
```bash
ssh atenea-ovh
cd ~/dev  # o demo/prod
grep ALLOWED_HOSTS .env
# Debe incluir: localhost,127.0.0.1,5.196.245.4,dev.atenea.nxhumans.com
```

### Error: "Port already allocated"
**Solución:** Hay un contenedor viejo usando el puerto
```bash
ssh atenea-ovh
docker ps -a | grep <puerto>
docker stop <container-id>
docker rm <container-id>
cd ~/<env> && docker compose up -d
```

### Error: "Database is uninitialized"
**Solución:** Verificar que `POSTGRES_PASSWORD` esté en el `.env`
```bash
ssh atenea-ovh
cd ~/dev  # o demo/prod
grep POSTGRES_PASSWORD .env
# Debe tener un valor (no vacío)
```

### Reiniciar un entorno completo
```bash
ssh atenea-ovh
cd ~/dev  # o demo/prod
docker compose down
docker compose up -d
```

---

## 📁 Estructura en el Servidor

```
/home/ubuntu/
├── dev/
│   ├── .env              # Variables de entorno para DEV
│   ├── docker-compose.yml # Copia de docker/docker-compose.dev.yml
│   ├── credentials.json   # Credenciales de Google Cloud Storage
│   ├── html/             # Código de la aplicación
│   └── backups/          # Backups de la base de datos
├── demo/
│   ├── .env
│   ├── docker-compose.yml
│   ├── credentials.json   # Credenciales de Google Cloud Storage
│   ├── html/
│   └── backups/
└── prod/
    ├── .env
    ├── docker-compose.yml
    ├── credentials.json   # Credenciales de Google Cloud Storage
    ├── html/
    └── backups/
```

### 📄 Archivo credentials.json

**Ubicación:** Debe estar en el directorio raíz de cada entorno:
- `~/dev/credentials.json`
- `~/demo/credentials.json`
- `~/prod/credentials.json`

**Cómo copiarlo:**
```bash
# Desde tu ordenador local
scp -i ~/.ssh/atenea_ovh_key credentials.json atenea-ovh:~/dev/credentials.json
scp -i ~/.ssh/atenea_ovh_key credentials.json atenea-ovh:~/demo/credentials.json
scp -i ~/.ssh/atenea_ovh_key credentials.json atenea-ovh:~/prod/credentials.json
```

**⚠️ Importante:**
- El archivo se monta como volumen de solo lectura (`:ro`) en `/app/credentials.json` dentro del contenedor
- Si cambias el archivo, necesitas reiniciar el contenedor: `docker compose restart web`
- Puedes usar una ruta diferente configurando `GCS_CREDENTIALS_PATH` en el `.env`

---

## 🔐 Variables de Entorno Importantes

Cada entorno tiene su `.env` con:

**Obligatorias para Docker Compose:**
```bash
POSTGRES_DB=atenea_dev      # o atenea_demo o atenea_prod
POSTGRES_USER=atenea
POSTGRES_PASSWORD=<password>
```

**Obligatorias para Django:**
```bash
SECRET_KEY=<django-secret-key>
DEBUG=True                  # False en prod
ALLOWED_HOSTS=localhost,127.0.0.1,5.196.245.4,dev.atenea.nxhumans.com
```

**Para la aplicación:**
```bash
DATABASE_URL=postgresql://atenea:<password>@db:5432/atenea_dev
GCS_BUCKET_NAME=<bucket>
GCS_PROJECT_ID=<project>
HEYGEN_API_KEY=<key>
GEMINI_API_KEY=<key>
# ... otras API keys
```

---

## ⚡ Comandos Rápidos de Referencia

```bash
# Conectarse al servidor
ssh atenea-ovh

# Ver logs de un entorno
cd ~/dev && docker compose logs -f web

# Ejecutar migraciones
cd ~/dev && docker compose run --rm migrate

# Recolectar archivos estáticos
cd ~/dev && docker compose run --rm collectstatic

# Reiniciar un entorno
cd ~/dev && docker compose restart

# Ver estado
cd ~/dev && docker compose ps

# Acceder a la shell de Django
cd ~/dev && docker compose exec web python manage.py shell

# Ver créditos de usuario
cd ~/dev && docker compose exec web python manage.py show_user_credits <username>

# Cargar prompt templates
cd ~/dev/html && docker compose exec web python manage.py load_default_prompt_templates --update
```

---

## 📞 Acceso SSH

**Configuración en `~/.ssh/config`:**
```
Host atenea-ovh
    HostName 5.196.245.4
    User ubuntu
    IdentityFile ~/.ssh/atenea_ovh_key
    StrictHostKeyChecking no
```

**Uso:**
```bash
ssh atenea-ovh
```

---

## 🔄 GitHub Actions

El workflow `.github/workflows/deploy.yml` se ejecuta automáticamente en:
- Push a `dev` → Despliega a DEV
- Push a `demo` → Despliega a DEMO
- Push a `main` → Despliega a PROD

**Ver estado de despliegues:**
- Ve a: https://github.com/devidbarreiro/atenea/actions

---

## ⚠️ Notas Importantes

1. **Nunca hagas cambios directamente en `main`** - siempre desde `dev` → `demo` → `main`

2. **Cada entorno es independiente** - cambios en dev NO afectan a demo o prod

3. **Las bases de datos son separadas** - no hay sincronización automática

4. **Los `.env` NO están en git** - se configuran manualmente en el servidor

5. **Backups:** Se guardan en `~/<env>/backups/` (configurar cron si es necesario)

---

## 📚 Más Información

- **Docker Compose files:** `docker/docker-compose.{dev,demo,prod}.yml`
- **Scripts de despliegue:** `scripts/deploy-to-server.sh`
- **GitHub Actions:** `.github/workflows/deploy.yml`

