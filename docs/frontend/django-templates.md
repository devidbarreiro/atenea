# 🐍 Django Templates

> Guía completa del sistema de templates de Django

## 🎯 ¿Qué son Django Templates?

Django Templates es un sistema de plantillas que te permite generar HTML dinámicamente en el servidor. Piensa en ello como "HTML con superpoderes".

```html
<!-- HTML estático -->
<h1>Hola Mundo</h1>

<!-- Django Template (dinámico) -->
<h1>Hola {{ user_name }}</h1>
```

---

## 📚 Sintaxis Básica

### Variables

Mostrar datos del backend:

```html
{{ variable }}
{{ object.attribute }}
{{ dict.key }}
{{ list.0 }}
```

Ejemplos:
```html
<h1>{{ project.name }}</h1>
<p>{{ user.email }}</p>
<span>{{ config.api_key }}</span>
<div>{{ items.0 }}</div>
```

---

### Filtros

Transformar variables antes de mostrarlas:

```html
{{ variable|filter }}
{{ variable|filter:arg }}
```

#### Filtros Comunes

**Strings**:
```html
{{ text|lower }}                    <!-- minúsculas -->
{{ text|upper }}                    <!-- MAYÚSCULAS -->
{{ text|title }}                    <!-- Título Con Mayúsculas -->
{{ text|truncatewords:10 }}         <!-- primeras 10 palabras -->
{{ text|default:"Sin texto" }}      <!-- valor por defecto si vacío -->
```

**Números**:
```html
{{ price|floatformat:2 }}           <!-- 2 decimales: 10.50 -->
{{ count|pluralize }}               <!-- s si count > 1 -->
{{ count|pluralize:"es" }}          <!-- videos → videos, video → video -->
```

**Fechas**:
```html
{{ created_at|date:"d/m/Y" }}       <!-- 27/10/2025 -->
{{ created_at|date:"d M Y" }}       <!-- 27 Oct 2025 -->
{{ created_at|time:"H:i" }}         <!-- 14:30 -->
{{ created_at|timesince }}          <!-- "2 days ago" -->
```

**HTML**:
```html
{{ html_content|safe }}             <!-- No escapar HTML -->
{{ text|linebreaks }}               <!-- \n → <br> -->
{{ text|striptags }}                <!-- Eliminar tags HTML -->
```

**Listas**:
```html
{{ items|length }}                  <!-- Cantidad de items -->
{{ items|join:", " }}               <!-- Unir con comas -->
{{ items|first }}                   <!-- Primer item -->
{{ items|last }}                    <!-- Último item -->
```

#### Encadenar Filtros

```html
{{ text|lower|truncatewords:10 }}
{{ name|title|default:"Sin nombre" }}
{{ created_at|date:"d/m/Y"|default:"N/A" }}
```

---

### Tags

Control de flujo y lógica:

```html
{% tag %}
{% tag %}...{% endtag %}
```

#### {% if %}

```html
{% if condition %}
    <p>Es verdadero</p>
{% endif %}

{% if condition %}
    <p>Es verdadero</p>
{% else %}
    <p>Es falso</p>
{% endif %}

{% if condition1 %}
    <p>Condición 1</p>
{% elif condition2 %}
    <p>Condición 2</p>
{% else %}
    <p>Ninguna</p>
{% endif %}
```

**Operadores**:
```html
{% if count > 10 %}
{% if name == "Juan" %}
{% if status != "completed" %}
{% if age >= 18 %}
{% if age <= 65 %}

{% if x and y %}
{% if x or y %}
{% if not x %}

{% if x in list %}
{% if "draft" in video.status %}
```

**Ejemplos**:
```html
{% if projects %}
    <div class="grid">
        <!-- Mostrar proyectos -->
    </div>
{% else %}
    <div class="empty-state">
        <p>No hay proyectos</p>
    </div>
{% endif %}

{% if video.status == 'completed' %}
    <span class="badge-success">Completado</span>
{% elif video.status == 'processing' %}
    <span class="badge-warning">Procesando</span>
{% else %}
    <span class="badge-default">Pendiente</span>
{% endif %}
```

---

#### {% for %}

Iterar sobre listas:

