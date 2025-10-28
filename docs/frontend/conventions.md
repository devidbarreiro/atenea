# 📏 Convenciones de Código Frontend

> Estándares y mejores prácticas para el desarrollo frontend en Atenea

## 🎯 Filosofía

1. **Consistencia** - El código debe verse como si lo escribiera una sola persona
2. **Simplicidad** - Prefiere soluciones simples sobre complejas
3. **Mantenibilidad** - Escribe código que otros (y tu yo futuro) puedan entender
4. **Performance** - Pero no prematuramente

---

## 📁 Estructura de Archivos

### Templates

```
templates/
├── base.html                    # Template base (navbar, footer, scripts)
├── base_item_detail.html        # Base para páginas de detalle
├── dashboard/                   # Un directorio por sección
│   └── index.html              # Vista principal
├── projects/                    # CRUD de proyectos
│   ├── create.html
│   ├── detail.html
│   └── delete.html
├── videos/                      # CRUD de videos
│   ├── create.html
│   ├── detail.html
│   └── delete.html
├── partials/                    # Componentes reutilizables
│   ├── video_status.html       # Componente específico
│   ├── confirm_modal.html      # Componente genérico
│   └── ...
└── includes/                    # Layouts y estructuras
    └── media_card.html
```

### Naming Conventions

**Templates**:
- `{modelo}_{accion}.html` → `project_create.html`, `video_detail.html`
- Siempre en `snake_case`
- Nombres descriptivos y específicos

**Partials**:
- `{componente}_{variante}.html` → `button_primary.html`
- `{funcionalidad}.html` → `video_status.html`

**Includes**:
- `{tipo}_{variante}.html` → `media_card.html`

---

## 🎨 HTML y Templates Django

### Estructura General

```html
{% extends 'base.html' %}

{% block title %}Título de la Página{% endblock %}

{% block content %}
<div class="container">
    <h1 class="text-3xl font-bold mb-6">Título</h1>
    
    <!-- Contenido -->
</div>
{% endblock %}

{% block extra_js %}
<script>
// JavaScript específico de esta página
</script>
{% endblock %}
```

### Indentación

- **4 espacios** (no tabs)
- Indentar bloques de Django y HTML correctamente

```html
<!-- ✅ BIEN -->
<div class="container">
    {% if projects %}
        {% for project in projects %}
            <div class="card">
                {{ project.name }}
            </div>
        {% endfor %}
    {% endif %}
</div>

<!-- ❌ MAL -->
<div class="container">
{% if projects %}
{% for project in projects %}
<div class="card">
{{ project.name }}
</div>
{% endfor %}
{% endif %}
</div>
```

### Comentarios

```html
{# Comentario de Django (no se renderiza) #}

{% comment %}
Comentario de bloque
más largo
{% endcomment %}

<!-- Comentario HTML (sí se renderiza) -->
```

**Cuándo usar cada uno**:
- `{# #}` - Para notas de desarrollo, TODOs
- `{% comment %}` - Para desactivar temporalmente código
- `<!-- -->` - Para contenido que debe estar en el HTML final

### Orden de Atributos HTML

```html
<div 
    id="mi-id"
    class="clases tailwind"
    x-data="{ ... }"
    hx-get="/api/"
    hx-trigger="click"
    data-custom="value">
</div>
```

Orden:
1. `id`
2. `class`
3. Alpine.js (`x-data`, `x-show`, etc.)
4. HTMX (`hx-*`)
5. Data attributes (`data-*`)
6. Otros atributos

---

## 🎨 Tailwind CSS

### Organización de Clases

Agrupa clases relacionadas:

```html
<!-- ✅ BIEN: Agrupadas lógicamente -->
<button class="
    bg-black text-white 
    hover:bg-gray-800 
    px-4 py-2 
    rounded-md 
    shadow-sm 
    transition-colors">
    Botón
</button>

<!-- ❌ MAL: Sin orden -->
<button class="px-4 bg-black shadow-sm text-white py-2 rounded-md hover:bg-gray-800">
```

### Orden Recomendado

1. Layout (`flex`, `grid`, `block`)
2. Position (`relative`, `absolute`)
3. Display (`hidden`, `flex`)
4. Size (`w-full`, `h-screen`)
5. Spacing (`p-4`, `m-2`)
6. Typography (`text-lg`, `font-bold`)
7. Colors (`bg-white`, `text-black`)
8. Borders (`border`, `rounded`)
9. Effects (`shadow`, `opacity`)
10. Transitions (`transition`, `duration`)
11. States (`hover:`, `focus:`)

### Responsive Design

Mobile-first approach:

