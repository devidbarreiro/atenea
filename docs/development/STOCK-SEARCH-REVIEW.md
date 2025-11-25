# Revisión de Sistema de Búsqueda de Stock

## Resumen Ejecutivo

Revisión sistemática de las áreas críticas del sistema de búsqueda de contenido stock, identificando problemas potenciales y mejoras necesarias.

---

## 1. API Client Implementations

### 1.1 Pexels Client (`pexels.py`)

#### ✅ Fortalezas
- Manejo robusto de errores con logging detallado
- Validación de límites de paginación (`per_page: min(per_page, 80)`)
- Mapeo correcto de orientaciones

#### ⚠️ Problemas Identificados

**1.1.1 Mapeo de campos en `parse_photos()`**
```python
# Línea 222-224: Acceso anidado sin validación
'thumbnail': photo.get('src', {}).get('medium', ''),
'preview': photo.get('src', {}).get('large', ''),
'download_url': photo.get('src', {}).get('original', ''),
```
**Problema**: Si `photo.get('src')` retorna `None`, `.get('medium')` fallará con `AttributeError`.

**Solución**:
```python
src = photo.get('src') or {}
'thumbnail': src.get('medium', ''),
'preview': src.get('large', ''),
'download_url': src.get('original', ''),
```

**1.1.2 Mapeo de campos en `parse_videos()`**
```python
# Línea 260-265: Selección de mejor calidad
best_quality = max(
    video_files,
    key=lambda x: x.get('width', 0) * x.get('height', 0),
    default={}
)
```
**Problema**: Si `video_files` está vacío, `max()` con `default={}` retorna `{}`, pero luego se accede a `best_quality.get('link')` que puede ser `None`.

**Solución**: Validar que `best_quality` tenga contenido antes de usarlo.

**1.1.3 Construcción de URL**
- ✅ Correcta: Usa `f"{self.base_url}{endpoint}"` con validación

### 1.2 Pixabay Client (`pixabay.py`)

#### ⚠️ Problemas Identificados

**1.2.1 Mapeo de campos en `parse_videos()`**
```python
# Línea 327-328: Acceso anidado sin validación completa
videos = video.get('videos', {})
best_quality = videos.get('large', {}) or videos.get('medium', {}) or videos.get('small', {})
```
**Problema**: Si `videos` es `None` o no tiene ninguna de las claves, `best_quality` será `{}`, causando problemas en líneas 336-339.

**Solución**: Validar que `best_quality` tenga `url` antes de agregar al resultado.

**1.2.2 Construcción de URL de photographer**
```python
# Línea 299: Construcción de URL puede fallar si user_id es None
'photographer_url': f"https://pixabay.com/users/{image.get('user', '')}-{image.get('user_id', '')}/",
```
**Problema**: Si `user_id` es `None`, la URL será inválida: `...users/username-None/`

**Solución**: Validar que ambos campos existan antes de construir la URL.

**1.2.3 Límites de paginación**
- ✅ Correcto: `min(per_page, 200)` para imágenes y videos
- ✅ Correcto: `min(per_page, 200)` para audio

### 1.3 Unsplash Client (`unsplash.py`)

#### ⚠️ Problemas Identificados

**1.3.1 Mapeo de campos en `parse_photos()`**
```python
# Línea 160: Acceso anidado sin validación completa
urls = photo.get('urls', {})
```
**Problema**: Similar a Pexels, si `urls` es `None`, el acceso fallará.

**Solución**: Usar `photo.get('urls') or {}`

**1.3.2 Orientación**
```python
# Línea 171: Usa directamente el campo de la API
'orientation': photo.get('orientation', 'unknown'),
```
**Problema**: Unsplash retorna `'landscape'`, `'portrait'`, `'squarish'`, pero el sistema espera `'horizontal'`, `'vertical'`, `'square'`.

**Solución**: Mapear valores de Unsplash al formato interno.

**1.3.3 Límites de paginación**
- ✅ Correcto: `min(per_page, 30)` (límite de Unsplash)

### 1.4 FreeSound Client (`freesound.py`)

#### ⚠️ Problemas Identificados

**1.4.1 Construcción de download_url**
```python
# Línea 195: URL de descarga requiere autenticación
download_url = f"https://freesound.org/apiv2/sounds/{sound.get('id')}/download/"
```
**Problema**: Esta URL requiere autenticación adicional y puede no funcionar directamente. FreeSound requiere un endpoint específico para obtener la URL de descarga.

**Solución**: Usar el endpoint `/sounds/{id}/download/` con autenticación, o marcar como `None` si no está disponible.

**1.4.2 Campos opcionales**
- ✅ Correcto: Maneja campos opcionales con `.get()` y valores por defecto

---

## 2. StockService Orchestration (`stock_service.py`)

### ✅ Fortalezas
- Aislamiento de errores: Cada fuente se maneja en try/except separado
- Mapeo de orientaciones centralizado
- Filtrado de fuentes disponibles

### ⚠️ Problemas Identificados

