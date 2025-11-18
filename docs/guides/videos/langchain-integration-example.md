# 🔗 Ejemplo de Integración: Reemplazar n8n con LangChain

## 📝 Ejemplo: AgentConfigureView

### Antes (con n8n)

```python
# En core/views.py
from .services import N8nService

class AgentConfigureView(ServiceMixin, View):
    def post(self, request, *args, **kwargs):
        # ... código de validación ...
        
        # Crear script
        script = Script.objects.create(...)
        
        # Enviar a n8n
        n8n_service = N8nService()
        if n8n_service.send_script_for_processing(script):
            # Esperar webhook de n8n...
            return JsonResponse({'status': 'processing'})
```

### Después (con LangChain)

```python
# En core/views.py
from .services_agent import ScriptAgentService

class AgentConfigureView(ServiceMixin, View):
    def post(self, request, *args, **kwargs):
        # ... código de validación ...
        
        # Crear script
        script = Script.objects.create(...)
        
        # Procesar directamente con LangChain
        try:
            agent_service = ScriptAgentService()
            script = agent_service.process_script(script)
            
            # Las escenas ya están creadas
            return JsonResponse({
                'status': 'success',
                'script_id': script.id,
                'scenes_count': script.db_scenes.count()
            })
        except Exception as e:
            logger.error(f"Error al procesar guión: {e}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
```

---

## 📝 Ejemplo: N8nWebhookView (Ya no necesario)

### Antes

```python
class N8nWebhookView(View):
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        n8n_service = N8nService()
        script = n8n_service.process_webhook_response(data)
        return JsonResponse({'status': 'ok'})
```

### Después

**Este endpoint ya no es necesario** porque el procesamiento es síncrono.

Puedes:
1. **Eliminar** el endpoint completamente
2. **Mantenerlo** para compatibilidad durante migración (retorna error informativo)

```python
class N8nWebhookView(View):
    """Endpoint deprecated - Ya no se usa con LangChain"""
    def post(self, request, *args, **kwargs):
        logger.warning("N8nWebhookView llamado pero ya no se usa con LangChain")
        return JsonResponse({
            'status': 'deprecated',
            'message': 'Este endpoint ya no se usa. El procesamiento es síncrono ahora.'
        }, status=410)  # 410 Gone
```

---

## 📝 Ejemplo: Feature Flag para Migración Gradual

```python
# En core/views.py
from django.conf import settings
from decouple import config

# Feature flag
USE_LANGCHAIN_AGENT = config('USE_LANGCHAIN_AGENT', default=False, cast=bool)

class AgentConfigureView(ServiceMixin, View):
    def post(self, request, *args, **kwargs):
        # ... crear script ...
        
        if USE_LANGCHAIN_AGENT:
            # Nuevo sistema con LangChain
            from .services_agent import ScriptAgentService
            service = ScriptAgentService()
            script = service.process_script(script)
        else:
            # Sistema antiguo con n8n
            from .services import N8nService
            service = N8nService()
            service.send_script_for_processing(script)
        
        return JsonResponse({'status': 'processing'})
```

**En `.env`:**
```env
USE_LANGCHAIN_AGENT=True  # Cambiar a True para activar LangChain
```

---

## 📝 Ejemplo: Manejo de Errores Mejorado

```python
from core.services_agent import ScriptAgentService
from core.services import ValidationException, ServiceException

class AgentConfigureView(ServiceMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            # ... crear script ...
            
            agent_service = ScriptAgentService()
            script = agent_service.process_script(script)
            
            return JsonResponse({
                'status': 'success',
                'script_id': script.id,
                'scenes_count': script.db_scenes.count()
            })
            
        except ValidationException as e:
            # Errores de validación (guión inválido, etc.)
            logger.warning(f"Error de validación: {e}")
            return JsonResponse({
                'status': 'error',
                'message': str(e),
                'type': 'validation'
            }, status=400)
            
        except ServiceException as e:
            # Errores del servicio (LLM falló, etc.)
            logger.error(f"Error del servicio: {e}")
            return JsonResponse({
                'status': 'error',
                'message': 'Error al procesar guión. Por favor intenta de nuevo.',
                'type': 'service'
            }, status=500)
            
        except Exception as e:
            # Errores inesperados
            logger.exception(f"Error inesperado: {e}")
            return JsonResponse({
                'status': 'error',
                'message': 'Error inesperado. Contacta soporte.',
                'type': 'unexpected'
            }, status=500)
```

---

## 📝 Ejemplo: Polling (Ya no necesario)

### Antes (con n8n)

El frontend hacía polling esperando el webhook:

```javascript
// En templates/agent/configure.html
function pollScriptStatus(scriptId) {
    setInterval(() => {
        fetch(`/scripts/${scriptId}/status/`)
            .then(r => r.json())
            .then(data => {
                if (data.status === 'completed') {
                    // Redirigir a escenas
                    window.location.href = `/agent/scenes/${scriptId}/`;
                }
            });
    }, 3000);
}
```

### Después (con LangChain)

El procesamiento es síncrono, así que puedes:

**Opción 1: Respuesta inmediata**
```javascript
// El servidor procesa y responde inmediatamente
fetch('/agent/configure/', {
    method: 'POST',
    body: formData
})
.then(r => r.json())
.then(data => {
    if (data.status === 'success') {
        // Redirigir inmediatamente
        window.location.href = `/agent/scenes/${data.script_id}/`;
    }
});
```

**Opción 2: Procesamiento async con feedback**
```python
# En views.py - Procesar en background con Celery
from celery import shared_task

@shared_task
def process_script_async(script_id):
    script = Script.objects.get(id=script_id)
    service = ScriptAgentService()
    return service.process_script(script)

class AgentConfigureView(ServiceMixin, View):
    def post(self, request, *args, **kwargs):
        # ... crear script ...
        
        # Procesar en background
        task = process_script_async.delay(script.id)
        
        return JsonResponse({
            'status': 'processing',
            'task_id': task.id,
            'script_id': script.id
        })
```

---

## ✅ Checklist de Integración

- [ ] Reemplazar `N8nService` por `ScriptAgentService` en todas las views
- [ ] Eliminar o deprecar `N8nWebhookView`
- [ ] Actualizar frontend para manejar respuesta síncrona
- [ ] Eliminar polling innecesario
- [ ] Agregar manejo de errores mejorado
- [ ] Probar flujo completo end-to-end
- [ ] Monitorear métricas en LangSmith
- [ ] Documentar cambios

---

**Nota:** Durante la migración, puedes mantener ambos sistemas con un feature flag para hacer rollback fácil si es necesario.