```html
<!-- ✅ BIEN: Mobile first -->
<div class="
    grid grid-cols-1 
    md:grid-cols-2 
    lg:grid-cols-3 
    xl:grid-cols-4 
    gap-4">
</div>

<!-- Breakpoints: sm (640px), md (768px), lg (1024px), xl (1280px) -->
```

### Reutilización

Para estilos repetidos muchas veces, considera extraer a `base.html`:

```html
<style>
    .btn {
        @apply px-4 py-2 rounded-md transition-colors;
    }
    .btn-primary {
        @apply bg-black text-white hover:bg-gray-800;
    }
</style>
```

Pero usa con moderación - prefiere clases directas de Tailwind.

---

## ⚡ HTMX

### Naming

Atributos en orden:
1. `hx-get/post/delete/put`
2. `hx-target`
3. `hx-swap`
4. `hx-trigger`
5. `hx-indicator`
6. Otros

```html
<button 
    hx-post="/api/create/"
    hx-target="#result"
    hx-swap="innerHTML"
    hx-trigger="click"
    hx-indicator="#loading">
    Crear
</button>
```

### URLs

Siempre usar `{% url %}`:

```html
<!-- ✅ BIEN -->
<div hx-get="{% url 'core:video_status_partial' video.id %}">

<!-- ❌ MAL -->
<div hx-get="/videos/{{ video.id }}/status/">
```

### Polling

Convenciones de tiempo:
- Crítico: `every 2s`
- Normal: `every 5s`
- Background: `every 30s` o `load delay:30s`

```html
<!-- ✅ BIEN: 5s es un buen balance -->
<div hx-get="/status/" hx-trigger="every 5s">

<!-- ❌ MAL: Muy frecuente -->
<div hx-get="/status/" hx-trigger="every 1s">
```

---

## 🏔️ Alpine.js

### Naming

#### Variables: camelCase

```html
<!-- ✅ BIEN -->
<div x-data="{ 
    isOpen: false,
    selectedItem: null,
    showConfirmDialog: false
}">

<!-- ❌ MAL -->
<div x-data="{ 
    is_open: false,
    SelectedItem: null
}">
```

#### Métodos: camelCase con verbo

```html
<div x-data="{
    showModal() { ... },
    hideModal() { ... },
    submitForm() { ... }
}">
```

### Organización

Para componentes complejos, divide en métodos:

```html
<!-- ✅ BIEN -->
<div x-data="{
    form: { name: '', email: '' },
    errors: {},
    
    validate() {
        // Validación
    },
    
    async submit() {
        if (!this.validate()) return;
        // Submit
    }
}">

<!-- ❌ MAL: Todo inline -->
<button @click="if (form.name && form.email && form.name.length > 3) { /* ... */ }">
```

### x-cloak

Siempre usa `x-cloak` para evitar flash de contenido:

```html
<div x-data="{ open: false }" x-cloak>
    <div x-show="open">...</div>
</div>

<style>
[x-cloak] { display: none !important; }
</style>
```

---

## 🎨 CSS Custom

### Cuándo Escribir CSS

Solo cuando Tailwind no sea suficiente:
- Animaciones complejas
- Estilos muy específicos
- Hacks de navegador

### Ubicación

1. **Estilos globales**: `base.html` en el `<style>` tag
2. **Estilos de página**: `{% block extra_css %}` en la página específica

```html
<!-- base.html -->
<style>
    @keyframes slideIn {
        from { transform: translateX(400px); }
        to { transform: translateX(0); }
    }
    
    .message {
        animation: slideIn 0.3s ease;
    }
    
    [x-cloak] { display: none !important; }
</style>
```

### BEM (si es necesario)

```css
/* Bloque */
.card { ... }

/* Elemento */
.card__title { ... }
.card__body { ... }

/* Modificador */
.card--featured { ... }
```

Pero recuerda: **Tailwind primero, CSS custom solo si es necesario.**

---

## 📝 JavaScript

### Ubicación

1. **Global**: `static/js/main.js`
2. **Página específica**: `{% block extra_js %}`

```html
{% block extra_js %}
<script>
    // JavaScript específico de esta página
    document.addEventListener('DOMContentLoaded', () => {
        console.log('Página cargada');
    });
</script>
{% endblock %}
```

### Estilo

```javascript
// ✅ BIEN: const/let, camelCase
const videoId = 123;
let isProcessing = false;

function fetchVideoStatus() {
    // ...
}

// ❌ MAL: var, snake_case
var video_id = 123;
```

### Event Listeners

Preferir Alpine o HTMX sobre JavaScript manual:

```html
<!-- ✅ BIEN: Alpine -->
<button @click="handleClick()">

<!-- ✅ BIEN: HTMX -->
<button hx-post="/api/">

<!-- ⚠️ SOLO SI NECESARIO: JavaScript manual -->
<button id="my-button">
<script>
document.getElementById('my-button').addEventListener('click', ...);
</script>
```

---

## 🎯 Componentes Reutilizables

### Documentación

Siempre documenta parámetros:

```html
{# templates/partials/status_badge.html #}
{# 
Componente: Badge de Estado

Parámetros:
- status (requerido): 'pending' | 'processing' | 'completed' | 'error'
- text (opcional): Texto a mostrar (default: status traducido)
- size (opcional): 'sm' | 'md' | 'lg' (default: 'md')

Ejemplo:
{% include 'partials/status_badge.html' with status='completed' size='lg' %}
#}

<span class="badge badge-{{ status }} {{ size }}">
    {{ text|default:status }}
</span>
```

### Parámetros con Defaults

```html
<!-- Usar filter default -->
<div class="{{ container_class|default:'container mx-auto' }}">
    <h1 class="{{ title_class|default:'text-3xl font-bold' }}">
        {{ title|default:"Sin título" }}
    </h1>
</div>
```

---

## 🎨 Paleta de Colores

Usa colores consistentes:

```html
<!-- Primarios -->
bg-black           text-white          /* Botones principales */
bg-white           text-gray-900       /* Fondos */
bg-gray-50         text-gray-600       /* Fondos secundarios */

<!-- Estados -->
bg-green-500       text-white          /* Success / Completado */
bg-yellow-500      text-white          /* Warning / Procesando */
bg-red-500         text-white          /* Error / Danger */
bg-blue-500        text-white          /* Info / Secondary */
bg-purple-600      text-white          /* Accent */

<!-- Neutrales -->
bg-gray-100        hover:bg-gray-200   /* Hover states */
border-gray-200    border-gray-300     /* Borders */
text-gray-500      text-gray-600       /* Text secundario */
```

---

## 📐 Espaciado

Sistema de 8pt grid:

```html
<!-- Spacing interno: p-{n} -->
p-2  = 8px    <!-- Pequeño -->
p-4  = 16px   <!-- Mediano (DEFAULT) -->
p-6  = 24px   <!-- Grande -->
p-8  = 32px   <!-- Extra grande -->

<!-- Spacing entre elementos: gap-{n}, space-y-{n} -->
gap-4          <!-- Grid/Flex gap -->
space-y-4      <!-- Vertical spacing -->
space-x-4      <!-- Horizontal spacing -->
```

---

## 🚨 Estados de UI

### Loading States

```html
<button hx-post="/api/" hx-indicator="#loading">
    <span>Crear</span>
    <span id="loading" class="htmx-indicator animate-spin">⚙️</span>
</button>
```

### Empty States

```html
{% if items %}
    <!-- Lista -->
{% else %}
    <div class="text-center py-12">
        <div class="text-6xl mb-4 opacity-30">📭</div>
        <h3 class="text-xl font-bold mb-2">No hay items</h3>
        <p class="text-gray-600 mb-4">Crea tu primer item</p>
        <a href="{% url 'create' %}" class="btn btn-primary">
            Crear Item
        </a>
    </div>
{% endif %}
```

### Error States

```html
{% if error %}
<div class="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
    <div class="flex items-center gap-2">
        <svg class="w-5 h-5">...</svg>
        <span>{{ error }}</span>
    </div>
</div>
{% endif %}
```

---

## ✅ Checklist de Code Review

Antes de hacer commit:

- [ ] Indentación consistente (4 espacios)
- [ ] Nombres descriptivos (no `x`, `tmp`, `data`)
- [ ] Comentarios donde sea necesario
- [ ] Clases de Tailwind ordenadas
- [ ] URLs usando `{% url %}`
- [ ] CSRF token en formularios
- [ ] `x-cloak` en componentes Alpine
- [ ] Estados de loading/error/empty
- [ ] Responsive (probado en mobile)
- [ ] Sin errores en consola

---

## 🚀 Recursos

- [Tailwind CSS Docs](https://tailwindcss.com/docs)
- [HTMX Docs](https://htmx.org/docs/)
- [Alpine.js Docs](https://alpinejs.dev/)
- [Django Templates](https://docs.djangoproject.com/en/5.2/ref/templates/)

---

## 📞 ¿Dudas?

Si no estás seguro de cómo escribir algo:
1. Busca código similar en el proyecto
2. Sigue estas convenciones
3. Pregunta al equipo en caso de duda

