# 🏔️ Patrones Alpine.js

> Guía de uso de Alpine.js en Atenea

## 🎯 ¿Qué es Alpine.js?

Alpine.js es un framework JavaScript minimalista para agregar interactividad reactiva a tu HTML. Piensa en ello como "jQuery para el mundo moderno" o "Tailwind CSS para JavaScript".

### Filosofía
- Declarativo (directamente en el HTML)
- Reactivo (el DOM se actualiza automáticamente)
- Ligero (15kb minified)
- Ideal para interacciones locales

---

## 📚 Patrones Usados en Atenea

### 1. Modal / Dialog

**Caso de uso**: Confirmación antes de eliminar algo.

```html
<div x-data="{ open: false }" x-cloak>
    <!-- Botón para abrir -->
    <button @click="open = true" class="btn btn-danger">
        Eliminar
    </button>
    
    <!-- Modal Overlay -->
    <div 
        x-show="open" 
        @click.self="open = false"
        class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center"
        x-transition:enter="transition ease-out duration-300"
        x-transition:enter-start="opacity-0"
        x-transition:enter-end="opacity-100"
        x-transition:leave="transition ease-in duration-200"
        x-transition:leave-start="opacity-100"
        x-transition:leave-end="opacity-0">
        
        <!-- Modal Box -->
        <div class="bg-white rounded-lg p-6 max-w-md"
             @click.stop
             x-transition:enter="transition ease-out duration-300"
             x-transition:enter-start="opacity-0 transform scale-90"
             x-transition:enter-end="opacity-100 transform scale-100">
            
            <h3 class="text-xl font-bold mb-4">¿Estás seguro?</h3>
            <p class="mb-6">Esta acción no se puede deshacer.</p>
            
            <div class="flex gap-3 justify-end">
                <button @click="open = false" class="btn btn-ghost">
                    Cancelar
                </button>
                <form method="post" action="/delete/">
                    {% csrf_token %}
                    <button type="submit" class="btn btn-danger">
                        Confirmar
                    </button>
                </form>
            </div>
        </div>
    </div>
</div>

<style>
[x-cloak] { display: none !important; }
</style>
```

**Características**:
- `x-data="{ open: false }"` - Estado local
- `@click="open = true"` - Shorthand de `x-on:click`
- `x-show="open"` - Mostrar/ocultar con display
- `@click.self` - Solo si click en el overlay (no en hijos)
- `@click.stop` - Evitar que el click se propague
- `x-transition` - Animaciones suaves
- `x-cloak` - Evitar flash de contenido no hidratado

---

### 2. Toggle de Vista (Grid/Lista)

**Caso de uso**: Cambiar entre vista de cuadrícula y lista.

```html
<div x-data="{ view: 'grid' }">
    <!-- Botones de toggle -->
    <div class="inline-flex rounded-lg border">
        <button 
            @click="view = 'grid'"
            :class="view === 'grid' ? 'bg-gray-100' : ''"
            class="px-4 py-2 rounded-l-lg">
            ⊞ Cuadrícula
        </button>
        <button 
            @click="view = 'list'"
            :class="view === 'list' ? 'bg-gray-100' : ''"
            class="px-4 py-2 rounded-r-lg">
            ☰ Lista
        </button>
    </div>
    
    <!-- Vista Grid -->
    <div x-show="view === 'grid'" class="grid grid-cols-3 gap-4">
        {% for project in projects %}
        <div class="card">{{ project.name }}</div>
        {% endfor %}
    </div>
    
    <!-- Vista Lista -->
    <div x-show="view === 'list'" class="space-y-2">
        {% for project in projects %}
        <div class="flex items-center gap-4">{{ project.name }}</div>
        {% endfor %}
    </div>
</div>
```

**Características**:
- `:class` - Binding dinámico de clases (shorthand de `x-bind:class`)
- Expresiones ternarias: `condition ? 'class-si' : 'class-no'`

---

### 3. Dropdown Menu

```html
<div x-data="{ open: false }" @click.away="open = false">
    <!-- Trigger -->
    <button @click="open = !open" class="btn">
        Opciones ▼
    </button>
    
    <!-- Menu -->
    <div 
        x-show="open"
        x-transition
        class="absolute mt-2 bg-white shadow-lg rounded-lg py-2">
        
        <a href="/edit/" class="block px-4 py-2 hover:bg-gray-100">
            Editar
        </a>
        <a href="/delete/" class="block px-4 py-2 hover:bg-gray-100 text-red-600">
            Eliminar
        </a>
    </div>
</div>
```

