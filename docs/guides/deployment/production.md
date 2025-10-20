# Despliegue en Producción

> Guía para desplegar Atenea en producción

## Prerequisitos

_TODO: Lista de requisitos_

## Opciones de Deployment

### Cloud Providers
- Google Cloud Platform
- AWS
- Azure
- DigitalOcean

## Pasos Generales

### 1. Configurar Servidor

_TODO: Sistema operativo, dependencias_

### 2. Variables de Entorno

_TODO: Ver environment-vars.md_

### 3. Base de Datos

_TODO: PostgreSQL recomendado_

### 4. GCS Configuration

_TODO: Service account, permisos_

### 5. Web Server

_TODO: Gunicorn + Nginx_

### 6. HTTPS

_TODO: Certbot_

### 7. Monitoreo

_TODO: Logging, metrics_

## Checklist de Seguridad

- [ ] DEBUG=False
- [ ] SECRET_KEY único
- [ ] ALLOWED_HOSTS configurado
- [ ] HTTPS activo
- [ ] API Keys en variables de entorno

## Ver También

- [Docker Deployment](docker.md)
- [Environment Variables](environment-vars.md)

