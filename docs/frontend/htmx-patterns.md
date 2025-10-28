# ⚡ Patrones HTMX

> Guía de uso de HTMX en Atenea

## 🎯 ¿Qué es HTMX?

HTMX permite agregar interactividad AJAX moderna a tu HTML usando atributos, sin escribir JavaScript.

### Filosofía
- Extiende HTML con nuevos atributos
- El servidor responde con HTML (no JSON)
- Intercambias partes de la página, no toda la página
- Ideal para aplicaciones server-side rendered

---

## 📚 Patrones Usados en Atenea

### 1. Auto-actualización / Polling

Actualizar contenido automáticamente cada X segundos.

**Caso de uso**: Ver el estado de un video procesándose.

```html
<!-- Cada 5 segundos, hace GET y reemplaza el div -->
<div 
    hx-get="{% url 'core:video_status_partial' video.id %}" 
    hx-trigger="every 5s"
    hx-swap="outerHTML">
    
    <span class="badge">Estado: {{ video.status }}</span>
</div>
```

**Backend (Django)**:
```python
# core/views.py
class VideoStatusPartialView(View):
    def get(self, request, video_id):
        video = get_object_or_404(Video, pk=video_id)
        return render(request, 'partials/video_status.html', {'video': video})
```

**URLs**:
```python
# core/urls.py
path('videos/<int:video_id>/status-partial/', 
     views.VideoStatusPartialView.as_view(), 
     name='video_status_partial'),
```

#### Variantes

**Parar polling cuando esté completo**:
```html
<div 
    hx-get="/status/" 
    hx-trigger="every 5s [status != 'completed']"
    hx-swap="outerHTML"
    data-status="{{ video.status }}">
    <!-- Estado -->
</div>
```

**Polling más lento después de un tiempo**:
```html
<div 
    hx-get="/status/" 
    hx-trigger="every 5s, load delay:30s">
    <!-- Cada 5s, pero empieza después de 30s -->
</div>
```

---

### 2. Click para Cargar

Cargar contenido al hacer click en un botón.

**Caso de uso**: Cargar más proyectos (paginación).

```html
<button 
    hx-get="{% url 'core:load_more_projects' %}?page={{ page }}" 
    hx-target="#projects-list"
    hx-swap="beforeend"
    class="btn">
    Cargar Más
</button>

<div id="projects-list">
    <!-- Proyectos se agregan aquí -->
</div>
```

**Backend**:
```python
def load_more_projects(request):
    page = request.GET.get('page', 1)
    projects = Project.objects.all()[page*10:(page+1)*10]
    return render(request, 'partials/projects_list.html', {
        'projects': projects,
        'page': page + 1
    })
```

---

### 3. Formularios AJAX

Enviar formularios sin recargar la página.

**Caso de uso**: Crear un proyecto.

```html
<form 
    hx-post="{% url 'core:project_create' %}"
    hx-target="#projects-list"
    hx-swap="afterbegin">
    
    {% csrf_token %}
    <input type="text" name="name" placeholder="Nombre del proyecto">
    <button type="submit">Crear</button>
</form>

<div id="projects-list">
    <!-- Nuevo proyecto aparece aquí -->
</div>
```

**Backend**:
```python
def project_create(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save()
            # Responde con el HTML del proyecto
            return render(request, 'partials/project_card.html', {
                'project': project
            })
    return render(request, 'projects/create.html', {'form': form})
```

---

### 4. Confirmación Inline

Mostrar confirmación antes de eliminar.

```html
<button 
    hx-delete="{% url 'core:video_delete' video.id %}"
    hx-confirm="¿Eliminar este video?"
    hx-target="closest .video-card"
    hx-swap="outerHTML swap:1s"
    class="btn btn-danger">
    Eliminar
</button>
```

**Backend**:
```python
def video_delete(request, video_id):
    video = get_object_or_404(Video, pk=video_id)
    video.delete()
    return HttpResponse('')  # Respuesta vacía = elimina el elemento
```

