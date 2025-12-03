# 🔍 Revisión de Áreas Críticas - Nueva UI de Creación

Este documento detalla los problemas encontrados y mejoras sugeridas para las áreas que requieren atención especial según el plan de ejecución.

---

## 1. ⚠️ `core/services.py` - Routing de Higgsfield y Descarga de Imágenes

### Problemas Encontrados

#### 1.1. Falta método `_check_higgsfield_status`
**Ubicación:** `core/services.py:1167`

**Problema:** En `check_video_status()`, cuando el tipo de video es Higgsfield o Kling, simplemente retorna el estado del modelo sin consultar la API:

```python
elif video.type == 'sora':
    status_data = self._check_sora_status(video)
else:
    status_data = {'status': video.status}  # ⚠️ No consulta API para Higgsfield/Kling
```

**Impacto:** Los videos de Higgsfield nunca se marcan como completados automáticamente, requiriendo intervención manual.

**Solución Requerida:**
- Crear método `_check_higgsfield_status()` similar a `_check_sora_status()` o `_check_veo_status()`
- Implementar polling del estado usando `client.get_request_status()`
- Descargar video cuando esté completado y subirlo a GCS
- Manejar errores apropiadamente

#### 1.2. Descarga de Imágenes de Higgsfield - Manejo de Errores Mejorable
**Ubicación:** `core/services.py:2004-2007`

**Problema:** La descarga de imágenes usa `requests.get()` sin manejo robusto de timeouts y reintentos:

```python
img_response = requests.get(image_url, timeout=30)
img_response.raise_for_status()
image_data = img_response.content
```

**Mejoras Sugeridas:**
- Agregar reintentos con backoff exponencial
- Manejar errores de red específicos
- Validar tamaño de imagen antes de descargar
- Agregar logging más detallado

#### 1.3. Integración con Ruta de Gemini - Verificación Necesaria
**Ubicación:** `core/services.py:1861-1863`

**Problema:** La lógica de routing entre Higgsfield y Gemini parece correcta, pero falta validación de que ambas rutas manejen errores consistentemente.

**Verificación Requerida:**
- Asegurar que ambos servicios manejen `InsufficientCreditsException` igual
- Verificar que ambos servicios manejen errores de API externa igual
- Confirmar que ambos servicios actualicen metadata de forma consistente

---

## 2. ⚠️ `core/forms/dynamic.py` - Generación de Campos Dinámicos y Manejo de Errores

### Problemas Encontrados

#### 2.1. Instanciación de Clientes HeyGen/Higgsfield - Manejo de Errores Mejorable
**Ubicación:** `core/forms/dynamic.py:269-344` y `347-422`

**Problema Actual:** Los errores se capturan y se muestra un mensaje en el HTML, pero:

1. **Error silencioso en logs:** El error se loguea pero no se propaga al usuario de forma clara
2. **Campos requeridos no se validan:** Si HeyGen falla, los campos `avatar_id` y `voice_id` siguen siendo requeridos pero no están disponibles
3. **No hay fallback:** Si la API de HeyGen está caída, el formulario queda bloqueado

**Mejoras Sugeridas:**

```python
# Mejorar manejo de errores en get_model_specific_fields()
except Exception as e:
    logger.error(f"Error cargando datos de HeyGen V2: {e}", exc_info=True)
    
    # Opción 1: Hacer campos opcionales si hay error
    # Opción 2: Mostrar mensaje más claro al usuario
    # Opción 3: Permitir entrada manual de IDs si la API falla
    
    fields.append({
        'name': 'heygen_error',
        'label': 'Advertencia',
        'required': False,
        'html': f'''
            <div class="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p class="text-sm text-yellow-800 font-semibold mb-2">
                    ⚠️ No se pudieron cargar opciones automáticamente
                </p>
                <p class="text-xs text-yellow-700 mb-2">
                    Puedes ingresar los IDs manualmente:
                </p>
                <input type="text" name="avatar_id" 
                       placeholder="Avatar ID (opcional)" 
                       class="w-full px-3 py-2 border border-yellow-300 rounded-lg text-sm">
            </div>
        '''
    })
```

#### 2.2. Validación de Campos Dinámicos
**Ubicación:** `core/forms/dynamic.py:77-247`

**Problema:** Los campos dinámicos se generan pero no hay validación explícita de que los valores sean válidos según las capacidades del modelo.

