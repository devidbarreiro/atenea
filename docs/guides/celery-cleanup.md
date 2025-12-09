# 🧹 Limpiar Celery - Guía Completa

## Problema

A veces Celery acumula tareas "fantasma" en Redis o en la BD que no se pueden purgar con los comandos normales:

```bash
celery -A atenea purge  # ❌ No funciona
celery -A atenea purge --force  # ❌ Tampoco
```

Esto puede pasar cuando:
- Un worker se cuelga sin limpiar sus tareas
- Redis tiene keys corruptas o de tipo incorrecto
- Hay tareas huérfanas en la BD

## Solución Rápida

### Opción 1: Flujo Completo (Recomendado ⭐)

Este flujo limpia tanto BD como Redis:

```powershell
# 1. Ver qué hay
python manage.py celery_status

# 2. Limpiar tareas atascadas en BD (dry-run primero)
python manage.py clean_stuck_tasks --dry-run
python manage.py clean_stuck_tasks

# 3. Limpiar Redis
python manage.py clean_celery

# 4. Verificar que todo está limpio
python manage.py celery_status
```

### Opción 2: Solo Limpieza Redis (Si BD ya está limpia)

```powershell
python manage.py clean_celery
```

### Opción 3: Limpiar TODO Redis (Nuclear 💥)

Si nada funciona y necesitas empezar desde cero:

```powershell
python manage.py clean_celery --hard
```

⚠️ **ADVERTENCIA**: Esto vacía TODO Redis, no solo Celery. Si usas Redis para cache o sessions, perderás esos datos también.

### Opción 4: Solo Verificar (Sin Borrar Nada)

```powershell
# Ver estado sin hacer cambios
python manage.py celery_status

# Ver qué tareas atascadas hay sin eliminarlas
python manage.py clean_stuck_tasks --dry-run
```

## Ver Estado de Celery

Para diagnosticar problemas:

```powershell
python manage.py celery_status
```

Muestra:
- 🟢 Estado de conexión a Redis
- 📋 Tareas pendientes en cada cola
- 💾 Tareas en la BD
- ⏰ Tareas periódicas

## Limpiar Tareas Atascadas en BD

Si hay tareas que nunca se completaron (pending, processing, queued, failed):

```powershell
# Ver qué se eliminaría (sin hacer cambios)
python manage.py clean_stuck_tasks --dry-run

# Eliminar las tareas atascadas
python manage.py clean_stuck_tasks
```

Limpia:
- ✅ GenerationTasks en estado `queued` o `failed`
- ✅ Videos en estado `pending` o `processing`
- ✅ Imágenes en estado `pending` o `processing`
- ✅ Audios en estado `pending` o `processing`

Ejemplo de output:

```
🔴 Redis
  ✅ Conectado a Redis
     Host: localhost:6379
     Version: 7.0.15
     Memory: 1.35M

📋 Tareas en Redis
  video_generation: ✅ 0
  image_generation: ✅ 0
  ...

💾 Tareas en BD
  Total de tareas: 0
  ✅ BD sin tareas residuales
```

## Flujo de Limpieza Completo

Si Celery está atascado y necesitas un reset total:

### 1️⃣ Detén todo

```powershell
# Detener el worker (Ctrl+C si está en terminal)
# Detener el servidor Django (Ctrl+C si está en terminal)
```

### 2️⃣ Verifica qué hay atascado

```powershell
python manage.py celery_status
python manage.py clean_stuck_tasks --dry-run
```

### 3️⃣ Limpia tareas en BD

```powershell
python manage.py clean_stuck_tasks
```

### 4️⃣ Limpia Redis

```powershell
python manage.py clean_celery
```

### 5️⃣ Verifica que esté todo limpio

```powershell
python manage.py celery_status
```

Deberías ver ceros en todo.

### 6️⃣ Reinicia los servicios

```powershell
# Terminal 1: Worker
celery -A atenea worker --loglevel=info `
    --queues=video_generation,image_generation,audio_generation,scene_processing,default,polling_tasks `
    --concurrency=4

# Terminal 2: Django
python manage.py runserver
```

