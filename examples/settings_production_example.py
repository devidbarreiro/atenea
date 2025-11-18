"""
EJEMPLO: Settings para Producción - Mejores Prácticas
======================================================

Archivo: atenea/settings_production.py
Uso: Importar este archivo en settings.py según el entorno
"""

from pathlib import Path
import os
from decouple import config
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

BASE_DIR = Path(__file__).resolve().parent.parent

# ====================
# SEGURIDAD
# ====================

# SECRET_KEY sin default - falla si no está configurado
SECRET_KEY = config('SECRET_KEY')

# DEBUG siempre False en producción
DEBUG = False

# ALLOWED_HOSTS desde variable de entorno
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

# HTTPS/SSL Settings
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=True, cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=True, cast=bool)

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True, cast=bool)
SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=True, cast=bool)

# Security Headers
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# ====================
# APLICACIONES
# ====================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'corsheaders',
    'django_celery_beat',
    'django_celery_results',
    
    # Local apps
    'core.apps.CoreConfig',
]

# ====================
# MIDDLEWARE
# ====================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Servir archivos estáticos
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ====================
# BASE DE DATOS
# ====================

DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE', default='django.db.backends.postgresql'),
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', default='5432'),
        'CONN_MAX_AGE': config('DB_CONN_MAX_AGE', default=600, cast=int),
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}

# ====================
# CACHÉ (Redis)
# ====================

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            }
        },
        'KEY_PREFIX': 'atenea',
        'TIMEOUT': 300,  # 5 minutos por defecto
    }
}

# Session con Redis
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# ====================
# CELERY
# ====================

CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutos
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutos

# ====================
# CORS
# ====================

CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='',
    cast=lambda v: [s.strip() for s in v.split(',') if s]
)

CORS_ALLOW_CREDENTIALS = True

# ====================
# ARCHIVOS ESTÁTICOS
# ====================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# WhiteNoise para servir archivos estáticos eficientemente
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ====================
# GOOGLE CLOUD STORAGE
# ====================

GCS_BUCKET_NAME = config('GCS_BUCKET_NAME')
GCS_PROJECT_ID = config('GCS_PROJECT_ID')

# En producción, usar Workload Identity o service account automático
# NO usar GOOGLE_APPLICATION_CREDENTIALS en producción
# Las credenciales se obtienen automáticamente de los metadatos de GCP

# ====================
# API KEYS
# ====================

HEYGEN_API_KEY = config('HEYGEN_API_KEY')
GEMINI_API_KEY = config('GEMINI_API_KEY')

# ====================
# LOGGING
# ====================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {process:d} {thread:d} - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '[{levelname}] {asctime} - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'json': {
            # Para logs estructurados en Cloud Logging
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'atenea.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'error.log',
            'maxBytes': 10485760,
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
            'include_html': True,
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': config('DJANGO_LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'error_file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console', 'error_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'core': {
            'handlers': ['console', 'file'],
            'level': config('APP_LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        'core.ai_services': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'core.storage': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}

# ====================
# SENTRY (Error Tracking)
# ====================

SENTRY_DSN = config('SENTRY_DSN', default=None)

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        
        # Porcentaje de transacciones a trackear
        traces_sample_rate=0.1,
        
        # Enviar información de usuario
        send_default_pii=True,
        
        # Entorno
        environment=config('ENVIRONMENT', default='production'),
        
        # Release (usa git commit hash)
        release=config('RELEASE', default=None),
        
        # Antes de enviar
        before_send=lambda event, hint: event if not DEBUG else None,
    )

# ====================
# EMAIL
# ====================

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@atenea.com')

ADMINS = [
    ('Admin', config('ADMIN_EMAIL', default='admin@atenea.com')),
]

# ====================
# INTERNACIONALIZACIÓN
# ====================

LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'Europe/Madrid'  # O tu zona horaria
USE_I18N = True
USE_TZ = True

# ====================
# AUTENTICACIÓN
# ====================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,  # Mínimo 12 caracteres en producción
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Login URLs
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# ====================
# TEMPLATES
# ====================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            # Cache templates en producción
            'loaders': [
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ]),
            ],
        },
    },
]

# ====================
# PERFORMANCE
# ====================

# Connection pooling
DATABASES['default']['CONN_MAX_AGE'] = 600

# Template caching (ya configurado arriba)

# ====================
# MONITOREO
# ====================

# Si usas Google Cloud, puedes integrar con Cloud Monitoring
# pip install google-cloud-monitoring

# ====================
# WSGI
# ====================

WSGI_APPLICATION = 'atenea.wsgi.application'

# ====================
# OTRAS CONFIGURACIONES
# ====================

ROOT_URLCONF = 'atenea.urls'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ====================
# CÓMO USAR ESTE ARCHIVO
# ====================

"""
1. En settings.py principal, detectar el entorno:

# atenea/settings.py

from pathlib import Path
from decouple import config

# Detectar entorno
ENVIRONMENT = config('ENVIRONMENT', default='development')

# Cargar configuración base
from .settings_base import *

# Sobrescribir con configuración específica
if ENVIRONMENT == 'production':
    from .settings_production import *
elif ENVIRONMENT == 'staging':
    from .settings_staging import *
else:
    from .settings_development import *

2. En .env:

ENVIRONMENT=production  # o staging, development

3. Variables requeridas en producción:

SECRET_KEY=<strong-secret-key>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DB_NAME=atenea
DB_USER=atenea_user
DB_PASSWORD=<strong-password>
DB_HOST=<db-host>
GCS_BUCKET_NAME=<bucket>
GCS_PROJECT_ID=<project>
HEYGEN_API_KEY=<key>
GEMINI_API_KEY=<key>
REDIS_URL=redis://redis:6379/0
SENTRY_DSN=<sentry-dsn>
"""

