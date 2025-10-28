# 🎨 Visual Cheat Sheet

> Referencia rápida visual para desarrollo frontend en Atenea

## 🎨 Tailwind CSS - Clases Más Usadas

### Layout & Display

```html
<!-- Flexbox -->
<div class="flex items-center justify-between gap-4">
<div class="flex flex-col space-y-4">
<div class="flex flex-wrap">

<!-- Grid -->
<div class="grid grid-cols-3 gap-4">
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">

<!-- Display -->
<div class="block">
<div class="hidden md:block">
<div class="inline-block">
```

### Spacing

```html
<!-- Padding -->
p-2  = 0.5rem (8px)
p-4  = 1rem (16px)     ← DEFAULT
p-6  = 1.5rem (24px)
p-8  = 2rem (32px)

px-4  = padding horizontal
py-2  = padding vertical
pt-4  = padding top
pr-4  = padding right
pb-4  = padding bottom
pl-4  = padding left

<!-- Margin -->
m-2, m-4, m-6, m-8
mx-4, my-2
mt-4, mr-4, mb-4, ml-4

<!-- Gap (para flex/grid) -->
gap-2, gap-4, gap-6, gap-8

<!-- Space (entre hijos) -->
space-y-4  = vertical spacing
space-x-4  = horizontal spacing
```

### Typography

```html
<!-- Size -->
text-xs    = 0.75rem (12px)
text-sm    = 0.875rem (14px)
text-base  = 1rem (16px)
text-lg    = 1.125rem (18px)
text-xl    = 1.25rem (20px)
text-2xl   = 1.5rem (24px)
text-3xl   = 1.875rem (30px)
text-4xl   = 2.25rem (36px)

<!-- Weight -->
font-light      = 300
font-normal     = 400
font-medium     = 500
font-semibold   = 600
font-bold       = 700

<!-- Align -->
text-left
text-center
text-right
text-justify
```

### Colors

```html
<!-- Background -->
bg-white
bg-black
bg-gray-50, bg-gray-100, bg-gray-200, ..., bg-gray-900

bg-red-500, bg-yellow-500, bg-green-500, bg-blue-500, bg-purple-600

<!-- Text -->
text-white
text-black
text-gray-500, text-gray-600, text-gray-900

<!-- Estados -->
bg-green-500    = Success / Completado
bg-yellow-500   = Warning / Procesando
bg-red-500      = Error / Danger
bg-blue-500     = Info / Secondary
```

### Borders & Rounded

```html
<!-- Border -->
border                      = 1px
border-2                    = 2px
border-t, border-r, border-b, border-l

border-gray-200            = color
border-gray-300

<!-- Rounded -->
rounded         = 0.25rem (4px)
rounded-md      = 0.375rem (6px)
rounded-lg      = 0.5rem (8px)
rounded-xl      = 0.75rem (12px)
rounded-2xl     = 1rem (16px)
rounded-full    = 9999px (círculo)
```

### Shadows

```html
shadow-sm       = sombra pequeña
shadow          = sombra normal
shadow-md       = sombra mediana  ← DEFAULT
shadow-lg       = sombra grande
shadow-xl       = sombra extra grande
shadow-2xl      = sombra enorme
```

### Hover & Focus

```html
<!-- Hover -->
<button class="bg-black hover:bg-gray-800">
<div class="shadow-md hover:shadow-xl">

<!-- Focus -->
<input class="focus:ring-2 focus:ring-black focus:outline-none">

<!-- Transition -->
<div class="transition-all duration-300">
<div class="transition-colors duration-200">
```

### Responsive

```html
<!-- Mobile first -->
<div class="text-sm md:text-base lg:text-lg xl:text-xl">

<!-- Breakpoints -->
sm:   640px   (tablet pequeño)
md:   768px   (tablet)
lg:   1024px  (desktop)
xl:   1280px  (desktop grande)
2xl:  1536px  (pantallas grandes)

<!-- Ejemplos -->
<div class="
    grid 
    grid-cols-1 
    md:grid-cols-2 
    lg:grid-cols-3 
    xl:grid-cols-4">
</div>

<div class="hidden md:block">  <!-- Visible solo en tablet+ -->
<div class="block md:hidden">  <!-- Visible solo en mobile -->
```

---

## ⚡ HTMX - Atributos Comunes

### Request Types

```html
hx-get="/api/data/"
hx-post="/api/create/"
hx-put="/api/update/1/"
hx-delete="/api/delete/1/"
hx-patch="/api/patch/1/"
```

### Triggers

```html
<!-- Click (default en buttons) -->
<button hx-get="/api/">

<!-- Cada X segundos -->
<div hx-get="/api/" hx-trigger="every 5s">

<!-- Al cargar -->
<div hx-get="/api/" hx-trigger="load">

<!-- Input con delay -->
<input hx-get="/search/" hx-trigger="keyup changed delay:300ms">

<!-- Cuando entra en viewport -->
<div hx-get="/api/" hx-trigger="revealed">

<!-- Múltiples -->
<div hx-get="/api/" hx-trigger="click, every 30s">
```