## Si Aún No Funciona

### A. Verificar Redis manualmente

```powershell
# En Python:
python manage.py shell
>>> import redis
>>> r = redis.Redis(host='localhost', port=6379)
>>> r.ping()  # Debería retornar True
>>> r.keys('*')  # Ver todas las keys
>>> len(r.keys('celery*'))  # Contar keys de celery
```

### B. Forzar limpieza manual

```powershell
python manage.py shell
>>> import redis
>>> r = redis.Redis(host='localhost', port=6379)
>>> for key in r.scan_iter('celery*'):
...     r.delete(key)
...     print(f'Eliminada: {key}')
```

### C. Si Redis está completamente corrupto

```powershell
# Opción 1: Con CLI (si tienes redis-cli instalado)
redis-cli FLUSHDB

# Opción 2: Con Python
python manage.py shell
>>> import redis
>>> r = redis.Redis(host='localhost', port=6379)
>>> r.flushdb()  # Vacía todo Redis
```

### D. Reiniciar Redis (última opción)

```powershell
# Windows con Docker
docker stop redis-container
docker start redis-container

# O si está instalado localmente:
# Buscar "Servicios" > "Redis Server" > Reiniciar
```

## Prevención

Para evitar que se acumule basura en Celery:

### 1. Usar task time limits

En `atenea/settings.py`:

```python
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutos max
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutos, tiempo para cleanup
```

### 2. Limpiar tareas antiguas periódicamente

```powershell
# Ejecutar diariamente (agregar a cron/Task Scheduler)
python manage.py shell -c "
from django_celery_results.models import TaskResult
from datetime import timedelta
from django.utils import timezone

# Eliminar tareas más de 7 días antiguas
TaskResult.objects.filter(
    date_done__lt=timezone.now() - timedelta(days=7)
).delete()
"
```

### 3. Monitoreo proactivo

```powershell
# Crear un alias o script para verificar regularmente
python manage.py celery_status
```

## Comandos Rápidos

```powershell
# Ver estado completo
python manage.py celery_status

# Ver qué tareas atascadas hay (sin eliminar)
python manage.py clean_stuck_tasks --dry-run

# Limpiar tareas atascadas en BD
python manage.py clean_stuck_tasks

# Limpiar Celery en Redis (seguro)
python manage.py clean_celery

# Limpiar TODO Redis (nuclear)
python manage.py clean_celery --hard

# Ver tareas en BD
python manage.py shell -c "
from django_celery_results.models import TaskResult
for t in TaskResult.objects.order_by('-date_done')[:10]:
    print(f'{t.task_id}: {t.status}')"

# Limpiar tareas antiguas (7+ días)
python manage.py shell -c "
from django_celery_results.models import TaskResult
from datetime import timedelta
from django.utils import timezone
old = TaskResult.objects.filter(
    date_done__lt=timezone.now() - timedelta(days=7)
).delete()
print(f'Eliminadas {old[0]} tareas antiguas')"
```

## Troubleshooting

| Problema | Solución |
|----------|----------|
| `redis.ConnectionError` | ¿Redis está corriendo? Ver instrucciones en README.md |
| `WRONGTYPE Operation against a key` | Keys corruptas. Usa `clean_celery --hard` |
| Tareas no se ejecutan | `celery_status` para ver si hay bloqueos |
| Worker se cuelga | Detén worker, limpia, reinicia |
| Tareas duplicadas | `clean_stuck_tasks`, `clean_celery`, reinicia |
| No puedo crear nuevos videos/imágenes | Posiblemente haya tareas atascadas. Usa `clean_stuck_tasks` |
| Las colas siguen apareciendo en UI | Limpia BD primero con `clean_stuck_tasks`, luego Redis con `clean_celery` |

## ¡Listo! 🎉

Después de ejecutar `clean_celery`, Celery está como nuevo. Cualquier problema debería estar resuelto.
