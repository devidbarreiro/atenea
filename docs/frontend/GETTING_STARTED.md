# 🚀 Getting Started - Frontend Developer

> Todo lo que necesitas saber para empezar a desarrollar en Atenea

## 👋 Bienvenido!

Atenea es una plataforma para generar videos e imágenes con IA. Como frontend developer, trabajarás principalmente con:

- **Tailwind CSS** - Para estilos
- **HTMX** - Para interactividad AJAX
- **Alpine.js** - Para componentes reactivos
- **Django Templates** - Para renderizar HTML

**No necesitas** Node.js, npm, webpack, o complejos build tools. Todo funciona con CDNs. 🎉

---

## ⚡ Setup en 5 Minutos

```bash
# 1. Clonar repo
git clone <repo-url>
cd atenea

# 2. Crear y activar entorno virtual
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar .env (copiar de env.example)
# Mínimo necesario:
# SECRET_KEY=cualquier-string-aleatorio
# DEBUG=True
# ALLOWED_HOSTS=localhost,127.0.0.1

# 5. Migrar DB
python manage.py migrate

# 6. Iniciar servidor
python manage.py runserver
```

Abre http://127.0.0.1:8000/ - ¡Listo! ✅

---

## 📁 Dónde Trabajarás

```
atenea/
├── templates/              # 👈 90% de tu trabajo estará aquí
│   ├── base.html          # Template base (navbar, scripts)
│   ├── dashboard/         # Dashboard principal
│   ├── projects/          # Páginas de proyectos
│   ├── videos/            # Páginas de videos
│   ├── images/            # Páginas de imágenes
│   └── partials/          # Componentes reutilizables
│       ├── video_status.html
│       ├── confirm_modal.html
│       └── ...
│
├── static/                # 👈 10% aquí
│   ├── img/              # Imágenes
│   └── js/               # JavaScript custom (opcional)
│
└── core/
    └── views.py          # Backend (solo para entender qué datos llegan)
```

---

## 🎨 Tu Primera Tarea

Vamos a cambiar el título del dashboard:

**1. Abre**: `templates/dashboard/index.html`

**2. Busca esta línea** (cerca de la línea 8):
```html
<h1 class="text-4xl font-bold mb-2">Dashboard</h1>
```

**3. Cámbiala a**:
```html
<h1 class="text-4xl font-bold mb-2">Mi Dashboard 🚀</h1>
```

**4. Guarda** (Ctrl+S)

**5. Recarga** el navegador (F5)

¡Ya hiciste tu primer cambio! 🎉

---

## 🛠️ Flujo de Trabajo Diario

### 1. Editar HTML/Templates

```bash
# Archivos en templates/*.html
# Guardas, recargas navegador → ves cambios
```

### 2. Agregar Estilos (Tailwind)

```html
<!-- En lugar de escribir CSS... -->
<div class="bg-white p-6 rounded-lg shadow-md hover:shadow-xl">
    <!-- ...usas clases de Tailwind -->
</div>
```

### 3. Agregar Interactividad (HTMX)

```html
<!-- Auto-actualización cada 5s -->
<div hx-get="/api/status/" hx-trigger="every 5s">
    Estado: {{ video.status }}
</div>
```

### 4. Componentes Reactivos (Alpine)

```html
<!-- Modal con Alpine.js -->
<div x-data="{ open: false }">
    <button @click="open = true">Abrir Modal</button>
    <div x-show="open">Contenido del modal</div>
</div>
```

---

## 📚 Documentación Esencial

Lee estos documentos **en orden**:

### Día 1 - Setup y Basics
1. ✅ Este archivo (ya lo leíste!)
2. **[Quick Start](./quick-start.md)** (20 min) - Tutorial paso a paso
3. **[Visual Cheat Sheet](./visual-cheatsheet.md)** (10 min) - Referencia rápida

### Día 2 - Stack Tecnológico
4. **[Stack](./stack.md)** (30 min) - Entender Tailwind, HTMX, Alpine
5. **[Convenciones](./conventions.md)** (20 min) - Cómo escribimos código

### Día 3 - Componentes
6. **[Componentes](./components.md)** (30 min) - Qué componentes hay disponibles
7. **[HTMX Patterns](./htmx-patterns.md)** (30 min) - Patrones de interactividad
8. **[Alpine Patterns](./alpine-patterns.md)** (30 min) - Componentes reactivos

### Día 4+ - Profundizar
9. **[Django Templates](./django-templates.md)** (30 min) - Sistema de templates
10. **[Troubleshooting](./troubleshooting.md)** - Para cuando algo no funciona

**Tiempo total de lectura**: ~4 horas  
**Pero puedes empezar a trabajar desde el Día 1** ✨

---

## 🎯 Conceptos Clave (5 minutos)

### 1. Server-Side Rendering (SSR)

El HTML se genera en el **servidor** (Django), no en el navegador.

```python
# Backend (Django views.py)
def dashboard(request):
    projects = Project.objects.all()
    return render(request, 'dashboard.html', {
        'projects': projects  # ← Pasa datos al template
    })
```

```html
<!-- Frontend (template.html) -->
{% for project in projects %}
    <div>{{ project.name }}</div>
{% endfor %}
```

**Pro**: SEO excelente, carga rápida inicial  
**Con**: No es una SPA tipo React

---

### 2. Tailwind CSS (Utility-first)

Clases pequeñas que combinas:

