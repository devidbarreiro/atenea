# Atenea 🎬

Plataforma centralizada para generación de contenido de video e imágenes con IA. Integra múltiples servicios de IA (HeyGen, Gemini Veo, OpenAI) para crear contenido de forma automatizada.

## 🚀 Inicio Rápido

### 👨‍💻 Frontend Developer (Nuevo Aquí?)
**[→ Guía de Frontend](docs/frontend/GETTING_STARTED.md)** - Todo lo que necesitas para empezar

**Stack**: Tailwind CSS + HTMX + Alpine.js + Django Templates  
**Tiempo de setup**: 5 minutos  
**No necesitas**: Node.js, npm, webpack, o build tools complejos

### 🔧 Backend Developer
Sigue las instrucciones de instalación abajo.

---

## 📚 Documentación Completa

**[→ Documentación Principal](docs/README.md)**

- **[Frontend](docs/frontend/)** - Tailwind, HTMX, Alpine, componentes
- **[Backend](docs/architecture/)** - Django, Service Layer, arquitectura
- **[Getting Started](docs/getting-started/)** - Tutoriales para empezar
- **[Guías](docs/guides/)** - Cómo hacer tareas específicas

---

## Requisitos

- Python 3.8 o superior
- pip
- Redis (para Celery y WebSockets)

### Instalar Redis

**macOS:**
```bash
brew install redis
brew services start redis
```

**Windows:**
- Opción 1: Descargar desde [Microsoft Archive Redis](https://github.com/microsoftarchive/redis/releases)
- Opción 2: Usar Docker: `docker run -d -p 6379:6379 redis`

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis
sudo systemctl enable redis  # Para iniciar automáticamente al arrancar
```

**Verificar que Redis está corriendo:**
```bash
redis-cli ping
# Debe responder: PONG
```

## Instalación

1. Clonar el repositorio:
```bash
git clone <url-del-repositorio>
cd atenea
```

2. Crear y activar el entorno virtual:
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Ejecutar migraciones:
```bash
python manage.py migrate
```

5. Crear un superusuario (opcional):
```bash
python manage.py createsuperuser
```

6. Ejecutar el servidor de desarrollo:
```bash
python manage.py runserver
```

La aplicación estará disponible en http://127.0.0.1:8000/

## Estructura del Proyecto

```
atenea/
├── atenea/                      # Configuración Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/                        # App principal
│   ├── models.py                # Project, Video
│   ├── views.py                 # Vistas y endpoints
│   ├── urls.py                  # URLs
│   ├── admin.py                 # Admin config
│   ├── ai_services/             # Abstracción de APIs IA
│   │   ├── base.py
│   │   ├── heygen.py
│   │   └── gemini_veo.py
│   └── storage/                 # Abstracción de storage
│       └── gcs.py
├── templates/                   # Templates HTML
│   ├── base.html
│   ├── dashboard/
│   ├── projects/
│   └── videos/
├── manage.py
└── requirements.txt
```

## Características 🚀

- **Gestión de Proyectos**: Organiza tus videos en proyectos
- **Múltiples Tipos de Video**:
  - 👤 **HeyGen Avatar**: Videos con avatares AI personalizables
  - 🎨 **Gemini Veo**: Videos generados por IA de Google
- **Almacenamiento en Cloud**: Integración con Google Cloud Storage
- **Dashboard Intuitivo**: Interfaz moderna y fácil de usar
- **Gestión de Estado**: Tracking completo del proceso de generación
- **Preview de Videos**: Visualización de videos completados

## Configuración ⚙️

### Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
SECRET_KEY=tu-secret-key-django
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Google Cloud Storage
GCS_BUCKET_NAME=devid-bucket-0001
GCS_PROJECT_ID=proeduca-472312
GOOGLE_APPLICATION_CREDENTIALS=credentials.json

# API Keys
HEYGEN_API_KEY=tu-api-key-de-heygen
GEMINI_API_KEY=tu-api-key-de-gemini
```

### Estructura del Bucket GCS

```
devid-bucket-0001/
├── projects/
│   └── {project_id}/
│       └── videos/
│           └── {video_id}/
│               └── final_video.mp4
```

## Comandos Útiles

```bash
# Crear una nueva aplicación
python manage.py startapp nombre_app

# Crear migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Ejecutar tests
python manage.py test

# Recopilar archivos estáticos
python manage.py collectstatic

# Reiniciar Daphne
daphne -b 0.0.0.0 -p 8000 atenea.asgi:application

# Reiniciar Celery
# ⚠️ IMPORTANTE: Antes de ejecutar Celery, asegúrate de que Redis esté corriendo

# Instalar y ejecutar Redis localmente:
# macOS:
#   brew install redis
#   brew services start redis
# Windows:
#   Descargar desde: https://github.com/microsoftarchive/redis/releases
#   O usar Docker: docker run -d -p 6379:6379 redis
# Linux:
#   sudo apt-get install redis-server
#   sudo systemctl start redis

# Verificar que Redis está corriendo:
#   redis-cli ping  (debe responder: PONG)

# Linux/macOS:
celery -A atenea worker --loglevel=info \
    --queues=video_generation,image_generation,audio_generation,scene_processing,default,polling_tasks \
    --concurrency=4

# linux sin comunicacion entre procesos (multiprocessing)
./venv/Scripts/celery.exe -A atenea worker --loglevel=info --pool=solo \
    --queues=video_generation,image_generation,audio_generation,scene_processing,default,polling_tasks

# Windows (PowerShell):
celery -A atenea worker --loglevel=info `
    --queues=video_generation,image_generation,audio_generation,scene_processing,default,polling_tasks `
    --concurrency=4

# Windows (CMD):
celery -A atenea worker --loglevel=info ^
    --queues=video_generation,image_generation,audio_generation,scene_processing,default,polling_tasks ^
    --concurrency=4

# Windows (una sola línea):
celery -A atenea worker --loglevel=info --queues=video_generation,image_generation,audio_generation,scene_processing,default,polling_tasks --concurrency=4
```

## 🧹 Limpiar Celery (Si se atasca)

Si las colas de Celery se atascan o acumulan tareas que no se pueden purgar:

### Paso 1: Ver estado actual
```powershell
python manage.py celery_status
```

### Paso 2: Limpiar tareas atascadas en BD
```powershell
# Ver qué se eliminaría (sin hacer cambios)
python manage.py clean_stuck_tasks --dry-run

# Eliminar
python manage.py clean_stuck_tasks
```

### Paso 3: Limpiar Redis
```powershell
# Limpiar solo Celery (recomendado)
python manage.py clean_celery

# O si nada funciona, limpiar TODO Redis (nuclear)
python manage.py clean_celery --hard
```

### Paso 4: Verificar que está limpio
```powershell
python manage.py celery_status
```

**Ver guía completa:** [🧹 Limpiar Celery](docs/guides/celery-cleanup.md)

# Test deployment