**Mejoras Sugeridas:**
- Agregar método `clean()` en `DynamicVideoForm` que valide según modelo seleccionado
- Validar que `duration` esté en el rango permitido
- Validar que `aspect_ratio` sea uno de los soportados
- Validar campos específicos de modelo (ej: `avatar_id` debe existir en HeyGen)

---

## 3. ⚠️ `templates/includes/creation_sidebar.html` - FormData vs JSON y CSRF

### Problemas Encontrados

#### 3.1. Flujo FormData vs JSON - Lógica Compleja
**Ubicación:** `templates/includes/creation_sidebar.html:164-234`

**Problema:** La lógica para decidir entre FormData y JSON es correcta pero tiene algunos puntos de mejora:

1. **Detección de imágenes:** La condición `hasReferenceImages` verifica si hay archivos, pero no valida que los archivos sean válidos antes de enviar
2. **CSRF token:** Se obtiene correctamente, pero si no existe el token, el request falla silenciosamente
3. **Manejo de errores:** Los errores se muestran con `alert()` que no es ideal para UX

**Mejoras Sugeridas:**

```javascript
// Validar archivos antes de enviar
const validateFiles = () => {
    const files = [startImage, endImage, styleImage, assetImage].filter(f => f?.files?.[0]);
    const maxSize = 10 * 1024 * 1024; // 10MB
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
    
    for (const fileInput of files) {
        const file = fileInput.files[0];
        if (file.size > maxSize) {
            alert(`El archivo ${file.name} es demasiado grande (máx: 10MB)`);
            return false;
        }
        if (!allowedTypes.includes(file.type)) {
            alert(`El archivo ${file.name} tiene un formato no soportado`);
            return false;
        }
    }
    return true;
};

// Mejorar manejo de CSRF
const token = document.querySelector('[name=csrfmiddlewaretoken]');
if (!token) {
    console.error('CSRF token no encontrado');
    alert('Error de seguridad. Por favor recarga la página.');
    return;
}

// Mejorar manejo de errores
if (!response.ok) {
    const errorData = await response.json().catch(() => ({ error: 'Error desconocido' }));
    // Mostrar error en UI en lugar de alert
    showError(errorData.error || `Error ${response.status}`);
    return;
}
```

#### 3.2. Campos Dinámicos y CSRF en FormData
**Ubicación:** `templates/includes/creation_sidebar.html:190`

**Problema:** Cuando se usa FormData, los `settings` se serializan como JSON string, pero si hay campos dinámicos complejos (ej: arrays), pueden no serializarse correctamente.

**Verificación Requerida:**
- Probar con campos que contengan arrays o objetos anidados
- Verificar que el backend pueda deserializar correctamente el JSON de `settings`
- Asegurar que campos de archivo no interfieran con la serialización

---

## 4. ⚠️ `templates/includes/library_panel.html` - Polling y Cleanup

### Problemas Encontrados

#### 4.1. Polling Interval - Cleanup Mejorable
**Ubicación:** `templates/includes/library_panel.html:366-403`

**Problema Actual:** El cleanup existe pero puede mejorarse:

1. **Cleanup en destroy():** ✅ Existe pero solo se ejecuta cuando Alpine destruye el componente
2. **Cleanup cuando cambia el estado:** ✅ Existe (línea 388) pero puede mejorarse
3. **Cleanup cuando se navega fuera:** ⚠️ No hay cleanup explícito cuando el usuario navega a otro item

**Mejoras Sugeridas:**

```javascript
// Agregar cleanup cuando se cierra el detalle
closeDetail() {
    // Limpiar todos los polling intervals antes de cerrar
    this.items.forEach(item => {
        if (item.pollingInterval) {
            clearInterval(item.pollingInterval);
            item.pollingInterval = null;
        }
    });
    
    this.selectedItem = null;
    // ... resto del código
}

// Agregar cleanup cuando se cambia de tab
window.addEventListener('library-tab-changed', (e) => {
    // Limpiar polling de items anteriores
    this.items.forEach(item => {
        if (item.pollingInterval) {
            clearInterval(item.pollingInterval);
        }
    });
    
    this.activeTab = e.detail.tab;
    this.selectedItem = null;
    this.loadItems();
});

// Mejorar el método destroy() para ser más robusto
destroy() {
    // Limpiar polling
    if (this.pollingInterval) {
        clearInterval(this.pollingInterval);
        this.pollingInterval = null;
    }
    
    // Limpiar event listeners si los hay
    // (si se agregaron listeners personalizados)
}
```

