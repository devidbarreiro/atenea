# 🧩 Componentes Reutilizables

> Biblioteca de componentes del proyecto Atenea

## 📦 Componentes Disponibles

Todos los componentes están en `templates/partials/` y se incluyen con:
```html
{% include 'partials/nombre_componente.html' with param1=value1 %}
```

---

## 1. Video Status Badge (HTMX Polling)

**Archivo**: `templates/partials/video_status.html`

Badge que muestra el estado de un video y se actualiza automáticamente cada 5 segundos usando HTMX.

### Uso

```html
{% include 'partials/video_status.html' with video=video %}
```

### Parámetros

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `video` | Video object | Sí | Objeto Video del modelo |

### Estados

- **✅ Completado** - `completed` - Badge verde
- **⚙️ Procesando** - `processing` - Badge amarillo con spinner animado
- **❌ Error** - `error` - Badge rojo
- **⏳ Pendiente** - `pending` - Badge gris

### Ejemplo Completo

```html
<div class="flex items-center gap-4">
    <span>{{ video.title }}</span>
    {% include 'partials/video_status.html' with video=video %}
</div>
```

### Cómo Funciona

```html
<div 
    hx-get="{% url 'core:video_status_partial' video.id %}" 
    hx-trigger="every 5s"
    hx-swap="outerHTML">
    <!-- Badge según estado -->
</div>
```

1. `hx-get` - Hace GET a la URL cada 5 segundos
2. `hx-trigger="every 5s"` - Polling automático
3. `hx-swap="outerHTML"` - Reemplaza todo el div
4. **Sin JavaScript custom** - Todo manejado por HTMX

---

## 2. Image Status Badge (HTMX Polling)

**Archivo**: `templates/partials/image_status.html`

Similar al video status pero para imágenes.

### Uso

```html
{% include 'partials/image_status.html' with image=image %}
```

### Parámetros

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `image` | Image object | Sí | Objeto Image del modelo |

---

## 3. Script Status Badge (HTMX Polling)

**Archivo**: `templates/partials/script_status.html`

Badge para el estado de generación de guiones.

### Uso

```html
{% include 'partials/script_status.html' with script=script %}
```

---

## 4. Modal de Confirmación (Alpine.js)

**Archivo**: `templates/partials/confirm_modal.html`

Modal interactivo para confirmar acciones destructivas (eliminar, etc.) usando Alpine.js.

### Uso

```html
{% include 'partials/confirm_modal.html' with 
    button_text="Eliminar Proyecto"
    button_class="bg-red-500 text-white px-4 py-2 rounded-md"
    modal_title="¿Confirmar eliminación?"
    modal_message="Esta acción no se puede deshacer."
    confirm_text="Eliminar"
    action_url=request.path
%}
```

### Parámetros

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `button_text` | String | "Eliminar" | Texto del botón trigger |
| `button_class` | String | Clases default | Clases CSS del botón |
| `modal_title` | String | "¿Estás seguro?" | Título del modal |
| `modal_message` | String | "Esta acción no se puede deshacer." | Mensaje de confirmación |
| `confirm_text` | String | "Confirmar" | Texto del botón de confirmación |
| `action_url` | String | - | URL del formulario POST |

### Características

- ✨ Animaciones suaves (x-transition)
- 🖱️ Click fuera para cerrar
- ⌨️ ESC para cerrar (x-on:keydown.escape)
- 📱 Responsive
- 🎨 Overlay con backdrop-blur

### Ejemplo: Eliminar Proyecto

```html
<div class="flex gap-2">
    <a href="{% url 'core:project_detail' project.id %}" 
       class="btn btn-ghost">
        Cancelar
    </a>
    
    {% include 'partials/confirm_modal.html' with 
        button_text="Eliminar Proyecto" 
        modal_title="¿Eliminar proyecto?" 
        modal_message="Se eliminarán todos los videos e imágenes asociados."
        action_url=request.path
    %}
</div>
```

### Cómo Funciona

```html
<div x-data="{ open: false }" x-cloak>
    <!-- Botón trigger -->
    <button @click="open = true">...</button>
    
    <!-- Modal Overlay -->
    <div x-show="open" @click.self="open = false"
         x-transition:enter="..." x-transition:leave="...">
        <!-- Modal Box -->
        <div>
            <h3>{{ modal_title }}</h3>
            <p>{{ modal_message }}</p>
            <form method="post" action="{{ action_url }}">
                {% csrf_token %}
                <button type="submit">Confirmar</button>
            </form>
        </div>
    </div>
</div>
```

---

## 5. Media Card