### Targets & Swaps

```html
<!-- Target: dónde poner la respuesta -->
hx-target="#result"
hx-target="closest .card"
hx-target="this"

<!-- Swap: cómo reemplazar -->
hx-swap="innerHTML"     (default, reemplaza contenido)
hx-swap="outerHTML"     (reemplaza elemento completo)
hx-swap="beforebegin"   (antes del elemento)
hx-swap="afterbegin"    (inicio del contenido)
hx-swap="beforeend"     (final del contenido)
hx-swap="afterend"      (después del elemento)
```

### Otros

```html
hx-indicator="#loading"     (mostrar loading)
hx-confirm="¿Seguro?"       (confirmación)
hx-include="[name='q']"     (incluir inputs)
```

### Ejemplo Completo

```html
<button 
    hx-post="/api/create/"
    hx-target="#result"
    hx-swap="innerHTML"
    hx-indicator="#loading"
    hx-confirm="¿Crear?">
    Crear
</button>

<div id="result"></div>
<div id="loading" class="htmx-indicator hidden">Cargando...</div>
```

---

## 🏔️ Alpine.js - Directivas Comunes

### x-data

Define componente con estado:

```html
<div x-data="{ open: false }">
<div x-data="{ count: 0, items: [] }">
<div x-data="{ 
    name: '', 
    submit() { /* ... */ } 
}">
```

### x-show / x-if

```html
<!-- x-show: muestra/oculta (display: none) -->
<div x-show="open">

<!-- x-if: agrega/elimina del DOM -->
<template x-if="open">
    <div>...</div>
</template>
```

### x-for

Loop sobre arrays:

```html
<template x-for="item in items" :key="item.id">
    <div x-text="item.name"></div>
</template>
```

### @ (Event Listeners)

```html
@click="..."
@click.away="..."       (click fuera)
@click.stop="..."       (stop propagation)
@click.prevent="..."    (prevent default)

@keydown.enter="..."
@keydown.escape="..."
@input="..."
```

### : (Binding)

```html
:class="open ? 'active' : ''"
:disabled="!isValid"
:href="url"
:style="{ color: color }"
```

### x-model

Two-way binding:

```html
<input type="text" x-model="name">
<span x-text="name"></span>
```

### x-text / x-html

```html
<span x-text="message"></span>
<div x-html="htmlContent"></div>
```

### x-transition

Animaciones:

```html
<div 
    x-show="open"
    x-transition:enter="transition ease-out duration-300"
    x-transition:enter-start="opacity-0"
    x-transition:enter-end="opacity-100">
</div>
```

### Ejemplo Completo: Modal

```html
<div x-data="{ open: false }" x-cloak>
    <button @click="open = true">Abrir</button>
    
    <div 
        x-show="open" 
        @click.away="open = false"
        class="fixed inset-0 bg-black bg-opacity-50"
        x-transition>
        
        <div class="bg-white p-6 rounded-lg">
            <h3>Modal</h3>
            <button @click="open = false">Cerrar</button>
        </div>
    </div>
</div>
```

---

## 🐍 Django Templates - Sintaxis Rápida

### Variables

```html
{{ variable }}
{{ object.attribute }}
{{ dict.key }}
{{ list.0 }}
```

### Filtros

```html
{{ text|lower }}
{{ text|upper }}
{{ text|title }}
{{ count|pluralize }}
{{ created_at|date:"d/m/Y" }}
{{ price|floatformat:2 }}
{{ text|default:"Default" }}
```

### Tags

```html
<!-- If -->
{% if condition %}...{% endif %}
{% if x %}...{% else %}...{% endif %}
{% if x %}...{% elif y %}...{% else %}...{% endif %}

<!-- For -->
{% for item in items %}
    {{ item }}
{% endfor %}

{% for item in items %}
    {{ item }}
{% empty %}
    <p>No items</p>
{% endfor %}

<!-- Include -->
{% include 'partials/component.html' %}
{% include 'partials/component.html' with var=value %}

<!-- URL -->
{% url 'view_name' %}
{% url 'app:view_name' arg1 arg2 %}

<!-- Block (herencia) -->
{% extends 'base.html' %}
{% block title %}Título{% endblock %}
{% block content %}...{% endblock %}
```

---

## 🎯 Componentes Comunes - Copy & Paste

### Card

```html
<div class="bg-white shadow-md rounded-lg p-6 hover:shadow-xl transition-all duration-300">
    <h3 class="text-xl font-bold mb-2">{{ title }}</h3>
    <p class="text-gray-600 mb-4">{{ description }}</p>
    <div class="flex gap-2">
        <a href="#" class="bg-black text-white px-4 py-2 rounded-md hover:bg-gray-800">
            Acción
        </a>
    </div>
</div>
```