**2.1 Aislamiento de errores**
```python
# Líneas 148-150: Error en una fuente no afecta otras
except Exception as e:
    logger.error(f"Error buscando en {source}: {e}")
    results_by_source[source] = []
```
✅ **Correcto**: Un error en una fuente no rompe el servicio completo.

**2.2 División de resultados**
```python
# Línea 118: División puede causar problemas si sources está vacío
max_results_per_source = (per_page // len(sources)) + 5
```
**Problema**: Si `sources` está vacío después del filtrado, `len(sources)` será 0 y causará `ZeroDivisionError`.

**Solución**:
```python
if not sources:
    return {'query': query, 'total': 0, 'results': [], ...}
max_results_per_source = (per_page // len(sources)) + 5 if sources else per_page
```

**2.3 Mapeo de orientación para Pixabay**
```python
# Línea 38: Pixabay no tiene square específico
'square': {
    'pixabay': None,  # Pixabay no tiene square específico
}
```
**Problema**: Si se busca con orientación `square` y solo Pixabay está disponible, no se aplicará ningún filtro.

**Solución**: Documentar este comportamiento o usar `'all'` como fallback.

**2.4 Agregación de resultados**
```python
# Línea 156: Limita resultados totales
all_results = all_results[:per_page]
```
✅ **Correcto**: Limita correctamente los resultados totales.

**2.5 Verificación de disponibilidad de fuentes**
```python
# Líneas 123-126: Verifica disponibilidad antes de usar
if source not in self.clients:
    logger.warning(f"Fuente '{source}' no disponible, saltando...")
    continue
```
✅ **Correcto**: Verifica disponibilidad antes de usar.

---

## 3. StockDownloadView Download Logic (`core/views.py`)

### ⚠️ Problemas Identificados

**3.1 Detección de tipo de archivo**
```python
# Líneas 5934-5955: Detección basada en Content-Type
http_content_type = response.headers.get('Content-Type', '')
```
**Problema**: Algunos servidores pueden retornar Content-Type genérico o incorrecto.

**Mejora sugerida**: Usar detección por magic bytes además de Content-Type:
```python
# Detectar por primeros bytes del archivo
file_content.seek(0)
first_bytes = file_content.read(16)
file_content.seek(0)

# Detectar tipo real
if first_bytes.startswith(b'\xFF\xD8\xFF'):
    file_extension = 'jpg'
elif first_bytes.startswith(b'\x89PNG'):
    file_extension = 'png'
# ... etc
```

**3.2 Manejo de errores de red**
```python
# Líneas 5924-5930: Descarga con timeout
response = requests.get(download_url, timeout=30, stream=True, headers=headers)
response.raise_for_status()
```
✅ **Correcto**: Tiene timeout y manejo de errores HTTP.

**Problema**: Si la descarga falla después de `raise_for_status()` pero antes de leer el contenido, no hay manejo específico.

**Mejora**: Agregar manejo de errores de lectura:
```python
try:
    file_content = BytesIO(response.content)
except MemoryError:
    # Archivo muy grande
    return JsonResponse({'success': False, 'error': 'Archivo demasiado grande'}, status=413)
```

**3.3 Tipos de contenido no soportados**
```python
# Líneas 5962-5971: Fallback según tipo de contenido
if not file_extension:
    if content_type == 'image':
        file_extension = 'jpg'
    elif content_type == 'video':
        file_extension = 'mp4'
    elif content_type == 'audio':
        file_extension = 'mp3'
    else:
        file_extension = 'bin'
```
✅ **Correcto**: Tiene fallback razonable.

**3.4 Asignación de proyecto**
```python
# Líneas 5914-5921: Verificación de proyecto
if project_id:
    try:
        project = Project.objects.get(id=project_id, owner=request.user)
    except Project.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Proyecto no encontrado'}, status=404)
```
⚠️ **Problema**: Solo verifica `owner`, pero no verifica si el usuario tiene acceso como colaborador.

**Solución**: Usar `ProjectService.user_has_access()`:
```python
from core.services import ProjectService
project = Project.objects.get(id=project_id)
if not ProjectService.user_has_access(project, request.user):
    return JsonResponse({'success': False, 'error': 'No tienes acceso a este proyecto'}, status=403)
```

**3.5 Manejo de Content-Type vacío**
```python
# Línea 6090: Usa fallback si http_content_type está vacío
content_type=http_content_type or 'image/jpeg'
```
✅ **Correcto**: Tiene fallback apropiado.

---

## 4. Frontend State Management (`templates/stock/list.html`)

### ⚠️ Problemas Identificados

**4.1 Reactividad de Alpine.js**
```javascript
// Líneas 575-598: Computed property para uniqueSources
get uniqueSources() {
    const seen = new Set();
    const result = [];
    for (const s of this.availableSources) {
        // ...
    }
    return result;
}
```
✅ **Correcto**: Usa computed property para reactividad.

**4.2 Sincronización de URL**
```javascript
// Líneas 692-776: updateUrl() actualiza URL sin recargar
window.history.pushState({}, '', newUrl);
```
✅ **Correcto**: Usa `pushState` para actualizar URL sin recargar.

**Problema potencial**: Si el usuario navega con botones del navegador, el estado puede desincronizarse.