**Características**:
- `@click.away` - Cerrar al hacer click fuera
- `open = !open` - Toggle booleano

---

### 4. Tabs

```html
<div x-data="{ tab: 'videos' }">
    <!-- Tab Headers -->
    <div class="flex border-b">
        <button 
            @click="tab = 'videos'"
            :class="tab === 'videos' ? 'border-b-2 border-black' : ''"
            class="px-4 py-2">
            Videos
        </button>
        <button 
            @click="tab = 'images'"
            :class="tab === 'images' ? 'border-b-2 border-black' : ''"
            class="px-4 py-2">
            Imágenes
        </button>
        <button 
            @click="tab = 'scripts'"
            :class="tab === 'scripts' ? 'border-b-2 border-black' : ''"
            class="px-4 py-2">
            Scripts
        </button>
    </div>
    
    <!-- Tab Panels -->
    <div x-show="tab === 'videos'" class="p-4">
        <!-- Contenido de videos -->
    </div>
    <div x-show="tab === 'images'" class="p-4">
        <!-- Contenido de imágenes -->
    </div>
    <div x-show="tab === 'scripts'" class="p-4">
        <!-- Contenido de scripts -->
    </div>
</div>
```

---

### 5. Accordion / Collapse

```html
<div x-data="{ expanded: false }">
    <!-- Header -->
    <button 
        @click="expanded = !expanded"
        class="flex items-center justify-between w-full p-4 bg-gray-100 rounded-lg">
        <span>Detalles del Proyecto</span>
        <svg 
            :class="expanded ? 'rotate-180' : ''"
            class="w-5 h-5 transition-transform"
            fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
    </button>
    
    <!-- Content -->
    <div 
        x-show="expanded"
        x-collapse
        class="p-4 border-l-2 border-gray-200">
        <p>Información detallada del proyecto...</p>
    </div>
</div>
```

**Características**:
- `x-collapse` - Plugin para animaciones de altura
- `:class` con transformaciones CSS

---

### 6. Toast / Notificación

```html
<div x-data="{ 
    show: false, 
    message: '',
    notify(msg) { 
        this.message = msg; 
        this.show = true; 
        setTimeout(() => this.show = false, 3000); 
    }
}">
    <!-- Trigger -->
    <button @click="notify('¡Acción completada!')">
        Hacer algo
    </button>
    
    <!-- Toast -->
    <div 
        x-show="show"
        x-transition
        class="fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg">
        <span x-text="message"></span>
    </div>
</div>
```

**Características**:
- Métodos en `x-data`: `notify(msg) { ... }`
- `x-text` - Binding de texto
- `setTimeout` para auto-cerrar

---

### 7. Form Validation (Inline)

```html
<form x-data="{ 
    name: '',
    email: '',
    get isValid() {
        return this.name.length > 0 && this.email.includes('@');
    }
}">
    <!-- Name Input -->
    <div>
        <input 
            type="text" 
            x-model="name" 
            placeholder="Nombre"
            class="border rounded px-3 py-2">
        <p x-show="name.length > 0 && name.length < 3" class="text-red-500 text-sm">
            Mínimo 3 caracteres
        </p>
    </div>
    
    <!-- Email Input -->
    <div>
        <input 
            type="email" 
            x-model="email" 
            placeholder="Email"
            class="border rounded px-3 py-2">
        <p x-show="email.length > 0 && !email.includes('@')" class="text-red-500 text-sm">
            Email inválido
        </p>
    </div>
    
    <!-- Submit -->
    <button 
        type="submit"
        :disabled="!isValid"
        :class="isValid ? 'bg-black' : 'bg-gray-400 cursor-not-allowed'"
        class="text-white px-4 py-2 rounded">
        Enviar
    </button>
</form>
```

**Características**:
- `x-model` - Two-way data binding
- Getters: `get isValid() { ... }`
- `:disabled` - Binding de atributos

---

### 8. Counter / Stepper

```html
<div x-data="{ count: 0 }">
    <div class="flex items-center gap-4">
        <button 
            @click="count--"
            :disabled="count === 0"
            class="btn">
            -
        </button>
        
        <span class="text-2xl font-bold" x-text="count"></span>
        
        <button @click="count++" class="btn">
            +
        </button>
    </div>
</div>
```