#### 4.2. Event Lifecycle - Verificación Necesaria
**Ubicación:** `templates/includes/library_panel.html:28-57`

**Problema:** Los event listeners se agregan en `init()` pero no se documenta claramente cuándo se destruyen.

**Verificación Requerida:**
- Confirmar que Alpine.js destruye los listeners automáticamente
- Verificar que no haya memory leaks cuando se navega entre páginas
- Probar que los eventos se limpian correctamente cuando se cambia de proyecto

**Mejora Sugerida:**

```javascript
init() {
    this.loadItems();
    
    // Guardar referencias a los handlers para poder removerlos después
    this._handlers = {
        libraryTabChanged: (e) => {
            this.activeTab = e.detail.tab;
            this.selectedItem = null;
            this.loadItems();
        },
        itemCreated: () => {
            this.loadItems();
        },
        videoStatusChanged: (e) => {
            if (this.activeTab === 'video') {
                setTimeout(() => {
                    this.loadItems();
                }, 500);
            }
        },
        popstate: () => {
            this.selectedItem = null;
        }
    };
    
    // Agregar listeners
    window.addEventListener('library-tab-changed', this._handlers.libraryTabChanged);
    window.addEventListener('item-created', this._handlers.itemCreated);
    window.addEventListener('video-status-changed', this._handlers.videoStatusChanged);
    window.addEventListener('popstate', this._handlers.popstate);
},

destroy() {
    // Remover listeners
    if (this._handlers) {
        window.removeEventListener('library-tab-changed', this._handlers.libraryTabChanged);
        window.removeEventListener('item-created', this._handlers.itemCreated);
        window.removeEventListener('video-status-changed', this._handlers.videoStatusChanged);
        window.removeEventListener('popstate', this._handlers.popstate);
    }
    
    // Limpiar polling
    if (this.pollingInterval) {
        clearInterval(this.pollingInterval);
    }
}
```

---

## 5. ⚠️ `core/services/credits.py` - Mapeo Model-ID a Video-Type

### Problemas Encontrados

#### 5.1. Mapeo Model-ID a Video-Type - Lógica Compleja
**Ubicación:** `core/services/credits.py:564-608`

**Problema:** El método `estimate_video_cost()` tiene lógica compleja para mapear `model_id` a `video_type` con múltiples fallbacks. Esto puede llevar a inconsistencias.

**Análisis:**
- ✅ Hay mapeo explícito usando `VIDEO_TYPE_TO_MODEL_ID`
- ✅ Hay fallbacks basados en strings en `model_id`
- ⚠️ La lógica es extensa y puede tener casos edge no cubiertos

**Mejoras Sugeridas:**

```python
@staticmethod
def estimate_video_cost(video_type=None, duration=None, config=None, model_id=None):
    """
    Estima costo antes de generar (para mostrar al usuario)
    """
    from core.ai_services.model_config import VIDEO_TYPE_TO_MODEL_ID, get_model_capabilities
    
    duration = duration or 8
    
    # Si se proporciona model_id, intentar mapear a video_type
    if model_id and not video_type:
        video_type = CreditService._map_model_id_to_video_type(model_id)
    
    if not video_type:
        logger.warning(f"No se pudo determinar video_type para model_id: {model_id}")
        return Decimal('0')
    
    # ... resto del código
```

```python
@staticmethod
def _map_model_id_to_video_type(model_id: str) -> Optional[str]:
    """
    Mapea model_id a video_type de forma centralizada
    """
    from core.ai_services.model_config import VIDEO_TYPE_TO_MODEL_ID
    
    # 1. Buscar en mapeo explícito
    for vtype, mid in VIDEO_TYPE_TO_MODEL_ID.items():
        if mid == model_id:
            return vtype
    
    # 2. Fallback basado en strings
    model_id_lower = model_id.lower()
    
    if 'veo' in model_id_lower:
        return 'gemini_veo'
    elif 'sora' in model_id_lower:
        return 'sora'
    elif 'heygen-avatar-v2' in model_id_lower:
        return 'heygen_avatar_v2'
    elif 'heygen-avatar-iv' in model_id_lower:
        return 'heygen_avatar_iv'
    elif 'kling-v' in model_id_lower:
        return model_id.replace('-', '_')
    elif 'higgsfield-ai/dop/standard' in model_id_lower:
        return 'higgsfield_dop_standard'
    elif 'higgsfield-ai/dop/preview' in model_id_lower:
        return 'higgsfield_dop_preview'
    elif 'seedance' in model_id_lower:
        return 'higgsfield_seedance_v1_pro'
    elif 'kling-video/v2.1/pro' in model_id_lower:
        return 'higgsfield_kling_v2_1_pro'
    elif 'vuela' in model_id_lower:
        return 'vuela_ai'
    
    return None
```

