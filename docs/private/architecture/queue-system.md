# Sistema de Colas - Arquitectura

## Visión General

El sistema de colas de Atenea utiliza **Celery** con **Redis** como broker para procesar tareas asíncronas de generación de contenido (videos, imágenes, audio). Las notificaciones se envían en tiempo real mediante **WebSockets** (Django Channels).

## Flujo de Generación de Contenido

```mermaid
sequenceDiagram
    actor User
    participant WebUI as Web UI / Browser
    participant Server as Django Server
    participant QueueSvc as QueueService
    participant Celery as Celery<br/>Task Queue
    participant Redis as Redis<br/>Broker & Cache
    participant Worker as Celery<br/>Worker
    participant Services as Generation<br/>Services
    participant GCS as Google<br/>Cloud Storage
    participant DB as Database
    participant WebSocket as WebSocket<br/>Consumer
    participant Client as Client<br/>(WebSocket)

    User->>WebUI: Click "Generate Video"
    WebUI->>Server: POST /videos/generate (video_uuid)
    Server->>QueueSvc: enqueue_generation(video, user, 'video')
    QueueSvc->>DB: Create GenerationTask (queued)
    QueueSvc->>Celery: send_task(generate_video_task, args=[task_uuid, video_uuid, user_id])
    Celery->>Redis: Enqueue task message
    QueueSvc->>Server: Return GenerationTask
    Server->>WebUI: Return 200 (task created)
    WebUI->>WebUI: Update UI, emit 'item-created' event
    
    Worker->>Redis: Poll for tasks (video_generation queue)
    Redis->>Worker: Return task message
    Worker->>DB: Fetch GenerationTask by uuid
    Worker->>Services: call generate_video(video)
    Services->>GCS: Upload video / Poll status
    Services->>DB: Mark video completed/failed
    Worker->>DB: Update GenerationTask status
    
    alt Async (polling required)
        Worker->>Celery: Schedule poll_video_status_task in 30s
        Celery->>Redis: Enqueue polling task
    else Sync (completed)
        Worker->>WebSocket: Emit notification_message event
    end
    
    WebSocket->>Client: WebSocket: {type: 'notification_message', data: {...}}
    Client->>WebUI: Display toast & update count
    User->>WebUI: See "Video ready" notification
```

## Flujo de Notificaciones WebSocket

```mermaid
sequenceDiagram
    actor User
    participant Client as Client<br/>(Browser)
    participant WS as WebSocket<br/>Connection
    participant Consumer as Notification<br/>Consumer
    participant Redis as Redis<br/>Channel Layer
    participant DB as Database
    participant Worker as Celery<br/>Worker

    User->>Client: Open page (authenticated)
    Client->>WS: WebSocket connect to ws://server/ws/notifications/
    WS->>Consumer: on_connect()
    Consumer->>DB: Verify user, fetch unread count
    Consumer->>Redis: Join group notifications_user_{user_id}
    Consumer->>Client: Send {type: 'pending_count', count: N}
    Client->>Client: Update notification badge

    Worker->>Consumer: Send notification via channel layer
    Consumer->>Client: WebSocket: {type: 'notification_message', data: {uuid, type, title, message, ...}}
    Client->>Client: Show toast + increment badge
    
    User->>Client: Click "mark as read"
    Client->>WS: Send {action: 'mark_read', notification_uuid: '...'}
    WS->>Consumer: on_receive(text_data)
    Consumer->>DB: Mark notification.read = True
    Consumer->>Client: Confirm {status: 'success'}
    Client->>Client: Decrement badge count
```

## Componentes Principales

### QueueService (`core/services/queue.py`)

Servicio central para encolar tareas de generación:

```python
from core.services import QueueService

# Encolar generación de video
task = QueueService.enqueue_generation(
    item=video,
    user=request.user,
    task_type='video',
    priority=5
)
```

### Colas Disponibles

| Cola | Propósito | Prioridad |
|------|-----------|-----------|
| `video_generation` | Videos (Sora, Veo, Kling, etc.) | Alta |
| `image_generation` | Imágenes (Gemini, Freepik, etc.) | Alta |
| `audio_generation` | Audio TTS (ElevenLabs) | Media |
| `scene_processing` | Procesamiento de escenas | Media |
| `polling_tasks` | Polling de APIs asíncronas | Baja |
| `maintenance` | Tareas de mantenimiento | Baja |

### Tasks (`core/tasks.py`)

```python
@shared_task(bind=True, max_retries=3)
def generate_video_task(self, task_uuid, video_uuid, user_id, **kwargs):
    # 1. Marcar como processing
    # 2. Llamar al servicio de generación
    # 3. Crear notificación de éxito/error
    # 4. Manejar reintentos
```

### Modelos

**GenerationTask**: Rastrea el estado de cada tarea
- `uuid`: Identificador único
- `task_id`: ID de Celery (puede ser null inicialmente)
- `status`: queued → processing → completed/failed
- `task_type`: video, image, audio, scene
- `metadata`: JSON con datos adicionales

**Notification**: Notificaciones para usuarios
- `type`: generation_completed, generation_failed, system, info
- `read`: Boolean para marcar como leída
- `action_url`: URL para navegar al recurso

## Configuración

### Django Settings

```python
# Celery
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = CELERY_BROKER_URL

# Channels
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {'hosts': [CELERY_BROKER_URL]},
    },
}
```

### Ejecutar Workers

```bash
# Worker con todas las colas
celery -A atenea worker --loglevel=info \
    --queues=video_generation,image_generation,audio_generation,scene_processing,default,polling_tasks \
    --concurrency=4

# Servidor ASGI con WebSockets
daphne -b 0.0.0.0 -p 8000 atenea.asgi:application
```

## Manejo de Errores

1. **Reintentos automáticos**: Cada task tiene `max_retries=3` con backoff exponencial
2. **Notificaciones de error**: Si falla después de todos los reintentos, se notifica al usuario
3. **Logging**: Todos los errores se registran con `exc_info=True`

## Monitoreo

- **Panel de colas**: `/queues/` muestra tareas activas/pendientes
- **Admin Django**: Gestión de GenerationTask y Notification
- **Logs de Celery**: `--loglevel=info` para debugging