```html
<!-- Tradicional -->
<style>
.card { background: white; padding: 24px; border-radius: 8px; }
</style>
<div class="card">...</div>

<!-- Tailwind -->
<div class="bg-white p-6 rounded-lg">...</div>
```

**Pro**: Rápido, no inventar nombres  
**Con**: HTML más verbose

[📖 Tailwind Docs](https://tailwindcss.com/docs)

---

### 3. HTMX (AJAX sin JavaScript)

```html
<!-- Sin HTMX -->
<button onclick="fetch('/api/').then(r => r.text()).then(html => ...)">
    Cargar
</button>

<!-- Con HTMX -->
<button hx-get="/api/" hx-target="#result">
    Cargar
</button>
<div id="result"></div>
```

**Pro**: Simple, menos código  
**Con**: Menos control fino

[📖 HTMX Docs](https://htmx.org/docs/)

---

### 4. Alpine.js (Reactividad local)

```html
<div x-data="{ count: 0 }">
    <button @click="count++">Increment</button>
    <span x-text="count"></span>
</div>
```

**Pro**: Ligero, fácil  
**Con**: No para estado global complejo

[📖 Alpine Docs](https://alpinejs.dev/)

---

## 🎨 Ejemplo Completo

Veamos un componente real del proyecto:

```html
<!-- templates/partials/video_status.html -->

<!-- HTMX: Se auto-actualiza cada 5s -->
<div 
    hx-get="{% url 'core:video_status_partial' video.id %}" 
    hx-trigger="every 5s"
    hx-swap="outerHTML">
    
    <!-- Django: Lógica condicional -->
    {% if video.status == 'completed' %}
        <!-- Tailwind: Clases para estilos -->
        <span class="bg-green-500 text-white px-3 py-1 rounded-md text-xs font-semibold">
            ✓ Completado
        </span>
    {% elif video.status == 'processing' %}
        <span class="bg-yellow-500 text-white px-3 py-1 rounded-md text-xs font-semibold">
            <span class="animate-spin">⚙️</span>
            Procesando...
        </span>
    {% else %}
        <span class="bg-gray-500 text-white px-3 py-1 rounded-md text-xs font-semibold">
            Pendiente
        </span>
    {% endif %}
</div>
```

**Qué hace**:
1. Cada 5 segundos hace GET al servidor
2. Recibe HTML actualizado
3. Reemplaza el div con el nuevo HTML
4. Muestra badge según el estado

**Sin escribir JavaScript!** 🎉

---

## 🐛 Debugging Básico

### Ver Errores

```
1. F12 → Console
   Busca errores en rojo

2. F12 → Network
   Filtra por "XHR" para ver peticiones HTMX

3. Terminal donde corre runserver
   Ver errores de Django
```

### Problema Común: Estilos no se aplican

```bash
# Solución 1: Hard refresh
Ctrl + F5 (Windows)
Cmd + Shift + R (Mac)

# Solución 2: Limpiar cache
Ctrl + Shift + Delete → Clear cache
```

### Debugging HTMX

```javascript
// En Console (F12)
htmx.logAll();
// Ahora verás logs de todas las peticiones HTMX
```

---

## ✅ Checklist del Primer Día

Marca cuando completes cada item:

- [ ] Proyecto instalado y corriendo
- [ ] Servidor abierto en http://127.0.0.1:8000/
- [ ] Hice mi primer cambio (cambié el título del dashboard)
- [ ] Leí el [Quick Start](./quick-start.md)
- [ ] Guardé el [Visual Cheat Sheet](./visual-cheatsheet.md) en favoritos
- [ ] Entiendo la estructura de `templates/`
- [ ] Sé usar DevTools (F12)
- [ ] Probé hacer un hard refresh (Ctrl+F5)

---

## 🚀 Siguientes Pasos

### Inmediato (hoy)
1. Completa el [Quick Start](./quick-start.md)
2. Haz el ejercicio práctico (agregar contador de scripts)
3. Explora los archivos en `templates/`

### Esta Semana
4. Lee [Componentes](./components.md)
5. Lee [HTMX Patterns](./htmx-patterns.md)
6. Lee [Alpine Patterns](./alpine-patterns.md)
7. Toma tu primera tarea real del proyecto

### Este Mes
8. Lee [Convenciones](./conventions.md) completo
9. Contribuye un nuevo componente
10. Ayuda a mejorar la documentación

---

## 📞 ¿Necesitas Ayuda?

### Recursos
- **[Visual Cheat Sheet](./visual-cheatsheet.md)** - Referencia rápida
- **[Troubleshooting](./troubleshooting.md)** - Problemas comunes
- **[Tailwind Docs](https://tailwindcss.com/docs)** - Documentación oficial
- **[HTMX Docs](https://htmx.org/docs/)** - Documentación oficial
- **[Alpine Docs](https://alpinejs.dev/)** - Documentación oficial

### Contacto
- 🐛 **Bug?** Crea un issue
- 💡 **Pregunta?** Contacta al equipo
- 💬 **Chat?** [Canal del equipo]

---

## 🎉 ¡Listo para Empezar!

Ahora que tienes el contexto básico:

1. **[Quick Start](./quick-start.md)** - Comienza aquí
2. **[Visual Cheat Sheet](./visual-cheatsheet.md)** - Guárdalo en favoritos
3. **Abre el proyecto** - Empieza a explorar

**Recuerda**: No necesitas saberlo todo de memoria. La documentación está aquí para consultarla cuando la necesites.

¡Bienvenido al equipo! 🚀

---

**Última actualización**: Octubre 27, 2025

