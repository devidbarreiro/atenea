# 🐛 Troubleshooting Frontend

> Soluciones a problemas comunes

## 🎨 Tailwind CSS

### Problema: Los estilos no se aplican

#### Síntoma
```html
<div class="bg-blue-500 text-white p-4">
<!-- El div no tiene estilos -->
</div>
```

#### Soluciones

**1. Hard Refresh del navegador**
```
Windows: Ctrl + F5
Mac: Cmd + Shift + R
```

**2. Verificar que Tailwind esté cargando**
- Abre DevTools (F12)
- Ve a Network tab
- Busca `cdn.tailwindcss.com`
- Si no aparece, el script no está cargando

**3. Verificar el script en base.html**
```html
<!-- Debe estar en <head> -->
<script src="https://cdn.tailwindcss.com"></script>
```

**4. Verificar clases de Tailwind**
- Las clases incorrectas se ignoran silenciosamente
- Usa DevTools Inspector para ver clases aplicadas
- Compara con [docs de Tailwind](https://tailwindcss.com/docs)

**5. Cache del navegador**
```
1. Ctrl + Shift + Delete (abrir limpiar cache)
2. Seleccionar "Cached images and files"
3. Clear data
4. Recargar página
```

---

### Problema: Clases responsive no funcionan

#### Síntoma
```html
<div class="text-sm md:text-lg">
<!-- Siempre muestra text-sm, incluso en pantallas grandes -->
</div>
```

#### Soluciones

**1. Verificar el viewport**
- Redimensiona la ventana del navegador
- Breakpoints:
  - `sm`: 640px
  - `md`: 768px
  - `lg`: 1024px
  - `xl`: 1280px

**2. Usar DevTools responsive mode**
```
F12 → Click en icono de dispositivo móvil
O Ctrl + Shift + M (Windows) / Cmd + Shift + M (Mac)
```

**3. Orden de clases**
```html
<!-- ✅ BIEN: Mobile first -->
<div class="text-sm md:text-lg">

<!-- ❌ MAL: Desktop first no funciona así -->
<div class="text-lg md:text-sm">
```

---

### Problema: Colores custom no funcionan

#### Síntoma
```html
<div class="bg-[#FF6B6B]">
<!-- Color no se aplica -->
</div>
```

#### Solución

Con CDN de Tailwind, los colores arbitrarios funcionan:
```html
<!-- ✅ BIEN -->
<div class="bg-[#FF6B6B]">

<!-- Pero es mejor usar la paleta de Tailwind -->
<div class="bg-red-500">
```

---

## ⚡ HTMX

### Problema: HTMX no hace request

#### Síntoma
```html
<button hx-get="/api/data/" hx-target="#result">
    Cargar
</button>
<!-- No pasa nada al hacer click -->
```

#### Soluciones

**1. Verificar que HTMX esté cargando**
```javascript
// En DevTools Console
console.log(htmx);
// Si dice "undefined", HTMX no está cargado
```

**2. Verificar el script en base.html**
```html
<script src="https://unpkg.com/htmx.org@1.9.10"></script>
```

**3. Verificar la URL**
```html
<!-- ✅ BIEN: Usar {% url %} -->
<button hx-get="{% url 'core:my_view' %}">

<!-- ❌ MAL: URL hardcoded -->
<button hx-get="/api/data/">
```

**4. Ver errores en Network tab**
```
F12 → Network tab → Filter: XHR
Click el botón
Ver si aparece la request
Si hay error 404/500, la URL o el backend tienen problema
```

**5. Activar logs de HTMX**
```javascript
// En DevTools Console
htmx.logAll();
// Ahora haz click en el botón
// Verás logs detallados
```

---

### Problema: HTMX reemplaza contenido pero se ve mal

#### Síntoma
```html
<div id="result">
    <!-- El HTML llega pero sin estilos -->
</div>
```

#### Soluciones

**1. El HTML devuelto debe tener clases de Tailwind**
```python
# views.py
def my_view(request):
    return render(request, 'partials/card.html', {
        'data': data
    })
```

```html
<!-- partials/card.html -->
<div class="bg-white p-4 rounded shadow">
    <!-- Clases de Tailwind aquí -->
</div>
```

**2. Verificar hx-swap**
```html
<!-- innerHTML: reemplaza contenido interno -->
<div id="result" hx-get="/api/" hx-swap="innerHTML">

<!-- outerHTML: reemplaza elemento completo -->
<div id="result" hx-get="/api/" hx-swap="outerHTML">
```

---

### Problema: Polling no se detiene

#### Síntoma
```html
<div hx-get="/status/" hx-trigger="every 5s">
<!-- Sigue haciendo requests incluso cuando ya completó -->
</div>
```

#### Soluciones

**1. Usar condiciones en hx-trigger**
```html
<div 
    hx-get="/status/" 
    hx-trigger="every 5s [status !== 'completed']"
    data-status="{{ video.status }}">
```

**2. Detener desde el backend**
```python
# views.py
def status_view(request):
    video = get_object_or_404(Video, pk=video_id)
    response = render(request, 'partials/status.html', {'video': video})
    
    # Decirle a HTMX que pare el polling
    if video.status == 'completed':
        response['HX-Trigger'] = 'stopPolling'
    
    return response
```

```html
<div 
    hx-get="/status/" 
    hx-trigger="every 5s"
    hx-on:stopPolling="htmx.trigger(this, 'htmx:abort')">
</div>
```

---

### Problema: CSRF token error (403 Forbidden)

#### Síntoma
```
Forbidden (403)
CSRF verification failed. Request aborted.
```

#### Soluciones

**1. Incluir {% csrf_token %} en formularios**
```html
<form hx-post="/api/create/">
    {% csrf_token %}
    <input name="name">
    <button>Submit</button>
</form>
```

**2. Para requests fuera de forms, configurar HTMX**
```html
<!-- En base.html -->
<script>
document.body.addEventListener('htmx:configRequest', (event) => {
    // Obtener CSRF token
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    // Agregar header
    event.detail.headers['X-CSRFToken'] = csrftoken;
});
</script>
```

---

## 🏔️ Alpine.js

### Problema: Alpine no funciona (nada pasa)

#### Síntoma
```html
<div x-data="{ open: false }">
    <button @click="open = true">Abrir</button>
    <div x-show="open">Modal</div>
    <!-- Click no hace nada -->
</div>
```

#### Soluciones

**1. Verificar que Alpine esté cargando**
```javascript
// En DevTools Console
console.log(Alpine);
// Si dice "undefined", Alpine no está cargado
```

**2. Verificar el script en base.html**
```html
<!-- ⚠️ IMPORTANTE: defer es necesario -->
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.13.5/dist/cdn.min.js"></script>
```

**3. Ver errores en Console**
```
F12 → Console tab
Buscar errores en rojo
```

**4. Verificar sintaxis**
```html
<!-- ✅ BIEN -->
<div x-data="{ open: false }">
    <button @click="open = true">

<!-- ❌ MAL: Comillas -->
<div x-data='{ open: false }'>  <!-- Usar " -->

<!-- ❌ MAL: x-data debe estar en elemento padre -->
<div>
    <button x-data="{ open: false }" @click="open = true">
    <!-- open no está disponible aquí -->
</div>
```

---

### Problema: Flash de contenido antes de Alpine cargar

#### Síntoma
```html
<div x-data="{ show: false }">
    <div x-show="show">Modal</div>
    <!-- Se ve el modal por un momento antes de Alpine cargar -->
</div>
```

#### Solución

Usar `x-cloak`:

```html
<div x-data="{ show: false }" x-cloak>
    <div x-show="show">Modal</div>
</div>

<style>
[x-cloak] { display: none !important; }
</style>
```

---

### Problema: Estado no se actualiza

#### Síntoma
```html
<div x-data="{ count: 0 }">
    <button @click="count++">Increment</button>
    <span x-text="count"></span>
    <!-- El span no se actualiza -->
</div>
```

#### Soluciones

**1. Usar x-text, no {{ }}**
```html
<!-- ✅ BIEN -->
<span x-text="count"></span>

<!-- ❌ MAL: {{ }} es para Django, no Alpine -->
<span>{{ count }}</span>
```

**2. Verificar scope**
```html
<!-- ✅ BIEN: count está en x-data padre -->
<div x-data="{ count: 0 }">
    <button @click="count++">...</button>
    <span x-text="count"></span>
</div>

<!-- ❌ MAL: count no está disponible -->
<div>
    <button x-data="{ count: 0 }" @click="count++">...</button>
    <span x-text="count"></span>  <!-- count undefined aquí -->
</div>
```

---

### Problema: Click fuera no cierra dropdown

#### Síntoma
```html
<div x-data="{ open: false }">
    <button @click="open = !open">Menu</button>
    <div x-show="open">...</div>
    <!-- Click fuera no cierra -->
</div>
```

#### Solución

Usar `@click.away`:

```html
<div x-data="{ open: false }" @click.away="open = false">
    <button @click="open = !open">Menu</button>
    <div x-show="open">...</div>
</div>
```

---

## 🐍 Django Templates

### Problema: Variable no se muestra

#### Síntoma
```html
<p>{{ user.name }}</p>
<!-- Muestra vacío -->
```

#### Soluciones

**1. Verificar que la variable esté en el context**
```python
# views.py
def my_view(request):
    return render(request, 'template.html', {
        'user': user  # ← Asegúrate de pasar la variable
    })
```

**2. Verificar el nombre**
```html
<!-- ✅ BIEN -->
{{ user.name }}

<!-- ❌ MAL: typo -->
{{ user.nome }}
```

**3. Debugging: Ver todas las variables disponibles**
```html
<!-- Temporalmente, para debug -->
{{ debug }}  <!-- Si DEBUG=True en settings.py -->

<!-- O más específico -->
{% if user %}
    <p>User existe: {{ user }}</p>
{% else %}
    <p>User NO existe</p>
{% endif %}
```

---

### Problema: URL no funciona

#### Síntoma
```html
<a href="{% url 'core:project_detail' project.id %}">
<!-- Error: NoReverseMatch -->
</a>
```

#### Soluciones

**1. Verificar que la URL exista**
```python
# core/urls.py
app_name = 'core'

urlpatterns = [
    path('projects/<int:pk>/', 
         views.ProjectDetailView.as_view(), 
         name='project_detail'),  # ← El name debe coincidir
]
```

**2. Verificar app_name**
```python
# Si usas 'core:project_detail', debes tener:
app_name = 'core'
```

**3. Verificar parámetros**
```html
<!-- ✅ BIEN -->
{% url 'core:project_detail' project.id %}

<!-- ❌ MAL: falta parámetro -->
{% url 'core:project_detail' %}

<!-- ❌ MAL: parámetro incorrecto -->
{% url 'core:project_detail' project %}  <!-- Debe ser project.id -->
```

---

## 🌐 Problemas Generales

### Cambios no se reflejan

#### Soluciones

**1. Hard refresh**
```
Ctrl + F5 (Windows)
Cmd + Shift + R (Mac)
```

**2. Limpiar cache del navegador**
```
Ctrl + Shift + Delete
→ Cached images and files
→ Clear data
```

**3. Verificar que el servidor esté corriendo**
```bash
# Si cerraste el servidor
python manage.py runserver
```

**4. Verificar que guardaste el archivo**
```
Ctrl + S (Windows/Mac)
```

---

### Página en blanco / Error 500

#### Soluciones

**1. Ver logs del servidor**
```
# Terminal donde corre runserver
# Busca el traceback en rojo
```

**2. Ver error completo**
```
# En settings.py, temporalmente:
DEBUG = True

# Recarga la página
# Verás el error detallado
```

**3. Ver DevTools Console**
```
F12 → Console
Busca errores en rojo
```

---

### DevTools (F12) no abre

#### Solución

Atajos alternativos:
```
Windows:
- F12
- Ctrl + Shift + I
- Ctrl + Shift + J (directo a Console)

Mac:
- Cmd + Option + I
- Cmd + Option + J (directo a Console)
```

---

## 🔧 Herramientas de Debugging

### Ver peticiones HTMX

```javascript
// En Console
htmx.logAll();
```

### Ver estado de Alpine

```javascript
// Selecciona elemento en Inspector, luego en Console:
$el.__x.$data  // Ver datos
$el.__x  // Ver todo el contexto
```

### Ver variables de Django

```html
<!-- En template, temporalmente -->
<pre>{{ variable|pprint }}</pre>

<!-- Ver TODO el contexto -->
{% load static %}
{% debug %}
```

### Ver estilos aplicados

```
F12 → Inspector (Elements)
Click en elemento
Ver panel "Styles" a la derecha
```

---

## 📞 ¿Todavía no funciona?

### Checklist completo

- [ ] Hard refresh (Ctrl + F5)
- [ ] Limpiar cache del navegador
- [ ] Ver Console (F12) para errores
- [ ] Ver Network tab para requests fallidos
- [ ] Verificar logs del servidor Django
- [ ] Verificar que el archivo esté guardado
- [ ] Verificar sintaxis (typos)
- [ ] Leer el mensaje de error completo

### Pedir ayuda

Cuando pidas ayuda, incluye:

1. **Qué intentas hacer**
   - "Quiero que este botón cargue proyectos"

2. **Qué pasa actualmente**
   - "No pasa nada al hacer click"

3. **Código relevante**
   ```html
   <button hx-get="/api/projects/">Cargar</button>
   ```

4. **Errores (si hay)**
   - Screenshot de Console
   - Screenshot de Network tab
   - Logs del servidor

5. **Qué ya intentaste**
   - "Ya hice hard refresh"
   - "Ya verifiqué que HTMX esté cargando"

---

## 📚 Recursos Adicionales

- [HTMX Debugging](https://htmx.org/docs/#debugging)
- [Alpine.js DevTools](https://chrome.google.com/webstore/detail/alpinejs-devtools/)
- [Django Debug Toolbar](https://django-debug-toolbar.readthedocs.io/)