### Button

```html
<!-- Primary -->
<button class="bg-black text-white px-4 py-2 rounded-md hover:bg-gray-800 transition-colors">
    Botón
</button>

<!-- Secondary -->
<button class="border border-gray-300 px-4 py-2 rounded-md hover:bg-gray-100 transition-colors">
    Botón
</button>

<!-- Danger -->
<button class="bg-red-500 text-white px-4 py-2 rounded-md hover:bg-red-600 transition-colors">
    Eliminar
</button>
```

### Badge

```html
<span class="bg-green-500 text-white px-3 py-1 rounded-full text-xs font-semibold">
    Completado
</span>

<span class="bg-yellow-500 text-white px-3 py-1 rounded-full text-xs font-semibold">
    Procesando
</span>

<span class="bg-red-500 text-white px-3 py-1 rounded-full text-xs font-semibold">
    Error
</span>
```

### Empty State

```html
<div class="text-center py-12">
    <div class="text-6xl mb-4 opacity-30">📭</div>
    <h3 class="text-xl font-bold mb-2">No hay items</h3>
    <p class="text-gray-600 mb-4">Crea tu primer item para comenzar</p>
    <a href="{% url 'create' %}" class="bg-black text-white px-6 py-3 rounded-md">
        Crear Item
    </a>
</div>
```

### Grid Responsive

```html
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
    {% for item in items %}
    <div class="bg-white p-6 rounded-lg shadow-md">
        {{ item.name }}
    </div>
    {% endfor %}
</div>
```

### Modal (Alpine)

```html
<div x-data="{ open: false }" x-cloak>
    <button @click="open = true" class="bg-black text-white px-4 py-2 rounded-md">
        Abrir Modal
    </button>
    
    <div 
        x-show="open" 
        @click.self="open = false"
        class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
        x-transition>
        
        <div class="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 class="text-xl font-bold mb-4">Modal Title</h3>
            <p class="text-gray-600 mb-6">Modal content</p>
            
            <div class="flex gap-3 justify-end">
                <button @click="open = false" class="px-4 py-2 rounded-md border">
                    Cancelar
                </button>
                <button class="bg-black text-white px-4 py-2 rounded-md">
                    Confirmar
                </button>
            </div>
        </div>
    </div>
</div>

<style>
[x-cloak] { display: none !important; }
</style>
```

### Status Badge con HTMX Polling

```html
<div 
    hx-get="{% url 'core:video_status_partial' video.id %}" 
    hx-trigger="every 5s"
    hx-swap="outerHTML">
    
    {% if video.status == 'completed' %}
        <span class="bg-green-500 text-white px-3 py-1 rounded-md text-xs font-semibold">
            ✓ Completado
        </span>
    {% elif video.status == 'processing' %}
        <span class="bg-yellow-500 text-white px-3 py-1 rounded-md text-xs font-semibold">
            ⚙️ Procesando...
        </span>
    {% else %}
        <span class="bg-gray-500 text-white px-3 py-1 rounded-md text-xs font-semibold">
            Pendiente
        </span>
    {% endif %}
</div>
```

---

## 🎨 Paleta de Colores del Proyecto

```html
<!-- Primarios -->
bg-black text-white              /* Botones principales, navbar */
bg-white text-black              /* Cards, contenido */
bg-gray-50                       /* Fondo de página */

<!-- Estados -->
bg-green-500 text-white          /* ✓ Success / Completado */
bg-yellow-500 text-white         /* ⚙️ Warning / Procesando */
bg-red-500 text-white            /* ✗ Error / Peligro */
bg-blue-500 text-white           /* ℹ Info / Secundario */

<!-- Neutrales -->
bg-gray-100                      /* Hover states */
border-gray-200                  /* Borders sutiles */
border-gray-300                  /* Borders visibles */
text-gray-600                    /* Texto secundario */
text-gray-500                    /* Texto terciario */
```

---

## ⚡ Atajos de Teclado

```
DevTools:
F12                     Abrir DevTools
Ctrl + Shift + I        Abrir DevTools (alternativo)
Ctrl + Shift + J        Abrir Console
Ctrl + Shift + M        Toggle responsive mode

Navegador:
F5                      Refresh
Ctrl + F5               Hard refresh (limpiar cache)
Ctrl + Shift + Delete   Limpiar cache del navegador

Editor:
Ctrl + S                Guardar
Ctrl + F                Buscar
Ctrl + H                Buscar y reemplazar
```

---

## 📚 Links Rápidos

- [Tailwind Docs](https://tailwindcss.com/docs)
- [Tailwind Cheat Sheet](https://nerdcave.com/tailwind-cheat-sheet)
- [HTMX Docs](https://htmx.org/docs/)
- [Alpine Docs](https://alpinejs.dev/)
- [Django Templates](https://docs.djangoproject.com/en/5.2/ref/templates/builtins/)

---

Guarda este archivo para referencia rápida! 🚀