---

### 9. Search/Filter Local

```html
<div x-data="{ 
    search: '',
    items: {{ items|safe }},  // Desde Django
    get filtered() {
        return this.items.filter(item => 
            item.name.toLowerCase().includes(this.search.toLowerCase())
        );
    }
}">
    <!-- Search Input -->
    <input 
        type="search" 
        x-model="search" 
        placeholder="Buscar..."
        class="border rounded px-4 py-2 mb-4">
    
    <!-- Results -->
    <div class="space-y-2">
        <template x-for="item in filtered" :key="item.id">
            <div class="p-4 bg-white rounded shadow">
                <h3 x-text="item.name"></h3>
            </div>
        </template>
    </div>
    
    <!-- No results -->
    <p x-show="filtered.length === 0" class="text-gray-500">
        No se encontraron resultados
    </p>
</div>
```

**Características**:
- `x-for` - Loop sobre arrays
- `:key` - Key único para cada item
- `<template>` - No renderiza el template tag en el DOM

---

### 10. Multi-step Form / Wizard

```html
<div x-data="{ 
    step: 1,
    formData: { name: '', email: '', message: '' },
    nextStep() { if (this.step < 3) this.step++; },
    prevStep() { if (this.step > 1) this.step--; }
}">
    <!-- Progress Bar -->
    <div class="flex gap-2 mb-6">
        <div :class="step >= 1 ? 'bg-black' : 'bg-gray-300'" class="h-2 flex-1 rounded"></div>
        <div :class="step >= 2 ? 'bg-black' : 'bg-gray-300'" class="h-2 flex-1 rounded"></div>
        <div :class="step >= 3 ? 'bg-black' : 'bg-gray-300'" class="h-2 flex-1 rounded"></div>
    </div>
    
    <!-- Step 1 -->
    <div x-show="step === 1">
        <h2 class="text-xl font-bold mb-4">Paso 1: Nombre</h2>
        <input type="text" x-model="formData.name" class="border rounded px-3 py-2 w-full">
    </div>
    
    <!-- Step 2 -->
    <div x-show="step === 2">
        <h2 class="text-xl font-bold mb-4">Paso 2: Email</h2>
        <input type="email" x-model="formData.email" class="border rounded px-3 py-2 w-full">
    </div>
    
    <!-- Step 3 -->
    <div x-show="step === 3">
        <h2 class="text-xl font-bold mb-4">Paso 3: Mensaje</h2>
        <textarea x-model="formData.message" class="border rounded px-3 py-2 w-full"></textarea>
    </div>
    
    <!-- Navigation -->
    <div class="flex justify-between mt-6">
        <button 
            @click="prevStep()"
            x-show="step > 1"
            class="btn btn-ghost">
            Anterior
        </button>
        
        <button 
            @click="nextStep()"
            x-show="step < 3"
            class="btn btn-primary">
            Siguiente
        </button>
        
        <button 
            x-show="step === 3"
            type="submit"
            class="btn btn-primary">
            Enviar
        </button>
    </div>
</div>
```

---

## 🎨 Directivas Alpine.js

| Directiva | Descripción | Ejemplo |
|-----------|-------------|---------|
| `x-data` | Define componente con estado | `x-data="{ open: false }"` |
| `x-show` | Mostrar/ocultar (display) | `x-show="open"` |
| `x-if` | Renderizado condicional (DOM) | `<template x-if="open">` |
| `x-for` | Loop sobre arrays | `<template x-for="item in items">` |
| `x-on:` / `@` | Event listeners | `@click="open = true"` |
| `x-bind:` / `:` | Bind attributes/classes | `:class="open ? 'active' : ''"` |
| `x-model` | Two-way binding | `x-model="email"` |
| `x-text` | Set text content | `x-text="message"` |
| `x-html` | Set HTML content | `x-html="htmlContent"` |
| `x-cloak` | Ocultar hasta Alpine cargue | `[x-cloak] { display: none }` |
| `x-transition` | Animaciones | `x-transition` |
| `x-ref` | Referencias a elementos | `x-ref="input"` |

---

## 🎯 Modifiers

### Event Modifiers

```html
<!-- Prevenir default -->
<form @submit.prevent="handleSubmit()">

<!-- Stop propagation -->
<button @click.stop="...">

<!-- Ejecutar solo una vez -->
<button @click.once="...">

<!-- Click fuera -->
<div @click.away="open = false">

<!-- Self (solo si click en el elemento, no hijos) -->
<div @click.self="...">

<!-- Debounce -->
<input @input.debounce.500ms="search()">

<!-- Throttle -->
<div @scroll.throttle.1s="onScroll()">
```