#### 5.2. Validación de Pricing Keys - Mejorable
**Ubicación:** `core/services/credits.py:264-266`, `274-276`, `284-286`, etc.

**Problema:** Hay validaciones de pricing keys pero son inconsistentes. Algunas usan `logger.error()` y retornan `Decimal('0')`, otras lanzan excepciones.

**Mejoras Sugeridas:**
- Centralizar validación de pricing keys
- Usar excepciones consistentes cuando falta una clave
- Agregar validación al inicio de cada método de cálculo

```python
@staticmethod
def _validate_pricing_key(service_key: str, price_key: str = None) -> bool:
    """
    Valida que una clave de pricing existe
    """
    if service_key not in CreditService.PRICING:
        logger.error(f"Servicio '{service_key}' no encontrado en PRICING")
        return False
    
    if price_key and price_key not in CreditService.PRICING[service_key]:
        logger.error(f"Clave de precio '{price_key}' no encontrada en PRICING para {service_key}")
        return False
    
    return True
```

---

## 6. ⚠️ Templates `_form.html` Eliminados - Verificación de Referencias

### Estado Actual

**Templates que aún existen:**
- ✅ `templates/audios/_form.html` - **AÚN EN USO** (referenciado en `create.html` y `create_partial.html`)
- ✅ `templates/images/_form.html` - **AÚN EN USO** (referenciado en `create.html` y `create_partial.html`)
- ✅ `templates/scripts/_form.html` - **AÚN EN USO** (referenciado en `create.html` y `create_partial.html`)
- ✅ `templates/music/_form.html` - **AÚN EN USO** (referenciado en `create.html`)

**Templates eliminados/migrados:**
- ✅ `templates/videos/_form.html` - **MIGRADO** a `_form_simple.html` y sistema dinámico

### Verificación Requerida

1. **Verificar que `_form.html` de videos no tenga referencias rotas:**
   ```bash
   grep -r "_form.html" templates/ --exclude-dir=__pycache__
   ```
   ✅ Ya verificado: Solo se usa `_form_simple.html` para videos

2. **Decidir sobre templates restantes:**
   - ¿Migrar `images/_form.html` al sistema dinámico?
   - ¿Migrar `audios/_form.html` al sistema dinámico?
   - ¿Mantener `scripts/_form.html` y `music/_form.html` como están?

3. **Verificar funcionalidad migrada:**
   - ✅ Campos dinámicos funcionan para videos
   - ⚠️ Verificar que todos los campos de `_form.html` antiguo estén en el sistema dinámico
   - ⚠️ Verificar que validaciones antiguas estén implementadas

---

## 📋 Resumen de Acciones Requeridas

### 🔴 Crítico (Debe hacerse antes de producción)

1. **Implementar `_check_higgsfield_status()` en `core/services.py`**
   - Sin esto, los videos de Higgsfield nunca se completan automáticamente

2. **Mejorar cleanup de polling en `library_panel.html`**
   - Agregar cleanup explícito en navegación y cambio de tabs
   - Prevenir memory leaks

### 🟡 Importante (Debe hacerse pronto)

3. **Mejorar manejo de errores en `dynamic.py`**
   - Agregar fallbacks cuando APIs externas fallan
   - Mejorar UX cuando HeyGen/Higgsfield no están disponibles

4. **Validar flujo FormData vs JSON**
   - Probar con casos edge (archivos grandes, tipos inválidos)
   - Mejorar manejo de errores en frontend

5. **Centralizar mapeo model-id a video-type**
   - Crear método `_map_model_id_to_video_type()` en `credits.py`
   - Reducir duplicación de lógica