---

### 5. Loading States

Mostrar indicador de carga mientras se procesa.

```html
<button 
    hx-post="/api/generate-video/"
    hx-indicator="#loading">
    Generar Video
</button>

<div id="loading" class="htmx-indicator">
    <span class="animate-spin">⚙️</span> Generando...
</div>

<style>
.htmx-indicator { display: none; }
.htmx-request .htmx-indicator { display: block; }
</style>
```

**Con CSS de Tailwind**:
```html
<button 
    hx-post="/api/action/"
    hx-indicator=".my-loader"
    class="btn">
    Acción
</button>

<div class="my-loader hidden htmx-indicator">
    Cargando...
</div>

<style>
.htmx-request .htmx-indicator { display: block !important; }
</style>
```

---

### 6. Búsqueda en Tiempo Real

Buscar mientras escribes.

```html
<input 
    type="search"
    name="q"
    placeholder="Buscar proyectos..."
    hx-get="{% url 'core:search_projects' %}"
    hx-trigger="keyup changed delay:300ms"
    hx-target="#search-results">

<div id="search-results">
    <!-- Resultados aparecen aquí -->
</div>
```

**Backend**:
```python
def search_projects(request):
    query = request.GET.get('q', '')
    projects = Project.objects.filter(name__icontains=query)[:10]
    return render(request, 'partials/search_results.html', {
        'projects': projects
    })
```

---

### 7. Infinite Scroll

Cargar más contenido al hacer scroll.

```html
<div id="projects-list">
    {% for project in projects %}
        <div class="project-card">...</div>
    {% endfor %}
    
    <!-- Trigger para cargar más -->
    <div 
        hx-get="{% url 'core:load_more' %}?page={{ next_page }}"
        hx-trigger="revealed"
        hx-target="#projects-list"
        hx-swap="beforeend">
        <span class="loading">Cargando más...</span>
    </div>
</div>
```

`revealed` se activa cuando el elemento entra en el viewport.

---

### 8. Actualizar Múltiples Targets

Actualizar varias partes de la página a la vez.

```html
<button 
    hx-post="/api/action/"
    hx-target="#result"
    hx-swap="innerHTML"
    hx-include="[name='filter']">
    Aplicar Filtro
</button>

<div id="result">
    <!-- Resultado aquí -->
</div>
```

**Con respuesta múltiple (Out of Band Swaps)**:
```python
def action(request):
    # Backend devuelve HTML con múltiples elementos
    return HttpResponse("""
        <div id="result">Resultado principal</div>
        <div id="stats" hx-swap-oob="true">
            <span>Stats actualizados</span>
        </div>
    """)
```

```html
<div id="result"></div>
<div id="stats"></div>
<!-- Ambos se actualizan -->
```

---

## 🎨 Atributos HTMX Principales

| Atributo | Descripción | Ejemplo |
|----------|-------------|---------|
| `hx-get` | GET request | `hx-get="/api/data"` |
| `hx-post` | POST request | `hx-post="/api/create"` |
| `hx-delete` | DELETE request | `hx-delete="/api/delete/1"` |
| `hx-put` | PUT request | `hx-put="/api/update/1"` |
| `hx-trigger` | Cuándo activar | `hx-trigger="click"` |
| `hx-target` | Dónde poner respuesta | `hx-target="#result"` |
| `hx-swap` | Cómo reemplazar | `hx-swap="innerHTML"` |
| `hx-indicator` | Loading indicator | `hx-indicator="#loading"` |
| `hx-confirm` | Confirmación | `hx-confirm="¿Seguro?"` |
| `hx-include` | Incluir inputs | `hx-include="[name='filter']"` |

---

## 🎯 hx-swap Opciones

