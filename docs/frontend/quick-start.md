# 🚀 Guía de Inicio Rápido - Frontend

> Comienza a desarrollar en el frontend de Atenea en 10 minutos

## ⚡ Setup en 3 Pasos

### 1. Instalar y Configurar (5 minutos)

```bash
# 1. Clonar repositorio
git clone git@github.com:devidbarreiro/atenea.git
cd atenea

# 2. Crear entorno virtual
python -m venv venv

# 3. Activar entorno
# Windows:
.\venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Configurar variables de entorno
cp env.example .env
# Edita .env con tus credenciales (mínimo: SECRET_KEY, DEBUG=True)

# 6. Migrar base de datos
python manage.py migrate

# 7. Crear superusuario (opcional)
python manage.py createsuperuser
```

### 2. Iniciar Servidor (1 minuto)

```bash
python manage.py runserver
```

Abre http://127.0.0.1:8000/ en tu navegador.

### 3. Hacer Tu Primer Cambio (3 minutos)

Vamos a cambiar el título del dashboard:

```bash
# Abre templates/dashboard/index.html
```

Busca esta línea:
```html
<h1 class="text-4xl font-bold mb-2">Dashboard</h1>
```

Cámbiala a:
```html
<h1 class="text-4xl font-bold mb-2">Mi Dashboard 🚀</h1>
```

Guarda el archivo y recarga la página. ¡Listo! ✅

## 📁 Estructura del Proyecto

```
atenea/
├── templates/              # 👈 Aquí trabajarás principalmente
│   ├── base.html          # Template base (navbar, footer, scripts)
│   ├── dashboard/         # Página principal
│   ├── projects/          # Páginas de proyectos
│   ├── videos/            # Páginas de videos
│   ├── images/            # Páginas de imágenes
│   └── partials/          # Componentes reutilizables
│
├── static/                # Archivos estáticos (img, js custom)
├── core/
│   ├── views.py          # Vistas Django (backend)
│   ├── models.py         # Modelos de datos
│   └── urls.py           # URLs y rutas
└── atenea/
    └── settings.py       # Configuración del proyecto
```

## 🎨 Stack Frontend

### Tailwind CSS (Utility-first CSS)
```html
<!-- En lugar de escribir CSS, usas clases: -->
<div class="bg-white shadow-lg rounded-lg p-6 hover:shadow-xl">
    <h2 class="text-2xl font-bold mb-4">Card</h2>
    <p class="text-gray-600">Contenido</p>
</div>
```

### HTMX (AJAX sin JavaScript)
```html
<!-- Auto-actualización cada 5 segundos -->
<div hx-get="/api/status/" hx-trigger="every 5s">
    Estado: Cargando...
</div>
```

### Alpine.js (Interactividad local)
```html
<!-- Modal interactivo -->
<div x-data="{ open: false }">
    <button @click="open = true">Abrir Modal</button>
    <div x-show="open">
        Modal content
        <button @click="open = false">Cerrar</button>
    </div>
</div>
```

## 🛠️ Flujo de Trabajo

### 1. Entender el Sistema de Templates

Atenea usa **Django Templates**, que son HTML con superpoderes:

#### Template Base (`base.html`)
Contiene la estructura común (navbar, footer, scripts):
```html
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}Atenea{% endblock %}</title>
    <!-- Tailwind, HTMX, Alpine -->
</head>
<body>
    <nav><!-- Navbar --></nav>
    <main>
        {% block content %}{% endblock %}
    </main>
</body>
</html>
```

#### Templates Específicos (ej: `dashboard/index.html`)
Extienden de `base.html` y sobreescriben bloques:
```html
{% extends 'base.html' %}

{% block title %}Dashboard - Atenea{% endblock %}

{% block content %}
<h1>Dashboard</h1>
<!-- Tu contenido aquí -->
{% endblock %}
```

### 2. Componentes Reutilizables

Los componentes están en `templates/partials/`:

```html
<!-- templates/partials/video_status.html -->
<div hx-get="{% url 'core:video_status_partial' video.id %}" 
     hx-trigger="every 5s">
    {% if video.status == 'completed' %}
        <span class="bg-green-500 text-white px-3 py-1 rounded">Completado</span>
    {% endif %}
</div>
```