**Archivo**: `templates/includes/media_card.html`

Card reutilizable para mostrar videos o imágenes en grid.

### Uso

```html
{% include 'includes/media_card.html' with 
    item=video
    item_type="video"
    detail_url=video_detail_url
%}
```

### Parámetros

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `item` | Video/Image | Sí | Objeto a mostrar |
| `item_type` | String | Sí | "video" o "image" |
| `detail_url` | URL | Sí | URL al detalle |

---

## 6. Breadcrumbs

Breadcrumbs se pasan desde el backend a través del contexto.

### Uso en Backend (views.py)

```python
class ProjectDetailView(BreadcrumbMixin, DetailView):
    def get_breadcrumbs(self):
        return [
            {'label': 'Dashboard', 'url': reverse('core:dashboard')},
            {'label': 'Proyectos', 'url': None},  # Sin URL = activo
        ]
```

### Renderizado en Template (base.html)

```html
{% if breadcrumbs %}
<div class="flex items-center space-x-2 text-sm text-gray-500">
    {% for crumb in breadcrumbs %}
        {% if crumb.url %}
            <a href="{{ crumb.url }}">{{ crumb.label }}</a>
            <svg>→</svg>
        {% else %}
            <span class="font-medium">{{ crumb.label }}</span>
        {% endif %}
    {% endfor %}
</div>
{% endif %}
```

---

## 🎨 Crear Tu Propio Componente

### 1. Crear el Archivo

```bash
# Crear nuevo partial
touch templates/partials/mi_componente.html
```

### 2. Estructura Básica

```html
<!-- templates/partials/mi_componente.html -->

{# Documentación del componente #}
{# Parámetros:
   - param1: Descripción
   - param2: Descripción (opcional, default: valor)
#}

<div class="mi-componente">
    <h3>{{ title|default:"Título por defecto" }}</h3>
    <p>{{ description }}</p>
    
    {% if show_actions %}
    <div class="actions">
        <button class="btn">Acción</button>
    </div>
    {% endif %}
</div>
```

### 3. Usar el Componente

```html
{% include 'partials/mi_componente.html' with 
    title="Mi Título"
    description="Mi descripción"
    show_actions=True
%}
```

---

## 🎯 Patrones Comunes

### Loading States

```html
<div hx-get="/api/data/" hx-indicator="#loading">
    <!-- Contenido -->
</div>

<div id="loading" class="htmx-indicator">
    <span class="animate-spin">⚙️</span> Cargando...
</div>

<style>
.htmx-indicator { display: none; }
.htmx-request .htmx-indicator { display: block; }
</style>
```

### Empty States

```html
{% if items %}
    <!-- Lista de items -->
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

### Toggle de Vista (Grid/Lista)

```html
<div x-data="{ view: 'grid' }">
    <!-- Botones toggle -->
    <div class="inline-flex rounded-lg border">
        <button @click="view = 'grid'" 
                :class="view === 'grid' ? 'bg-gray-100' : ''">
            ⊞ Cuadrícula
        </button>
        <button @click="view = 'list'" 
                :class="view === 'list' ? 'bg-gray-100' : ''">
            ☰ Lista
        </button>
    </div>
    
    <!-- Vista Grid -->
    <div x-show="view === 'grid'" class="grid grid-cols-3 gap-4">
        <!-- Cards -->
    </div>
    
    <!-- Vista Lista -->
    <div x-show="view === 'list'" class="space-y-2">
        <!-- Rows -->
    </div>
</div>
```

---

## 📏 Convenciones

### Nombres de Archivos
- `snake_case.html` → `video_status.html`
- Descriptivos y específicos
- `partials/` para componentes reutilizables
- `includes/` para layouts/estructuras

### Parámetros
- Siempre documentar parámetros en comentarios
- Proporcionar defaults cuando sea posible: `{{ title|default:"Default" }}`
- Usar nombres descriptivos: `button_text` en lugar de `text`

### Estilos
- Usar clases de Tailwind directamente
- Agrupar clases relacionadas: `"bg-white shadow-lg rounded-lg p-6"`
- Para hover/focus: `"hover:shadow-xl focus:ring-2"`

### Accessibility
- Usar etiquetas semánticas: `<button>`, `<nav>`, `<main>`
- Agregar `aria-label` cuando sea necesario
- Asegurar contraste de colores adecuado

---

## 🚀 Siguientes Pasos

- Lee [Patrones HTMX](./htmx-patterns.md) para interactividad
- Lee [Patrones Alpine.js](./alpine-patterns.md) para componentes reactivos
- Revisa [Convenciones](./conventions.md) para mejores prácticas

