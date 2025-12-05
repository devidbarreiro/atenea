# 🎨 Integración de Rembg (Quitar Fondo) - Versión Asíncrona

## ✅ Problema Resuelto

El error `PermissionError` en Celery era causado por la **vista síncrona bloqueante** que procesaba rembg directamente en la petición HTTP. Esto colapsaba el pool de procesos de Celery en Windows.

## 🔄 Solución Implementada

Se convirtió el procesamiento a una **tarea asíncrona de Celery**, lo que:

- ✅ Libera la petición HTTP inmediatamente
- ✅ Procesa la imagen en un worker asincrónico
- ✅ Evita que Celery se atasque
- ✅ Usa notificaciones para informar cuando está lista

## 📋 Cambios Realizados

### 1. **Tarea Asíncrona** (`core/tasks.py`)

Nueva tarea: `remove_image_background_task`

```python
@shared_task(bind=True, max_retries=2)
def remove_image_background_task(self, image_uuid):
    """Procesa imagen con rembg de forma asíncrona"""
    # - Descarga imagen original desde GCS
    # - Ejecuta rembg con configuración BiRefNet
    # - Crea nuevo Item de imagen sin fondo
    # - Guarda en GCS
    # - Crea notificación de éxito/error
```

**Reintentos:** Hasta 2 intentos automáticos si falla.

### 2. **Vista Simplificada** (`core/views.py`)

Ahora la vista solo:
- Valida la imagen
- Encola la tarea
- Retorna respuesta inmediata

```python
@login_required
@require_http_methods(["POST"])
def remove_image_background(request, image_uuid):
    """Encola tarea asíncrona para quitar fondo"""
    # Valida imagen
    # Encola remove_image_background_task.delay()
    # Retorna { success: true, task_id, message }
```

### 3. **UI Actualizada** (`templates/includes/item_detail_modal.html`)

- Botón "Quitar fondo" encola y muestra confirmación
- Usuario recibe notificación cuando esté lista
- No abre automáticamente el nuevo item (evita confusión)

## 🚀 Cómo Usar

### Para el Usuario (UI)

1. Abrir detalles de una imagen completada
2. Pulsar botón "Quitar fondo"
3. Confirmar
4. ✅ Se muestra mensaje: "Imagen encolada para procesamiento"
5. ⏳ Esperar notificación (2-10 minutos según imagen)
6. 📬 Notificación muestra "Fondo removido - Ver imagen"

### Para Desarrolladores

```python
# Encolar manualmente (si fuera necesario)
from core.tasks import remove_image_background_task
task = remove_image_background_task.delay(image_uuid)

# Monitorear tarea
from celery.result import AsyncResult
result = AsyncResult(task.id)
print(result.status)  # PENDING, PROGRESS, SUCCESS, FAILURE
```

## 📊 Flujo de Datos

```
Usuario: "Quitar fondo" (UI)
    ↓
Petición POST /images/<uuid>/remove-bg/
    ↓
Vista: Valida + Encola tarea
    ↓
Response inmediata: { success: true, task_id }
    ↓
Celery Worker: Procesa imagen con rembg
    ↓
Crea nuevo Image item
    ↓
Guarda en GCS
    ↓
Notificación: "Fondo removido - Ver imagen"
    ↓
Usuario: Ve notificación + abre nueva imagen
```

## ⚙️ Configuración de rembg

La tarea usa la configuración **"PIXEL PERFECT"** que proporcionaste:

```python
remove(
    image_data,
    session=new_session('birefnet-general'),  # Mejor modelo
    alpha_matting=True,
    alpha_matting_foreground_threshold=240,   # Estricto: solo detalles claros
    alpha_matting_background_threshold=10,    # Estricto: solo fondo claro
    alpha_matting_erode_size=1,               # Limpieza quirúrgica
    alpha_matting_base_size=4096,             # Alta resolución
    post_process_mask=False                   # Sin suavizado que pierda detalles
)
```

## 🔧 Requisitos

- `rembg>=2.0.0` (ya en requirements.txt)
- Celery corriendo: `celery -A atenea worker --loglevel=info`
- Redis activo
- GCS configurado (para guardar imagen procesada)

## 📝 Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `core/tasks.py` | ✨ Nueva tarea `remove_image_background_task` |
| `core/views.py` | ⚡ Vista simplificada (solo encola) |
| `templates/includes/item_detail_modal.html` | ⬆️ UI actualizada |

## ✨ Ventajas vs Versión Síncrona

| Aspecto | Síncrona | Asíncrona ✅ |
|--------|----------|------------|
| Bloquea HTTP | ❌ Sí | ✅ No |
| Colapsa Celery | ❌ Sí | ✅ No |
| Timeout | ❌ Posible | ✅ No |
| Reintentos | ❌ Ninguno | ✅ Automáticos |
| UX | ⏳ Lento | ✅ Rápido |
| Escala | ❌ Mala | ✅ Excelente |

## 🐛 Troubleshooting

### Error: "Tarea no se ejecuta"

```powershell
# Verificar que Celery está corriendo
python manage.py celery_status

# Iniciar worker si está parado
celery -A atenea worker --loglevel=info
```

### Error: "PermissionError" en Celery

Ahora no debería ocurrir, pero si lo hace:

```powershell
# Limpiar colas
python manage.py clean_celery
python manage.py clean_stuck_tasks

# Reiniciar Celery
```

### Imagen no aparece como notificación

```python
# Verificar que Notification está funcionando
python manage.py shell
>>> from core.models import Notification
>>> Notification.objects.count()
```

## 🎯 Próximos Pasos (Opcionales)

1. **Webhook de progreso**: Actualizar UI con porcentaje mientras procesa
2. **Cola prioritaria**: Dar prioridad a quitar fondo sobre otras tareas
3. **Caché de modelos**: Reutilizar sesión de rembg entre tareas
4. **Estadísticas**: Trackear tiempo promedio de procesamiento

---

## ✅ Todo Funciona

El sistema está listo. Ahora puedes:
1. Tomar una imagen completada
2. Pulsar "Quitar fondo"
3. ¡La tarea se procesa sin bloqueos!