Para usarlo:
```html
{% include 'partials/video_status.html' with video=mi_video %}
```

### 3. Trabajar con Datos

Los datos vienen del backend (Django views) como **contexto**:

```python
# core/views.py
def dashboard(request):
    return render(request, 'dashboard/index.html', {
        'projects': Project.objects.all(),
        'total_videos': Video.objects.count(),
    })
```

```html
<!-- dashboard/index.html -->
<p>Total de videos: {{ total_videos }}</p>

{% for project in projects %}
    <div>{{ project.name }}</div>
{% endfor %}
```

## 🎯 Ejercicio Práctico

Vamos a agregar un contador de scripts en el dashboard:

### Paso 1: Verificar que el backend pase los datos
Abre `core/views.py` y busca `DashboardView`. Ya tiene:
```python
'total_scripts': Script.objects.count(),
```

### Paso 2: Agregar la tarjeta en el template
Abre `templates/dashboard/index.html` y busca las estadísticas.

Agrega esta tarjeta después de "Imágenes":
```html
<div class="stat bg-white rounded-lg p-6 shadow-sm border border-gray-200">
    <div class="stat-figure text-accent">
        <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
    </div>
    <div class="stat-title text-sm text-gray-600">Scripts</div>
    <div class="stat-value text-3xl font-bold text-blue-600">{{ total_scripts }}</div>
    <div class="stat-desc text-xs text-gray-500">{{ completed_scripts }} completados</div>
</div>
```

### Paso 3: Probar
1. Guarda el archivo
2. Recarga http://127.0.0.1:8000/
3. ¡Deberías ver la nueva tarjeta! 🎉

## 📚 Recursos Útiles

### Tailwind CSS
- [Documentación oficial](https://tailwindcss.com/docs)
- [Cheat sheet](https://nerdcave.com/tailwind-cheat-sheet)
- Tip: Busca "tailwind [cosa que quieres]" en Google

### HTMX
- [Documentación oficial](https://htmx.org/docs/)
- [Ejemplos](https://htmx.org/examples/)
- En el proyecto: Ver `partials/video_status.html`

### Alpine.js
- [Documentación oficial](https://alpinejs.dev/)
- [Ejemplos](https://alpinejs.dev/start-here)
- En el proyecto: Ver `partials/confirm_modal.html`

## 🐛 Troubleshooting

### Los estilos no se ven
1. Hard refresh: `Ctrl + F5` (Windows) o `Cmd + Shift + R` (Mac)
2. Verifica que `base.html` cargue el CDN de Tailwind
3. Abre DevTools (F12) → Console para ver errores

### HTMX no funciona
1. Abre DevTools → Network
2. Busca peticiones AJAX (deberían aparecer cada 5s si hay polling)
3. Verifica que la URL en `hx-get` sea correcta

### Alpine no funciona
1. Verifica que `x-data` esté en el elemento padre
2. Abre DevTools → Console para ver errores
3. Asegúrate de que el script de Alpine esté en `base.html`

### Cambios no se reflejan
1. Guarda el archivo (Ctrl+S)
2. Recarga la página (F5)
3. Si persiste, reinicia el servidor Django

## ✅ Checklist del Primer Día

- [ ] Proyecto clonado y funcionando
- [ ] Servidor corriendo en http://127.0.0.1:8000/
- [ ] Hice un cambio y lo vi reflejado
- [ ] Entiendo la estructura de templates
- [ ] Sé dónde están los componentes reutilizables
- [ ] Leí la documentación de Tailwind, HTMX, Alpine

## 🚀 Siguientes Pasos

1. **Explora los componentes existentes**
   - Abre `templates/partials/` y lee cada archivo
   - Entiende cómo funcionan

2. **Lee las guías específicas**
   - [Componentes Reutilizables](./components.md)
   - [Patrones HTMX](./htmx-patterns.md)
   - [Convenciones de Código](./conventions.md)

3. **Toma tu primera tarea**
   - Busca issues etiquetados con `frontend` o `good-first-issue`
   - Pregunta al equipo

---

¡Bienvenido al equipo! 🎉

