# 🔧 Stack Tecnológico

> Arquitectura y tecnologías del frontend de Atenea

## 📊 Visión General

Atenea usa un enfoque **Server-Side Rendering (SSR)** con mejoras progresivas para la interactividad.

```
┌─────────────────────────────────────────────────────┐
│                    NAVEGADOR                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐   │
│  │  Tailwind  │  │    HTMX    │  │  Alpine.js │   │
│  │    CSS     │  │   AJAX     │  │  Reactivo  │   │
│  └────────────┘  └────────────┘  └────────────┘   │
└───────────────────────┬─────────────────────────────┘
                        │ HTTP/HTML
┌───────────────────────▼─────────────────────────────┐
│                   SERVIDOR                           │
│  ┌────────────────────────────────────────────┐    │
│  │          Django Templates                   │    │
│  │         (Server-Side Rendering)             │    │
│  └────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────┐    │
│  │          Django Class-Based Views           │    │
│  └────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────┐    │
│  │              Service Layer                  │    │
│  │    (VideoService, ProjectService, etc.)     │    │
│  └────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────┐    │
│  │              Django ORM                     │    │
│  └────────────────────────────────────────────┘    │
└───────────────────────┬─────────────────────────────┘
                        │ SQL
┌───────────────────────▼─────────────────────────────┐
│              SQLite / PostgreSQL                     │
└──────────────────────────────────────────────────────┘
```

---

## 🎨 Tailwind CSS

### ¿Qué es?

Framework CSS "utility-first" - clases pequeñas y componibles en lugar de escribir CSS custom.

```html
<!-- Tradicional CSS -->
<style>
.card {
    background: white;
    padding: 1.5rem;
    border-radius: 0.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
</style>
<div class="card">...</div>

<!-- Tailwind -->
<div class="bg-white p-6 rounded-lg shadow-md">...</div>
```

### Ventajas

✅ **Rápido** - No necesitas cambiar entre HTML y CSS  
✅ **Consistente** - Sistema de diseño predefinido  
✅ **No dead code** - Solo las clases que usas  
✅ **Responsive** - Mobile-first por defecto  
✅ **No naming** - No inventar nombres de clases

### Cómo lo Usamos

**Via CDN** (actual):
```html
<script src="https://cdn.tailwindcss.com"></script>
```

**Pros**: No requiere build step, funciona inmediatamente  
**Cons**: No optimizado, sin purge, archivo grande

**Con Node.js** (futuro):
```bash
npm install -D tailwindcss
npx tailwindcss -i ./src/input.css -o ./dist/output.css --watch
```

**Pros**: Optimizado, purge CSS, plugins  
**Cons**: Requiere build step

### Clases Comunes

```html
<!-- Layout -->
<div class="flex items-center justify-between">
<div class="grid grid-cols-3 gap-4">

<!-- Spacing -->
<div class="p-4 m-2">        <!-- padding, margin -->
<div class="px-6 py-3">      <!-- horizontal/vertical -->
<div class="space-y-4">      <!-- spacing entre hijos -->

<!-- Typography -->
<h1 class="text-3xl font-bold">
<p class="text-gray-600 text-sm">

<!-- Colors -->
<div class="bg-white text-black">
<div class="bg-gray-50 text-gray-900">

<!-- Borders & Shadows -->
<div class="border border-gray-200 rounded-lg shadow-md">

<!-- States -->
<button class="hover:bg-gray-100 focus:ring-2">
```

### Responsive Design

```html
<!-- Mobile first: sin prefijo = mobile -->
<div class="text-sm md:text-base lg:text-lg xl:text-xl">
    <!-- text-sm en mobile -->
    <!-- text-base en tablet (md: 768px+) -->
    <!-- text-lg en desktop (lg: 1024px+) -->
    <!-- text-xl en pantallas grandes (xl: 1280px+) -->
</div>

<div class="
    grid 
    grid-cols-1          <!-- 1 columna en mobile -->
    md:grid-cols-2       <!-- 2 columnas en tablet -->
    lg:grid-cols-3       <!-- 3 columnas en desktop -->
    xl:grid-cols-4       <!-- 4 columnas en pantallas grandes -->
    gap-4">
</div>
```