```html
{% for item in items %}
    <div>{{ item.name }}</div>
{% endfor %}

{% for item in items %}
    <div>{{ item }}</div>
{% empty %}
    <p>No hay items</p>
{% endfor %}
```

**Variables especiales en loops**:

```html
{% for project in projects %}
    {{ forloop.counter }}       <!-- 1, 2, 3, ... -->
    {{ forloop.counter0 }}      <!-- 0, 1, 2, ... -->
    {{ forloop.revcounter }}    <!-- N, N-1, N-2, ... -->
    {{ forloop.first }}         <!-- True en primer item -->
    {{ forloop.last }}          <!-- True en último item -->
    {{ forloop.parentloop }}    <!-- Loop padre (si nested) -->
{% endfor %}
```

**Ejemplos**:
```html
<!-- Lista simple -->
<ul>
{% for video in videos %}
    <li>{{ video.title }}</li>
{% endfor %}
</ul>

<!-- Con empty -->
{% for video in videos %}
    <div class="card">{{ video.title }}</div>
{% empty %}
    <p>No hay videos</p>
{% endfor %}

<!-- Con índice -->
{% for item in items %}
    <div class="{% if forloop.first %}first{% endif %}">
        {{ forloop.counter }}. {{ item.name }}
    </div>
{% endfor %}

<!-- Nested loops -->
{% for project in projects %}
    <h2>{{ project.name }}</h2>
    <ul>
    {% for video in project.videos.all %}
        <li>{{ video.title }}</li>
    {% endfor %}
    </ul>
{% endfor %}
```

---

#### {% url %}

Generar URLs desde nombres de vistas:

```html
{% url 'view_name' %}
{% url 'view_name' arg1 arg2 %}
{% url 'app_name:view_name' arg %}
```

**Ejemplos**:
```html
<!-- Sin argumentos -->
<a href="{% url 'core:dashboard' %}">Dashboard</a>

<!-- Con argumentos posicionales -->
<a href="{% url 'core:project_detail' project.id %}">
    Ver Proyecto
</a>

<!-- Con argumentos nombrados -->
<a href="{% url 'core:video_detail' pk=video.id %}">
    Ver Video
</a>

<!-- Guardar URL en variable -->
{% url 'core:project_detail' project.id as project_url %}
<a href="{{ project_url }}">Link 1</a>
<a href="{{ project_url }}">Link 2</a>
```

---

#### {% include %}

Incluir otros templates:

```html
{% include 'template_name.html' %}
{% include 'template_name.html' with var1=value1 var2=value2 %}
```

**Ejemplos**:
```html
<!-- Incluir sin parámetros -->
{% include 'partials/navbar.html' %}

<!-- Incluir con parámetros -->
{% include 'partials/video_status.html' with video=video %}

<!-- Incluir con múltiples parámetros -->
{% include 'partials/card.html' with 
    title=project.name
    subtitle=project.description
    link=project_url
%}

<!-- Incluir solo si existe -->
{% include 'partials/optional.html' only %}
```

---

#### {% block %}

Definir bloques para herencia de templates:

```html
{% block name %}
    <!-- Contenido por defecto -->
{% endblock %}
```

**En base.html**:
```html
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}Atenea{% endblock %}</title>
    {% block extra_css %}{% endblock %}
</head>
<body>
    <main>
        {% block content %}{% endblock %}
    </main>
    {% block extra_js %}{% endblock %}
</body>
</html>
```

**En página específica**:
```html
{% extends 'base.html' %}

{% block title %}Proyectos - Atenea{% endblock %}

{% block content %}
<h1>Mis Proyectos</h1>
<!-- Contenido -->
{% endblock %}

{% block extra_js %}
<script>
console.log('JavaScript específico de esta página');
</script>
{% endblock %}
```

---

#### {% with %}

Crear variables temporales:

```html
{% with variable_name=value %}
    {{ variable_name }}
{% endwith %}
```

**Ejemplos**:
```html
<!-- Simplificar expresiones largas -->
{% with total=projects.count %}
    <p>Total de proyectos: {{ total }}</p>
    <p>Promedio: {{ total|floatformat:2 }}</p>
{% endwith %}

<!-- Múltiples variables -->
{% with completed=videos.completed processing=videos.processing %}
    <span>{{ completed }} completados</span>
    <span>{{ processing }} procesando</span>
{% endwith %}
```