**Solución**: Agregar listener para `popstate`:
```javascript
window.addEventListener('popstate', () => {
    this.readUrlParams();
    if (this.query) {
        this.search();
    }
});
```

**4.3 Navegación de teclado**
```javascript
// Líneas 778-825: setupKeyboardNavigation()
```
✅ **Correcto**: Verifica que no esté en input/textarea antes de procesar.

**Problema potencial**: El handler se agrega con `capture: true`, lo que puede interferir con otros handlers.

**Mejora**: Considerar usar `capture: false` y verificar el target antes de prevenir default.

**4.4 Consistencia de estado en cambio de vista**
```javascript
// Líneas 866-874: changeContentType()
changeContentType(newType) {
    this.contentType = newType;
    this.page = 1;
    this.currentIndex = 0;
    this.query = '';
    this.results = [];
    this.updateUrl({ query: '', page: 1, view: 'grid', index: 0 });
    this.loadFeaturedContent();
}
```
✅ **Correcto**: Resetea todos los estados relevantes.

**4.5 Paginación tipo infinite-scroll**
```javascript
// Líneas 1017-1069: loadMore()
```
✅ **Correcto**: Maneja tanto búsquedas como contenido destacado.

**Problema potencial**: Si `hasMore` se calcula incorrectamente, puede intentar cargar infinitamente.

**Mejora**: Agregar límite máximo de páginas o timeout:
```javascript
if (this.page > 100) { // Límite de seguridad
    this.hasMore = false;
    return;
}
```

**4.6 Guard de eventos de teclado**
```javascript
// Líneas 793-800: Verificación de target
if (target.tagName === 'INPUT' || 
    target.tagName === 'TEXTAREA' || 
    target.isContentEditable ||
    target.closest('input, textarea, [contenteditable]')) {
    return;
}
```
✅ **Correcto**: Verifica correctamente antes de procesar eventos.

---

## 5. Cache Key Generation (`stock_cache.py`)

### ⚠️ Problemas Identificados

**5.1 Normalización de query**
```python
# Línea 47: Normaliza query
normalized_query = query.lower().strip()
```
✅ **Correcto**: Normaliza correctamente.

**5.2 Ordenamiento de sources**
```python
# Línea 53: Ordena sources para consistencia
'sources': sorted(sources) if sources else None,
```
✅ **Correcto**: Ordena para evitar colisiones por orden diferente.

**5.3 Campos incluidos en hash**
```python
# Líneas 50-59: Todos los parámetros relevantes están incluidos
cache_data = {
    'query': normalized_query,
    'type': content_type,
    'sources': sorted(sources) if sources else None,
    'orientation': orientation,
    'license': license_filter,
    'audio_type': audio_type,
    'page': page,
    'per_page': per_page
}
```
✅ **Correcto**: Todos los filtros relevantes están incluidos.

**5.4 Potencial colisión de caché**
**Problema**: Si `sources` es `None` vs `[]`, generará claves diferentes aunque sean equivalentes.

**Solución**: Normalizar `None` y `[]`:
```python
'sources': sorted(sources) if sources else [],
```

**5.5 Hash determinístico**
```python
# Línea 61: Usa sort_keys=True para orden consistente
content_str = json.dumps(cache_data, sort_keys=True)
content_hash = hashlib.sha256(content_str.encode('utf-8')).hexdigest()
```
✅ **Correcto**: Usa `sort_keys=True` para garantizar orden consistente.

---

## Resumen de Problemas Críticos

### 🔴 Críticos (Deben corregirse)
1. **Pexels/Pixabay/Unsplash**: Acceso anidado sin validación completa de `None`
2. **StockService**: Posible `ZeroDivisionError` si `sources` está vacío
3. **StockDownloadView**: No verifica acceso de colaboradores a proyectos
4. **Frontend**: Falta listener para `popstate` para sincronización de navegación

### 🟡 Importantes (Deberían corregirse)
1. **Pixabay**: Construcción de URL de photographer puede incluir `None`
2. **Unsplash**: Mapeo de orientación no coincide con formato interno
3. **FreeSound**: URL de descarga requiere autenticación adicional
4. **StockDownloadView**: Detección de tipo de archivo podría mejorarse con magic bytes
5. **Cache**: Normalización de `None` vs `[]` para evitar colisiones

### 🟢 Mejoras (Opcionales)
1. Agregar límite máximo de páginas en frontend
2. Mejorar logging de errores con más contexto
3. Agregar métricas de rendimiento por fuente

---

## Recomendaciones de Implementación

### Prioridad Alta
1. Agregar validación de `None` en todos los parsers de clientes API
2. Corregir verificación de acceso a proyectos en `StockDownloadView`
3. Agregar manejo de `ZeroDivisionError` en `StockService`

### Prioridad Media
1. Mejorar detección de tipo de archivo con magic bytes
2. Agregar listener `popstate` en frontend
3. Normalizar `None` vs `[]` en generación de claves de caché

### Prioridad Baja
1. Mejorar mapeo de orientación de Unsplash
2. Documentar comportamiento de Pixabay con orientación `square`
3. Agregar límites de seguridad en paginación frontend