### Customización

En `base.html` o con un archivo de configuración:

```html
<style>
    /* Extender Tailwind con clases custom */
    .btn {
        @apply px-4 py-2 rounded-md transition-colors font-medium;
    }
    
    .btn-primary {
        @apply bg-black text-white hover:bg-gray-800;
    }
    
    .btn-danger {
        @apply bg-red-500 text-white hover:bg-red-600;
    }
</style>
```

---

## ⚡ HTMX

### ¿Qué es?

Biblioteca que permite hacer peticiones AJAX y actualizar el DOM usando atributos HTML, sin JavaScript.

```html
<!-- Botón que carga contenido al hacer click -->
<button hx-get="/api/projects/" hx-target="#result">
    Cargar Proyectos
</button>

<div id="result">
    <!-- Los proyectos aparecen aquí -->
</div>
```

### Ventajas

✅ **Simplicidad** - HTML en lugar de JavaScript  
✅ **SEO-friendly** - El servidor devuelve HTML  
✅ **Progressive Enhancement** - Funciona sin JS  
✅ **Menos código** - No escribes fetch/axios/jQuery  
✅ **Server-driven** - Lógica en el backend

### Cómo lo Usamos

```html
<!-- En base.html -->
<script src="https://unpkg.com/htmx.org@1.9.10"></script>
```

### Casos de Uso

**1. Polling / Auto-actualización**
```html
<div hx-get="/status/" hx-trigger="every 5s">
    Estado: {{ video.status }}
</div>
```

**2. Lazy Loading**
```html
<div hx-get="/api/videos/" hx-trigger="revealed">
    <!-- Se carga al entrar en viewport -->
</div>
```

**3. Formularios AJAX**
```html
<form hx-post="/api/create/" hx-target="#result">
    <input name="name">
    <button>Crear</button>
</form>
```

**4. Búsqueda en Tiempo Real**
```html
<input 
    hx-get="/search/" 
    hx-trigger="keyup changed delay:300ms"
    hx-target="#results">
```

### Backend (Django)

```python
# core/views.py
class VideoStatusPartialView(View):
    def get(self, request, video_id):
        video = get_object_or_404(Video, pk=video_id)
        # Retorna HTML, no JSON
        return render(request, 'partials/video_status.html', {
            'video': video
        })
```

### Debugging

```javascript
// En DevTools Console
htmx.logAll();  // Ver todas las peticiones
```

---

## 🏔️ Alpine.js

### ¿Qué es?

Framework JavaScript ligero para agregar reactividad y interactividad a tu HTML. Como Vue/React pero mucho más simple.

```html
<!-- Modal con Alpine.js -->
<div x-data="{ open: false }">
    <button @click="open = true">Abrir Modal</button>
    
    <div x-show="open" @click.away="open = false">
        <h3>Modal</h3>
        <button @click="open = false">Cerrar</button>
    </div>
</div>
```

### Ventajas

✅ **Ligero** - 15kb minified  
✅ **Declarativo** - Todo en el HTML  
✅ **Reactivo** - El DOM se actualiza automáticamente  
✅ **No build step** - Funciona con CDN  
✅ **Curva de aprendizaje baja** - Syntax simple

### Cómo lo Usamos

```html
<!-- En base.html -->
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.13.5/dist/cdn.min.js"></script>
```

### Casos de Uso

**1. Modals/Dialogs**
```html
<div x-data="{ show: false }">
    <button @click="show = true">Abrir</button>
    <div x-show="show">Modal content</div>
</div>
```

**2. Dropdowns**
```html
<div x-data="{ open: false }" @click.away="open = false">
    <button @click="open = !open">Menu</button>
    <div x-show="open">
        <a href="#">Opción 1</a>
        <a href="#">Opción 2</a>
    </div>
</div>
```

**3. Tabs**
```html
<div x-data="{ tab: 'videos' }">
    <button @click="tab = 'videos'">Videos</button>
    <button @click="tab = 'images'">Imágenes</button>
    
    <div x-show="tab === 'videos'">Contenido videos</div>
    <div x-show="tab === 'images'">Contenido imágenes</div>
</div>
```

