# 🚀 Guía de Implementación - Mejores Prácticas Django

Esta guía te llevará paso a paso para implementar las mejores prácticas en tu proyecto Atenea.

## 📋 Tabla de Contenidos

1. [Fase 1: Seguridad (URGENTE)](#fase-1-seguridad-urgente)
2. [Fase 2: Arquitectura](#fase-2-arquitectura)
3. [Fase 3: Performance](#fase-3-performance)
4. [Fase 4: Calidad y Testing](#fase-4-calidad-y-testing)

---

## Fase 1: Seguridad (URGENTE) ⚠️

### 1.1. Proteger Credenciales

**Tiempo estimado:** 30 minutos

1. Verificar que `.gitignore` incluya `*.json`:
```bash
# Ya está configurado en tu proyecto
cat .gitignore | grep "*.json"
```

2. Si tienes credenciales commiteadas, eliminarlas del historial:
```bash
# ⚠️ PELIGROSO - Solo si hay credenciales en git
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch *.json" \
  --prune-empty --tag-name-filter cat -- --all
```

3. Mover credenciales a variables de entorno o Secret Manager:
```bash
# Opción 1: Variables de entorno
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# Opción 2: GCP Secret Manager (RECOMENDADO para producción)
gcloud secrets create google-credentials --data-file=credentials.json
```

### 1.2. Cambiar Defaults Inseguros

**Tiempo estimado:** 10 minutos

**Archivo:** `atenea/settings.py`

```python
# ANTES (❌ INSEGURO):
DEBUG = config('DEBUG', default=True, cast=bool)
SECRET_KEY = config('SECRET_KEY', default='django-insecure-x=6fw5...')

# DESPUÉS (✅ SEGURO):
DEBUG = config('DEBUG', default=False, cast=bool)
SECRET_KEY = config('SECRET_KEY')  # Sin default, falla si no está
```

### 1.3. Configurar PostgreSQL

**Tiempo estimado:** 30 minutos

1. Instalar PostgreSQL:
```bash
# macOS
brew install postgresql

# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib

# Windows
# Descargar desde https://www.postgresql.org/download/windows/
```

2. Crear base de datos:
```bash
sudo -u postgres psql
CREATE DATABASE atenea;
CREATE USER atenea_user WITH PASSWORD 'strong_password_here';
ALTER ROLE atenea_user SET client_encoding TO 'utf8';
ALTER ROLE atenea_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE atenea_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE atenea TO atenea_user;
\q
```

3. Actualizar `settings.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='atenea'),
        'USER': config('DB_USER', default='atenea_user'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 600,
    }
}
```

4. Migrar datos (si es necesario):
```bash
# Exportar de SQLite
python manage.py dumpdata --natural-foreign --natural-primary > data.json

# Cambiar a PostgreSQL en settings

# Aplicar migraciones
python manage.py migrate

# Importar datos
python manage.py loaddata data.json
```

### 1.4. Implementar Autenticación

**Tiempo estimado:** 2-3 horas

1. Crear app de autenticación:
```bash
python manage.py startapp accounts
```

2. Agregar a `INSTALLED_APPS`:
```python
INSTALLED_APPS = [
    # ...
    'accounts',
]
```

3. Crear modelo de usuario personalizado (opcional pero recomendado):
```python
# accounts/models.py
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    # Agregar campos adicionales si es necesario
    pass
```

4. Agregar autenticación a views:
```python
# ANTES:
def dashboard(request):
    projects = Project.objects.all()
    # ...

# DESPUÉS:
from django.contrib.auth.decorators import login_required

@login_required
def dashboard(request):
    # Filtrar por usuario cuando se implemente multi-tenant
    projects = Project.objects.all()
    # ...
```

5. O mejor aún, usa las vistas de autenticación de Django:
```python
# atenea/urls.py
from django.contrib.auth import views as auth_views

urlpatterns = [
    # ...
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
]
```

### 1.5. Configurar Settings de Seguridad

**Tiempo estimado:** 15 minutos

**Archivo:** `atenea/settings.py`

```python
# Solo en producción (agregar al final)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
```

---

## Fase 2: Arquitectura

### 2.1. Crear Django Forms

**Tiempo estimado:** 3-4 horas

Usa los ejemplos de `examples/forms_example.py`:

1. Crear archivo `core/forms.py`
2. Copiar los forms de ejemplo
3. Adaptar según tus necesidades
4. Integrar en views

```python
# core/forms.py
from django import forms
from .models import Video

class VideoBaseForm(forms.ModelForm):
    class Meta:
        model = Video
        fields = ['title', 'script', 'type']
    
    def clean_script(self):
        script = self.cleaned_data.get('script')
        if len(script) < 10:
            raise forms.ValidationError('Script muy corto')
        return script
```

### 2.2. Crear Capa de Servicios

**Tiempo estimado:** 4-6 horas

1. Crear archivo `core/services.py`
2. Copiar de `examples/services_example.py`
3. Mover lógica de views a servicios

```python
# core/services.py
class VideoService:
    def create_video(self, project, title, video_type, script, config):
        """Toda la lógica de creación aquí"""
        pass
```

### 2.3. Refactorizar a Class-Based Views

**Tiempo estimado:** 6-8 horas

1. Revisar `examples/views_cbv_example.py`
2. Crear `core/views_cbv.py`
3. Migrar views una por una
4. Actualizar `urls.py`

**Estrategia recomendada:**
- Empezar con las views más simples (list, detail)
- Continuar con create, update, delete
- Dejar las views complejas para el final

### 2.4. Agregar Índices a Modelos

**Tiempo estimado:** 30 minutos

```python
# core/models.py
class Video(models.Model):
    # ... campos existentes ...
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['external_id']),
            models.Index(fields=['project', 'status']),
        ]
```

Después crear y aplicar migración:
```bash
python manage.py makemigrations
python manage.py migrate
```

---

## Fase 3: Performance

### 3.1. Instalar y Configurar Redis

**Tiempo estimado:** 1 hora

1. Instalar Redis:
```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis

# Docker
docker run -d -p 6379:6379 redis
```

2. Instalar cliente Python:
```bash
pip install redis django-redis
```

3. Configurar en `settings.py`:
```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/0',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'atenea',
        'TIMEOUT': 300,
    }
}
```

4. Usar caché en views:
```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 5)  # 5 minutos
def api_list_avatars(request):
    # ...
```

### 3.2. Implementar Celery

**Tiempo estimado:** 3-4 horas

1. Instalar Celery:
```bash
pip install celery redis django-celery-beat django-celery-results
```

2. Crear `atenea/celery.py`:
```python
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'atenea.settings')

app = Celery('atenea')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

3. Modificar `atenea/__init__.py`:
```python
from .celery import app as celery_app

__all__ = ('celery_app',)
```

4. Configurar en `settings.py`:
```python
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
```

5. Crear tasks en `core/tasks.py` (ver `examples/celery_example.py`)

6. Ejecutar Celery:
```bash
# Worker
celery -A atenea worker -l info

# Beat (tareas programadas)
celery -A atenea beat -l info

# Ambos
celery -A atenea worker -B -l info
```

### 3.3. Optimizar Queries

**Tiempo estimado:** 2 horas

Revisar todas las consultas y optimizar:

```python
# ANTES (N+1 query):
projects = Project.objects.all()
for project in projects:
    print(project.videos.count())  # ❌ Query por cada proyecto

# DESPUÉS:
from django.db.models import Count

projects = Project.objects.annotate(
    video_count=Count('videos')
)
for project in projects:
    print(project.video_count)  # ✅ Un solo query
```

---

## Fase 4: Calidad y Testing

### 4.1. Escribir Tests

**Tiempo estimado:** 8-12 horas (ongoing)

1. Crear estructura de tests:
```bash
mkdir -p core/tests
touch core/tests/__init__.py
touch core/tests/test_models.py
touch core/tests/test_views.py
touch core/tests/test_services.py
```

2. Copiar ejemplos de `examples/tests_example.py`

3. Ejecutar tests:
```bash
python manage.py test

# Con coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
```

### 4.2. Configurar CI/CD

**Tiempo estimado:** 2-3 horas

**GitHub Actions** (`.github/workflows/django.yml`):
```yaml
name: Django CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run tests
      env:
        DB_NAME: test_db
        DB_USER: postgres
        DB_PASSWORD: postgres
        DB_HOST: localhost
        SECRET_KEY: test-secret-key
      run: |
        python manage.py test
```

### 4.3. Configurar Sentry

**Tiempo estimado:** 30 minutos

1. Crear cuenta en [Sentry.io](https://sentry.io)

2. Instalar SDK:
```bash
pip install sentry-sdk
```

3. Configurar en `settings.py`:
```python
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

if not DEBUG:
    sentry_sdk.init(
        dsn=config('SENTRY_DSN'),
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=True,
    )
```

---

## 📊 Checklist Completo

### Seguridad
- [ ] Credenciales movidas a variables de entorno
- [ ] DEBUG=False por defecto
- [ ] SECRET_KEY sin default
- [ ] PostgreSQL configurado
- [ ] Autenticación implementada
- [ ] HTTPS/SSL configurado (producción)
- [ ] ALLOWED_HOSTS configurado

### Arquitectura
- [ ] Django Forms creados
- [ ] Capa de servicios implementada
- [ ] Class-Based Views migradas
- [ ] Índices agregados a modelos
- [ ] URLs usando reverse()

### Performance
- [ ] Redis configurado
- [ ] Caché implementado
- [ ] Celery configurado
- [ ] Queries optimizados (select_related, prefetch_related)
- [ ] Paginación agregada

### Calidad
- [ ] Tests unitarios escritos
- [ ] Tests de integración escritos
- [ ] Coverage > 70%
- [ ] CI/CD configurado
- [ ] Linter configurado (flake8, black)
- [ ] Pre-commit hooks

### Monitoreo
- [ ] Sentry configurado
- [ ] Logging mejorado
- [ ] Métricas configuradas

### Documentación
- [ ] README actualizado
- [ ] API documentada
- [ ] Decisiones arquitectónicas documentadas

---

## 🎯 Prioridades Sugeridas

### Esta Semana (CRÍTICO)
1. ✅ Proteger credenciales
2. ✅ Cambiar DEBUG y SECRET_KEY defaults
3. ✅ Configurar PostgreSQL
4. ⏳ Implementar autenticación básica

### Próximas 2 Semanas
5. Django Forms
6. Capa de servicios
7. Tests básicos
8. Redis + Caché

### Mes 1
9. Celery para tareas asíncronas
10. Class-Based Views
11. CI/CD
12. Sentry

### Mes 2
13. Optimizaciones de performance
14. Tests de integración completos
15. Monitoreo avanzado
16. Documentación completa

---

## 🆘 Ayuda y Soporte

Si tienes dudas sobre alguna implementación:

1. Revisa los archivos de ejemplo en `examples/`
2. Consulta la documentación oficial de Django
3. Abre un issue en el proyecto

**Archivos de Referencia:**
- `examples/forms_example.py` - Forms completos
- `examples/services_example.py` - Service layer
- `examples/views_cbv_example.py` - Class-Based Views
- `examples/settings_production_example.py` - Settings para producción
- `examples/tests_example.py` - Tests completos
- `examples/celery_example.py` - Tareas asíncronas

---

## 📚 Recursos Adicionales

- [Django Documentation](https://docs.djangoproject.com/)
- [Two Scoops of Django](https://www.feldroy.com/books/two-scoops-of-django-3-x)
- [Django Best Practices](https://django-best-practices.readthedocs.io/)
- [Awesome Django](https://github.com/wsvincent/awesome-django)

---

¡Mucho éxito con la implementación! 🚀