---

#### {% load %}

Cargar template tags custom:

```html
{% load static %}
{% load custom_tags %}
```

**Ejemplos**:
```html
{% load static %}
<img src="{% static 'img/logo.png' %}">

{% load custom_filters %}
{{ text|my_custom_filter }}
```

---

### Comentarios

```html
{# Comentario de una línea #}

{% comment %}
Comentario
de múltiples
líneas
{% endcomment %}

<!-- Comentario HTML (se renderiza en el HTML final) -->
```

**Cuándo usar**:
```html
{# TODO: Mejorar este código #}
{# Esto es una nota para desarrolladores #}

{% comment %}
Este código está desactivado temporalmente
<div>{{ old_code }}</div>
{% endcomment %}

<!-- Este comentario será visible en el HTML final -->
```

---

## 🏗️ Herencia de Templates

### Concepto

Crear un template base con la estructura común y extenderlo en páginas específicas.

### Template Base

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Atenea{% endblock %}</title>
    
    <!-- Tailwind, HTMX, Alpine -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.13.5/dist/cdn.min.js"></script>
    
    {% block extra_css %}{% endblock %}
</head>
<body class="bg-gray-50">
    <!-- Navbar -->
    <nav class="bg-white border-b">
        <div class="max-w-7xl mx-auto px-4">
            <div class="flex justify-between h-16">
                <a href="{% url 'core:dashboard' %}" class="flex items-center">
                    <span class="text-xl font-bold">🎨 Atenea</span>
                </a>
            </div>
        </div>
    </nav>
    
    <!-- Messages -->
    {% if messages %}
    <div class="fixed top-20 right-4 z-50 space-y-2">
        {% for message in messages %}
        <div class="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded">
            {{ message }}
        </div>
        {% endfor %}
    </div>
    {% endif %}
    
    <!-- Content -->
    <main class="max-w-7xl mx-auto px-4 py-8">
        {% block content %}{% endblock %}
    </main>
    
    {% block extra_js %}{% endblock %}
</body>
</html>
```

### Template que Extiende

```html
<!-- templates/projects/index.html -->
{% extends 'base.html' %}

{% block title %}Proyectos - Atenea{% endblock %}

{% block content %}
<div class="mb-8">
    <h1 class="text-4xl font-bold mb-2">Proyectos</h1>
    <p class="text-gray-600">Gestiona tus proyectos</p>
</div>

<div class="grid grid-cols-3 gap-4">
    {% for project in projects %}
    <div class="card">
        <h3>{{ project.name }}</h3>
        <p>{{ project.description }}</p>
    </div>
    {% endfor %}
</div>
{% endblock %}

{% block extra_js %}
<script>
console.log('JavaScript de proyectos');
</script>
{% endblock %}
```

### Herencia Múltiple

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html>
<head>...</head>
<body>
    <nav>...</nav>
    <main>
        {% block content %}{% endblock %}
    </main>
</body>
</html>

<!-- templates/base_item_detail.html -->
{% extends 'base.html' %}

{% block content %}
<div class="detail-page">
    <h1>{% block item_title %}{% endblock %}</h1>
    <div>{% block item_body %}{% endblock %}</div>
</div>
{% endblock %}

<!-- templates/projects/detail.html -->
{% extends 'base_item_detail.html' %}

{% block item_title %}{{ project.name }}{% endblock %}

{% block item_body %}
<p>{{ project.description }}</p>
{% endblock %}
```

---

## 🔄 Context (Datos del Backend)

### Pasar Datos desde Views

```python
# core/views.py
from django.shortcuts import render
from .models import Project, Video

def dashboard(request):
    projects = Project.objects.all()
    videos = Video.objects.filter(status='completed')
    
    context = {
        'projects': projects,
        'videos': videos,
        'total_projects': projects.count(),
        'user_name': request.user.username if request.user.is_authenticated else 'Invitado',
    }
    
    return render(request, 'dashboard/index.html', context)
```

### Usar en Template