**4. Toggle de Vista**
```html
<div x-data="{ view: 'grid' }">
    <button @click="view = 'grid'">Cuadrícula</button>
    <button @click="view = 'list'">Lista</button>
    
    <div x-show="view === 'grid'" class="grid">...</div>
    <div x-show="view === 'list'" class="space-y-2">...</div>
</div>
```

### Directivas Principales

```html
x-data="{ ... }"           <!-- Define componente con estado -->
x-show="condition"         <!-- Muestra/oculta (display) -->
x-if="condition"           <!-- Renderiza/elimina del DOM -->
@click="action"            <!-- Event listener (shorthand de x-on:click) -->
:class="expression"        <!-- Bind class (shorthand de x-bind:class) -->
x-model="variable"         <!-- Two-way binding -->
x-text="expression"        <!-- Set text content -->
x-for="item in items"      <!-- Loop -->
```

---

## 🐍 Django Templates

### Sistema de Templates

Django usa su propio lenguaje de templates para generar HTML dinámicamente en el servidor.

```html
<!-- Herencia -->
{% extends 'base.html' %}

<!-- Bloques -->
{% block title %}Mi Página{% endblock %}
{% block content %}...{% endblock %}

<!-- Variables -->
{{ variable }}
{{ object.attribute }}
{{ dict.key }}

<!-- Filtros -->
{{ text|lower }}
{{ created_at|date:"d/m/Y" }}
{{ count|pluralize }}

<!-- Tags -->
{% if condition %}...{% endif %}
{% for item in items %}...{% endfor %}
{% include 'partials/component.html' %}
{% url 'core:view_name' arg1 arg2 %}

<!-- Comentarios -->
{# Comentario #}
```

### Context (Datos del Backend)

```python
# views.py
def my_view(request):
    return render(request, 'template.html', {
        'projects': Project.objects.all(),
        'total': 10,
        'user_name': 'Juan'
    })
```

```html
<!-- template.html -->
<p>Hola {{ user_name }}</p>
<p>Total: {{ total }}</p>

{% for project in projects %}
    <div>{{ project.name }}</div>
{% endfor %}
```

### Template Inheritance

```html
<!-- base.html -->
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}Default{% endblock %}</title>
</head>
<body>
    <nav>...</nav>
    <main>
        {% block content %}{% endblock %}
    </main>
</body>
</html>

<!-- projects/index.html -->
{% extends 'base.html' %}

{% block title %}Proyectos{% endblock %}

{% block content %}
<h1>Mis Proyectos</h1>
{% endblock %}
```

---

## 🎯 Arquitectura de Decisiones

### ¿Cuándo usar qué?

| Necesitas... | Usa | Razón |
|--------------|-----|-------|
| Estilos | Tailwind | Utility-first, rápido |
| Cargar datos del servidor | HTMX | Server-driven, SEO-friendly |
| Modal, dropdown, toggle | Alpine | Estado local, no necesita servidor |
| Polling/auto-actualización | HTMX | Eficiente, server-driven |
| Formulario AJAX | HTMX | Validación en servidor, seguro |
| Filtrar lista local | Alpine | Datos ya en cliente, rápido |
| Búsqueda en servidor | HTMX | Necesita consultar DB |
| Animaciones simples | Tailwind transitions | Built-in, fácil |
| Animaciones complejas | CSS custom | Mayor control |

### HTMX vs Alpine

**Usa HTMX cuando**:
- Necesitas datos del servidor
- Quieres recargar partes de la página
- Polling/auto-actualización
- Formularios con validación server-side

**Usa Alpine cuando**:
- Estado local (UI state)
- No necesitas servidor
- Modals, dropdowns, tabs
- Toggle de vista
- Filtros locales

**Usa ambos**:
```html
<!-- HTMX para cargar datos, Alpine para mostrar/ocultar -->
<div x-data="{ showDetails: false }">
    <button @click="showDetails = !showDetails">Ver Detalles</button>
    
    <div 
        x-show="showDetails"
        hx-get="/details/" 
        hx-trigger="revealed once">
        <!-- Se carga del servidor cuando se muestra -->
    </div>
</div>
```

