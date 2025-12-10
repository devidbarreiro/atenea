# Guía de Configuración de Deploys

Esta guía explica cómo configurar correctamente los archivos `.env` para cada entorno y cómo funciona el flujo de deploy automático.

## Estructura de Directorios en el Servidor

```
~/dev/html/          # Código y .env para DEV
~/demo/html/         # Código y .env para DEMO  
~/prod/html/         # Código y .env para PROD
```

**IMPORTANTE:** Cada entorno debe tener su propio `.env` en `~/ENV/html/.env` (donde ENV es dev, demo o prod).

### Templates de Ejemplo

En el repositorio encontrarás templates de ejemplo para cada entorno:
- `env.dev.example` → Usar como referencia para `~/dev/html/.env`
- `env.demo.example` → Usar como referencia para `~/demo/html/.env`
- `env.prod.example` → Usar como referencia para `~/prod/html/.env`

Estos archivos NO contienen valores reales, solo la estructura y comentarios explicativos.

## Flujo de Deploy Automático

El deploy se ejecuta automáticamente cuando haces push a las siguientes ramas:

- **Push a `dev`** → Deploy automático a DEV
- **Push a `demo`** → Deploy automático a DEMO
- **Push a `main`** → Deploy automático a PROD

### Proceso de Deploy

1. **Tests**: Se ejecutan tests automáticamente
2. **Copia de código**: El código se copia al servidor usando rsync
3. **Validación**: Se verifica que existe `.env` en `~/ENV/html/.env`
4. **Configuración automática**: Se ajustan variables si es necesario:
   - `USE_SQLITE=False` (todos los entornos usan PostgreSQL)
   - `CELERY_BROKER_URL=redis://redis:6379/0`
   - `CELERY_RESULT_BACKEND=redis://redis:6379/0`
   - `CHANNEL_REDIS_URL=redis://redis:6379/1`
   - `DATABASE_URL` se genera automáticamente si no existe
5. **Limpieza**: Se detienen y eliminan contenedores antiguos
6. **Build**: Se construyen nuevas imágenes Docker
7. **Start**: Se inician los servicios (web, db, redis, celery_worker, celery_beat)
8. **Migraciones**: Se ejecutan migraciones de Django automáticamente
9. **Static files**: Se recolectan archivos estáticos
10. **Verificación**: Se verifica que todos los servicios están funcionando

## Variables Requeridas en .env

### Variables Críticas (Obligatorias)

```bash
SECRET_KEY=tu-secret-key-aqui
POSTGRES_PASSWORD=tu-password-segura
POSTGRES_USER=atenea_dev  # o atenea_demo, atenea_prod
POSTGRES_DB=atenea_dev    # o atenea_demo, atenea_prod
GCS_BUCKET_NAME=tu-bucket-name
GCS_PROJECT_ID=tu-project-id
```

### Variables Recomendadas (Se configuran automáticamente si faltan)

```bash
USE_SQLITE=False
DATABASE_URL=postgresql://USER:PASSWORD@db:5432/DB_NAME
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
CHANNEL_REDIS_URL=redis://redis:6379/1
DEBUG=True  # False para prod
```

### Variables Opcionales (API Keys, etc.)

```bash
HEYGEN_API_KEY=...
OPENAI_API_KEY=...
GEMINI_API_KEY=...
ELEVENLABS_API_KEY=...
# ... otras API keys
```

## Configuración por Entorno

### DEV (`~/dev/html/.env`)

```bash
SECRET_KEY=...
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,dev.atenea.nxhumans.com
USE_SQLITE=False
POSTGRES_USER=atenea_dev
POSTGRES_DB=atenea_dev
POSTGRES_PASSWORD=...
DATABASE_URL=postgresql://atenea_dev:PASSWORD@db:5432/atenea_dev
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
CHANNEL_REDIS_URL=redis://redis:6379/1
GCS_BUCKET_NAME=...
GCS_PROJECT_ID=...
```

### DEMO (`~/demo/html/.env`)

```bash
SECRET_KEY=...
DEBUG=True  # Puede ser False
ALLOWED_HOSTS=localhost,127.0.0.1,demo.atenea.nxhumans.com
USE_SQLITE=False
POSTGRES_USER=atenea_demo
POSTGRES_DB=atenea_demo
POSTGRES_PASSWORD=...
DATABASE_URL=postgresql://atenea_demo:PASSWORD@db:5432/atenea_demo
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
CHANNEL_REDIS_URL=redis://redis:6379/1
GCS_BUCKET_NAME=...
GCS_PROJECT_ID=...
```

### PROD (`~/prod/html/.env`)

```bash
SECRET_KEY=...  # DEBE SER FUERTE Y SEGURO
DEBUG=False     # CRÍTICO: Nunca True en producción
ALLOWED_HOSTS=localhost,127.0.0.1,atenea.nxhumans.com
USE_SQLITE=False
POSTGRES_USER=atenea_prod
POSTGRES_DB=atenea_prod
POSTGRES_PASSWORD=...  # DEBE SER MUY SEGURA
DATABASE_URL=postgresql://atenea_prod:PASSWORD@db:5432/atenea_prod
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
CHANNEL_REDIS_URL=redis://redis:6379/1
GCS_BUCKET_NAME=...
GCS_PROJECT_ID=...
```

## Credentials.json

Además del `.env`, cada entorno necesita `credentials.json` para Google Cloud Storage:

- `~/dev/html/credentials.json`
- `~/demo/html/credentials.json`
- `~/prod/html/credentials.json`

Este archivo NO se copia durante el deploy (por seguridad), debe estar en el servidor manualmente.

## Validación Antes del Deploy

Puedes validar tu `.env` antes del deploy usando el script:

```bash
./scripts/validate-env.sh dev ~/dev/html/.env
./scripts/validate-env.sh demo ~/demo/html/.env
./scripts/validate-env.sh prod ~/prod/html/.env
```

## Solución de Problemas

### El deploy falla porque falta .env

**Solución:** Asegúrate de que existe `~/ENV/html/.env` en el servidor antes del deploy.

### El deploy falla porque falta credentials.json

**Solución:** Copia `credentials.json` a `~/ENV/html/credentials.json` en el servidor.

### Los contenedores no se levantan

**Solución:** 
1. Verifica los logs: `cd ~/ENV/html && docker compose logs`
2. Verifica que el `.env` tiene todas las variables requeridas
3. Verifica que `credentials.json` existe

### Redis/Celery no funciona

**Solución:** Asegúrate de que en el `.env`:
- `CELERY_BROKER_URL=redis://redis:6379/0` (no `localhost`)
- `CELERY_RESULT_BACKEND=redis://redis:6379/0` (no `localhost`)
- `CHANNEL_REDIS_URL=redis://redis:6379/1` (no `localhost`)

### Las migraciones fallan

**Solución:**
1. Verifica que PostgreSQL está corriendo: `docker compose ps`
2. Verifica que `DATABASE_URL` está correctamente configurado
3. Verifica que `POSTGRES_PASSWORD` coincide con la contraseña de la BD existente

## Comandos Útiles

```bash
# Ver estado de contenedores
cd ~/dev/html && docker compose ps

# Ver logs
cd ~/dev/html && docker compose logs -f

# Ver logs de un servicio específico
cd ~/dev/html && docker compose logs -f web
cd ~/dev/html && docker compose logs -f celery_worker

# Reiniciar un servicio
cd ~/dev/html && docker compose restart web

# Ejecutar migraciones manualmente
cd ~/dev/html && docker compose run --rm migrate

# Recolectar archivos estáticos manualmente
cd ~/dev/html && docker compose run --rm collectstatic
```