```html
<!-- dashboard/index.html -->
<h1>Hola {{ user_name }}</h1>
<p>Tienes {{ total_projects }} proyectos</p>

<div class="grid">
    {% for project in projects %}
    <div class="card">{{ project.name }}</div>
    {% endfor %}
</div>

<div class="grid">
    {% for video in videos %}
    <div class="card">{{ video.title }}</div>
    {% endfor %}
</div>
```

---

## 🎨 Template Tags Custom

### Crear Tags Custom

```python
# core/templatetags/custom_tags.py
from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiplica value por arg"""
    return value * arg

@register.simple_tag
def get_status_badge(status):
    """Retorna HTML para badge según status"""
    colors = {
        'completed': 'bg-green-500',
        'processing': 'bg-yellow-500',
        'error': 'bg-red-500',
    }
    color = colors.get(status, 'bg-gray-500')
    return f'<span class="{color} text-white px-3 py-1 rounded">{status}</span>'
```

### Usar en Templates

```html
{% load custom_tags %}

<!-- Usar filtro -->
<p>Precio total: ${{ price|multiply:quantity }}</p>

<!-- Usar simple_tag -->
{% get_status_badge video.status %}
```

---

## 🎯 Mejores Prácticas

### 1. Nombres Descriptivos

```html
<!-- ✅ BIEN -->
{{ project.name }}
{{ user.email }}
{{ created_at|date:"d/m/Y" }}

<!-- ❌ MAL -->
{{ p }}
{{ x }}
{{ d }}
```

### 2. Default Values

```html
<!-- ✅ BIEN: Proporcionar default -->
{{ title|default:"Sin título" }}
{{ description|default:"Sin descripción" }}

<!-- ⚠️ OK: Pero puede mostrar vacío -->
{{ title }}
```

### 3. Verificar Existencia

```html
<!-- ✅ BIEN -->
{% if projects %}
    {% for project in projects %}
        <div>{{ project.name }}</div>
    {% endfor %}
{% else %}
    <p>No hay proyectos</p>
{% endif %}

<!-- ❌ MAL: No maneja caso vacío -->
{% for project in projects %}
    <div>{{ project.name }}</div>
{% endfor %}
```

### 4. DRY (Don't Repeat Yourself)

```html
<!-- ✅ BIEN: Usar include -->
{% for video in videos %}
    {% include 'partials/video_card.html' with video=video %}
{% endfor %}

<!-- ❌ MAL: Código duplicado -->
{% for video in videos %}
    <div class="card">
        <h3>{{ video.title }}</h3>
        <p>{{ video.description }}</p>
        <!-- 20 líneas más... -->
    </div>
{% endfor %}
```

### 5. Seguridad

```html
<!-- ⚠️ Por defecto, Django escapa HTML (seguro) -->
{{ user_input }}  <!-- <script> → &lt;script&gt; -->

<!-- ⚠️ PELIGRO: Solo usa |safe con contenido confiable -->
{{ trusted_html|safe }}

<!-- ✅ BIEN: Usar {% csrf_token %} en forms -->
<form method="post">
    {% csrf_token %}
    <input name="title">
</form>
```

---

## 🐛 Debugging Templates

### Ver Variables Disponibles

```html
<!-- Temporalmente, para debug -->
{% if debug %}
    <pre>{{ variable }}</pre>
{% endif %}

<!-- Ver TODO el contexto (solo si DEBUG=True) -->
{% debug %}
```

### Pretty Print

```html
{% load static %}
<pre>{{ variable|pprint }}</pre>
```

### Print en Console (con JavaScript)

```html
<script>
console.log('Variable:', {{ variable|safe }});
console.log('Project:', {{ project|safe }});
</script>
```

---

## 📚 Recursos

- [Django Templates Docs](https://docs.djangoproject.com/en/5.2/ref/templates/)
- [Built-in Template Tags](https://docs.djangoproject.com/en/5.2/ref/templates/builtins/)
- [Template Filters](https://docs.djangoproject.com/en/5.2/ref/templates/builtins/#built-in-filter-reference)

---

## 🚀 Siguientes Pasos

- Practica con los ejemplos
- Crea tu propio template tag custom
- Lee sobre [Componentes](./components.md)
- Aprende [HTMX](./htmx-patterns.md) para interactividad