---

## 📊 Comparación con SPAs

| Característica | Atenea (SSR + HTMX/Alpine) | SPA (React/Vue) |
|----------------|----------------------------|-----------------|
| **Tiempo de carga inicial** | ✅ Rápido | ⚠️ Lento (bundle JS) |
| **SEO** | ✅ Excelente | ⚠️ Requiere SSR |
| **Complejidad** | ✅ Baja | ❌ Alta |
| **Build step** | ✅ No necesario | ❌ Necesario |
| **Interactividad** | ✅ Buena | ✅ Excelente |
| **State management** | ✅ Simple | ⚠️ Complejo |
| **Transiciones** | ⚠️ Básicas | ✅ Avanzadas |
| **Offline** | ❌ No | ✅ Sí (con PWA) |

---

## 🔄 Flujo de Datos

```
1. Usuario hace click
   ↓
2. HTMX hace request al servidor
   ↓
3. Django View procesa request
   ↓
4. Django ORM consulta DB
   ↓
5. Service Layer procesa lógica
   ↓
6. Django Template renderiza HTML
   ↓
7. HTMX recibe HTML
   ↓
8. HTMX actualiza el DOM
   ↓
9. Alpine reactiva (si hay x-data)
   ↓
10. Tailwind aplica estilos
```

---

## 📦 Dependencias

### Python (Backend)
```txt
Django==5.2.7
django-tailwind==4.2.0
django-browser-reload==1.21.0
python-decouple==3.8
```

### CDN (Frontend)
```html
<!-- Tailwind CSS -->
<script src="https://cdn.tailwindcss.com"></script>

<!-- HTMX -->
<script src="https://unpkg.com/htmx.org@1.9.10"></script>

<!-- Alpine.js -->
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.13.5/dist/cdn.min.js"></script>
```

---

## 🚀 Performance

### Optimizaciones Actuales

✅ **Server-side rendering** - HTML ya renderizado  
✅ **CDN para librerías** - Cache global  
✅ **Polling inteligente** - Solo cuando es necesario  
✅ **Lazy loading** - `hx-trigger="revealed"`  
✅ **Minimal JavaScript** - Solo lo necesario

### Mejoras Futuras

- [ ] Compilar Tailwind (purge CSS)
- [ ] Service Worker para cache
- [ ] Lazy loading de imágenes
- [ ] Comprimir respuestas (Gzip)
- [ ] CDN para assets estáticos

---

## 📚 Recursos

### Tailwind CSS
- [Docs](https://tailwindcss.com/docs)
- [Cheat Sheet](https://nerdcave.com/tailwind-cheat-sheet)
- [UI Components](https://tailwindui.com/)

### HTMX
- [Docs](https://htmx.org/docs/)
- [Examples](https://htmx.org/examples/)
- [Essays](https://htmx.org/essays/)

### Alpine.js
- [Docs](https://alpinejs.dev/)
- [Examples](https://alpinejs.dev/start-here)
- [Plugins](https://alpinejs.dev/plugins)

### Django Templates
- [Docs](https://docs.djangoproject.com/en/5.2/ref/templates/)
- [Built-in Tags](https://docs.djangoproject.com/en/5.2/ref/templates/builtins/)

---

## 🎓 Aprendizaje

### Nuevo en el Stack?

1. **Día 1**: Tailwind CSS basics
   - [Tailwind CSS in 100 Seconds](https://www.youtube.com/watch?v=mr15Xzb1Ook)
   - Practica con las clases comunes

2. **Día 2**: HTMX basics
   - [HTMX in 100 Seconds](https://www.youtube.com/watch?v=r-GSGH2RxJs)
   - Crea un ejemplo de polling

3. **Día 3**: Alpine.js basics
   - [Alpine.js in 100 Seconds](https://www.youtube.com/watch?v=r5iWCtfltso)
   - Crea un modal desde cero

4. **Día 4-5**: Integración
   - Lee el código existente del proyecto
   - Haz un componente pequeño

---

¡Ya estás listo para desarrollar en Atenea! 🚀