### Key Modifiers

```html
<!-- Enter -->
<input @keydown.enter="submit()">

<!-- Escape -->
<div @keydown.escape="close()">

<!-- Shift + Enter -->
<input @keydown.shift.enter="...">
```

---

## 🛠️ Tips y Trucos

### 1. Compartir Estado Entre Componentes

Usa `Alpine.store()`:

```html
<script>
document.addEventListener('alpine:init', () => {
    Alpine.store('auth', {
        user: null,
        isLoggedIn() {
            return this.user !== null;
        }
    });
});
</script>

<!-- Componente 1 -->
<div x-data>
    <span x-text="$store.auth.user"></span>
</div>

<!-- Componente 2 -->
<div x-data>
    <button x-show="!$store.auth.isLoggedIn()">Login</button>
</div>
```

### 2. Inicializar con Datos de Django

```html
<div x-data='{{ initial_data|safe }}'>
    <!-- initial_data es un dict de Python convertido a JSON -->
</div>
```

Backend:
```python
import json

def my_view(request):
    initial_data = json.dumps({
        'items': [{'id': 1, 'name': 'Item 1'}],
        'count': 10
    })
    return render(request, 'template.html', {'initial_data': initial_data})
```

### 3. Persist State en localStorage

```html
<div x-data="{ 
    theme: localStorage.getItem('theme') || 'light',
    setTheme(newTheme) {
        this.theme = newTheme;
        localStorage.setItem('theme', newTheme);
    }
}">
    <button @click="setTheme('dark')">Dark</button>
    <button @click="setTheme('light')">Light</button>
</div>
```

### 4. Lazy Loading

```html
<div x-data="{ loaded: false }" x-intersect="loaded = true">
    <template x-if="loaded">
        <!-- Contenido pesado que se carga cuando entra en viewport -->
        <iframe src="..."></iframe>
    </template>
</div>
```

---

## 🐛 Debugging

### Ver Estado Actual

```javascript
// En DevTools Console, inspecciona un elemento con x-data
$el.__x  // Ver todo el contexto Alpine
$el.__x.$data  // Ver solo los datos
```

### Alpine DevTools

Instala la extensión de Chrome: [Alpine.js DevTools](https://chrome.google.com/webstore/detail/alpinejs-devtools/)

---

## ⚠️ Mejores Prácticas

### ✅ DO

```html
<!-- Usar para interacciones locales -->
<div x-data="{ open: false }">...</div>

<!-- Nombres descriptivos -->
<div x-data="{ showConfirmModal: false }">

<!-- Métodos para lógica compleja -->
<div x-data="{ 
    async submitForm() { /* ... */ }
}">
```

### ❌ DON'T

```html
<!-- No uses Alpine para estado global (usa Alpine.store o backend) -->

<!-- No pongas lógica de negocio compleja en Alpine -->
<div x-data="{ /* 100 líneas de código */ }">

<!-- No uses Alpine cuando HTMX es mejor -->
<!-- HTMX es mejor para cargar contenido del servidor -->
```

---

## 🎯 Alpine vs HTMX

| Caso de uso | Usa | Razón |
|-------------|-----|-------|
| Modal/Dialog | Alpine | Estado local, no necesita servidor |
| Dropdown menu | Alpine | Interacción puramente frontend |
| Cargar datos del servidor | HTMX | Servidor devuelve HTML |
| Auto-actualizar estado | HTMX | Polling desde servidor |
| Filtrar lista local | Alpine | Datos ya en el cliente |
| Buscar en servidor | HTMX | Necesita consultar BD |
| Toggle tabs | Alpine | Estado UI local |
| Enviar formulario | HTMX | Servidor procesa y responde |

---

## 📚 Recursos

- [Alpine.js Docs](https://alpinejs.dev/)
- [Alpine.js Examples](https://alpinejs.dev/start-here)
- [Alpine.js Cheat Sheet](https://www.alpinejs.tips/)

---

## 🚀 Siguientes Pasos

- Lee [Componentes](./components.md) para ver Alpine en acción
- Combina con [Patrones HTMX](./htmx-patterns.md)
- Revisa [Convenciones](./conventions.md)