### 🟢 Mejoras (Puede hacerse después)

6. **Mejorar validación de pricing keys**
   - Centralizar validación
   - Hacer más consistente el manejo de errores

7. **Documentar event lifecycle**
   - Documentar cuándo se crean/destruyen listeners
   - Agregar comentarios sobre cleanup

---

## 🧪 Testing Requerido

### Para cada área crítica:

1. **Higgsfield Service:**
   - [ ] Probar generación de video con Higgsfield
   - [ ] Verificar que el estado se actualiza correctamente
   - [ ] Probar descarga de imágenes con diferentes tamaños
   - [ ] Probar manejo de errores de API

2. **Dynamic Forms:**
   - [ ] Probar con API de HeyGen caída
   - [ ] Probar con campos requeridos faltantes
   - [ ] Probar validación de valores según modelo

3. **Creation Sidebar:**
   - [ ] Probar envío con FormData (con imágenes)
   - [ ] Probar envío con JSON (sin imágenes)
   - [ ] Probar con CSRF token faltante
   - [ ] Probar con archivos inválidos (tamaño, tipo)

4. **Library Panel:**
   - [ ] Probar polling de múltiples videos
   - [ ] Verificar cleanup al navegar entre items
   - [ ] Verificar cleanup al cambiar de tab
   - [ ] Probar memory leaks con DevTools

5. **Credits Service:**
   - [ ] Probar mapeo de todos los model_ids conocidos
   - [ ] Probar con model_ids desconocidos
   - [ ] Verificar cálculo de costos para todos los servicios

---

## 📝 Notas Finales

- La mayoría de las áreas críticas tienen implementaciones funcionales pero pueden mejorarse
- El problema más crítico es la falta de `_check_higgsfield_status()` que impide que los videos se completen automáticamente
- Los problemas de memory leaks en polling son importantes pero no bloquean funcionalidad básica
- Las mejoras sugeridas son incrementales y pueden implementarse gradualmente

---

**Última actualización:** 2024-12-19
**Revisado por:** AI Assistant
**Estado:** ✅ Implementación completada

---

## ✅ Mejoras Implementadas

### 1. ✅ `core/services.py` - Método `_check_higgsfield_status()` implementado
- ✅ Los videos de Higgsfield ahora se verifican automáticamente
- ✅ Descarga y sube videos a GCS cuando están completos
- ✅ Maneja errores apropiadamente (failed, error, nsfw)
- ✅ Integrado en el flujo de `check_video_status()`

### 2. ✅ `core/forms/dynamic.py` - Manejo de errores mejorado
- ✅ Cuando HeyGen API falla, se muestran campos de entrada manual
- ✅ Campos opcionales cuando hay error (no bloquean el formulario)
- ✅ Mensajes de error más claros y útiles
- ✅ Soporte para entrada manual de IDs cuando la API no está disponible

### 3. ✅ `templates/includes/creation_sidebar.html` - Validación y manejo de errores mejorado
- ✅ Validación de archivos antes de enviar (tamaño y tipo)
- ✅ Verificación de CSRF token antes de enviar
- ✅ Manejo mejorado de errores HTTP y JSON
- ✅ Soporte para campos de entrada manual de HeyGen (input text además de select)
- ✅ Métodos `showError()` y `showSuccess()` para mejor UX

### 4. ✅ `templates/includes/library_panel.html` - Cleanup de polling mejorado
- ✅ Método `destroy()` para limpiar listeners
- ✅ Método `_cleanupAllPolling()` para limpiar todos los intervals
- ✅ Cleanup explícito al cerrar detalles y cambiar de tab
- ✅ Método `stopPolling()` en cada item card para limpieza manual
- ✅ Prevención de memory leaks mejorada

### 5. ✅ `core/services/credits.py` - Mapeo centralizado y validación mejorada
- ✅ Método `_map_model_id_to_video_type()` centralizado
- ✅ Método `_validate_pricing_key()` para validación consistente
- ✅ Reducción de duplicación de código
- ✅ Manejo de errores más consistente en cálculo de costos

### 6. ✅ Verificación de templates - Sin referencias rotas
- ✅ Confirmado que `videos/_form.html` fue migrado correctamente a `_form_simple.html`
- ✅ Otros templates `_form.html` (images, audios, scripts, music) están en uso correctamente
- ✅ No hay referencias rotas