| Valor | Descripción | Ejemplo |
|-------|-------------|---------|
| `innerHTML` | Reemplaza contenido interno (default) | `<div>nuevo</div>` |
| `outerHTML` | Reemplaza elemento completo | Reemplaza `<div>...</div>` |
| `beforebegin` | Antes del elemento | `<nuevo/><div>...</div>` |
| `afterbegin` | Inicio del contenido | `<div><nuevo/>...</div>` |
| `beforeend` | Final del contenido | `<div>...<nuevo/></div>` |
| `afterend` | Después del elemento | `<div>...</div><nuevo/>` |
| `delete` | Elimina el target | - |
| `none` | No hace swap | - |

---

## 🎯 hx-trigger Opciones

```html
<!-- Click (default para botones) -->
<button hx-get="/api" hx-trigger="click">

<!-- Cada X segundos -->
<div hx-get="/api" hx-trigger="every 5s">

<!-- Al cargar la página -->
<div hx-get="/api" hx-trigger="load">

<!-- Input con delay -->
<input hx-get="/search" hx-trigger="keyup changed delay:300ms">

<!-- Cuando se hace visible -->
<div hx-get="/api" hx-trigger="revealed">

<!-- Múltiples triggers -->
<div hx-get="/api" hx-trigger="click, every 30s">

<!-- Con condición -->
<div hx-get="/api" hx-trigger="every 5s [status != 'completed']">
```

---

## 🛠️ Debugging HTMX

### 1. Ver Todas las Peticiones

```javascript
// En DevTools Console
htmx.logAll();
```

### 2. Extension HTMX

Agregar el atributo `hx-ext="debug"` para ver logs:
```html
<body hx-ext="debug">
```

### 3. DevTools Network Tab

- Abre DevTools (F12)
- Ve a Network
- Filtra por "XHR" o "Fetch"
- Verás todas las peticiones HTMX

### 4. Eventos HTMX

Escuchar eventos de HTMX:
```javascript
document.body.addEventListener('htmx:afterSwap', (event) => {
    console.log('Swap completado:', event.detail);
});
```

Eventos disponibles:
- `htmx:beforeRequest`
- `htmx:afterRequest`
- `htmx:beforeSwap`
- `htmx:afterSwap`

---

## 🎨 Patrones Avanzados

### Optimistic UI

Actualizar la UI inmediatamente, luego confirmar con el servidor:

```html
<button 
    hx-post="/api/like/"
    hx-target="#like-count"
    onclick="this.disabled=true">
    ❤️ Like
</button>

<span id="like-count">{{ likes }}</span>
```

### Transiciones Suaves

```html
<div 
    hx-get="/api/data"
    hx-swap="innerHTML swap:1s">
    <!-- Fade out viejo, fade in nuevo -->
</div>
```

### Headers Personalizados

```html
<button 
    hx-post="/api/action"
    hx-headers='{"X-Custom-Header": "value"}'>
    Acción
</button>
```

---

## ⚠️ Consideraciones

### CSRF Token (Django)

HTMX automáticamente incluye el CSRF token de Django si está en el formulario:
```html
<form hx-post="/api/create">
    {% csrf_token %}
    <!-- campos -->
</form>
```

Para peticiones fuera de formularios:
```javascript
// En base.html
document.body.addEventListener('htmx:configRequest', (event) => {
    event.detail.headers['X-CSRFToken'] = getCookie('csrftoken');
});
```

### SEO

HTMX es server-side rendered, así que el SEO es bueno. Pero:
- Asegúrate de que las URLs principales sean accesibles sin JavaScript
- Usa progressive enhancement

### Performance

- No hacer polling a más de 1 req/s
- Usar `hx-trigger="revealed"` para lazy loading
- Cachear respuestas en el backend cuando sea posible

---

## 📚 Recursos

- [HTMX Docs](https://htmx.org/docs/)
- [HTMX Examples](https://htmx.org/examples/)
- [HTMX + Django](https://htmx.org/docs/#django)

---

## 🚀 Siguientes Pasos

- Lee [Patrones Alpine.js](./alpine-patterns.md)
- Revisa [Componentes](./components.md) para ver ejemplos reales
- Experimenta con los ejemplos en tu proyecto local

