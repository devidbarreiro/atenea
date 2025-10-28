# 🎨 Frontend - Atenea

> Documentación completa del frontend para desarrolladores

## 📋 Stack Tecnológico

- **Tailwind CSS** - Framework CSS utility-first (via CDN)
- **HTMX** - Interactividad AJAX sin JavaScript complejo
- **Alpine.js** - Componentes reactivos ligeros
- **Django Templates** - Server-side rendering

## 🚀 Inicio Rápido

### 1. Configuración Inicial

```bash
# Clonar y activar entorno
git clone git@github.com:devidbarreiro/atenea.git
cd atenea
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp env.example .env
# Editar .env con tus credenciales

# Migrar base de datos
python manage.py migrate

# Iniciar servidor
python manage.py runserver
```

### 2. Estructura de Archivos Frontend

```
atenea/
├── templates/              # Templates Django
│   ├── base.html          # Template base con Tailwind/HTMX/Alpine
│   ├── dashboard/         # Vistas del dashboard
│   ├── projects/          # CRUD de proyectos
│   ├── videos/            # CRUD de videos
│   ├── images/            # CRUD de imágenes
│   ├── scripts/           # CRUD de guiones
│   └── partials/          # Componentes reutilizables
│       ├── video_status.html      # Badge de estado con HTMX polling
│       ├── image_status.html      # Badge de estado de imagen
│       ├── confirm_modal.html     # Modal de confirmación Alpine
│       └── script_status.html     # Badge de estado de script
├── static/                # Archivos estáticos
│   ├── img/              # Imágenes
│   └── js/               # JavaScript personalizado
└── theme/                 # App de Tailwind (preparada para Node.js)
```

## 📚 Documentación

### Para Empezar
- [Guía de Inicio Rápido](./quick-start.md) - Primeros pasos con el frontend
- [Stack Tecnológico](./stack.md) - Detalles de Tailwind, HTMX, Alpine

### Componentes y Patrones
- [Componentes Reutilizables](./components.md) - Biblioteca de componentes
- [Patrones HTMX](./htmx-patterns.md) - Cómo usar HTMX en el proyecto
- [Patrones Alpine.js](./alpine-patterns.md) - Componentes reactivos con Alpine

### Guías de Desarrollo
- [Convenciones de Código](./conventions.md) - Estándares y mejores prácticas
- [Guía de Tailwind](./tailwind-guide.md) - Uso de Tailwind CSS
- [Testing Frontend](./testing.md) - Cómo testear componentes

### Referencia
- [API de Vistas](./views-api.md) - Endpoints y respuestas
- [Django Templates](./django-templates.md) - Sistema de templates
- [Troubleshooting](./troubleshooting.md) - Solución de problemas comunes

## 🎯 Conceptos Clave

### 1. Server-Side Rendering (SSR)
Atenea usa Django templates para renderizar HTML en el servidor. No es una SPA, lo que significa:
- ✅ SEO-friendly por defecto
- ✅ Tiempo de carga inicial rápido
- ✅ No necesita build step complejo
- ✅ Estado manejado por el servidor

### 2. HTMX para Interactividad
HTMX permite hacer peticiones AJAX y actualizar el DOM sin escribir JavaScript:
```html
<div hx-get="/api/status/" hx-trigger="every 5s" hx-swap="outerHTML">
    Estado: Procesando...
</div>
```

### 3. Alpine.js para Componentes Locales
Alpine maneja estado y lógica reactiva local (modals, dropdowns, toggles):
```html
<div x-data="{ open: false }">
    <button @click="open = true">Abrir Modal</button>
    <div x-show="open">Contenido del Modal</div>
</div>
```

### 4. Tailwind CSS para Estilos
Clases utility-first directamente en el HTML:
```html
<button class="bg-black text-white hover:bg-gray-800 px-4 py-2 rounded-md">
    Botón
</button>
```

## 🔧 Tareas Comunes

### Crear un Nuevo Componente
```bash
# 1. Crear template en templates/partials/
# 2. Incluir con {% include 'partials/mi_componente.html' %}
```

### Agregar una Nueva Vista
```bash
# 1. Editar templates/nueva_vista.html
# 2. Extender de base.html
# 3. Usar bloques: title, content, extra_js, extra_css
```

### Agregar Interactividad con HTMX
```html
<!-- Polling automático -->
<div hx-get="/status/" hx-trigger="every 5s">...</div>

<!-- Click para actualizar -->
<button hx-post="/api/action/" hx-target="#result">Acción</button>

<!-- Formulario AJAX -->
<form hx-post="/api/create/" hx-swap="outerHTML">...</form>
```

### Crear Modal con Alpine
```html
<div x-data="{ showModal: false }">
    <button @click="showModal = true">Abrir</button>
    <div x-show="showModal" @click.away="showModal = false">
        <!-- Contenido del modal -->
    </div>
</div>
```

## 🎨 Paleta de Colores

```css
/* Colores principales */
bg-black       /* Botones primarios */
bg-white       /* Fondos de cards */
bg-gray-50     /* Fondo de página */
bg-gray-100    /* Hover states */

/* Estados */
bg-green-500   /* Success/Completado */
bg-yellow-500  /* Warning/Procesando */
bg-red-500     /* Error */
bg-blue-500    /* Info/Secondary */
bg-purple-600  /* Accent */
```

## 📝 Convenciones de Nombres

### Templates
- `nombre_modelo_action.html` → `project_create.html`, `video_detail.html`
- Partials en `partials/` con nombres descriptivos
- Includes en `includes/` para layouts compartidos

### Clases CSS
- Usar clases de Tailwind directamente
- Para estilos custom, agregarlos en `<style>` de `base.html`
- Evitar CSS custom innecesario

### IDs y Nombres
- IDs en kebab-case: `video-grid-view`
- Data attributes: `data-video-id="123"`
- Alpine data: camelCase `x-data="{ isOpen: false }"`

## 🐛 Debugging

### Ver Peticiones HTMX
```javascript
// En la consola del navegador
htmx.logAll();
```

### Problemas con Alpine
- Verificar que `x-data` esté en el elemento padre
- Usar `x-cloak` para evitar flash de contenido
- Abrir DevTools y buscar errores en consola

### Estilos no se aplican
- Hard refresh: `Ctrl + F5` (Windows) o `Cmd + Shift + R` (Mac)
- Verificar que las clases de Tailwind existan
- Ver DevTools → Network para verificar que los CDN carguen

## 🚀 Próximos Pasos

1. Lee la [Guía de Inicio Rápido](./quick-start.md)
2. Revisa los [Componentes Reutilizables](./components.md)
3. Estudia los [Patrones HTMX](./htmx-patterns.md)
4. Lee las [Convenciones de Código](./conventions.md)

## 📞 ¿Necesitas Ayuda?

- 🐛 Bug? Crea un issue en GitHub
- 💡 Pregunta? Contacta al equipo
- 📖 Documentación incompleta? Abre un PR

---

**Última actualización**: Octubre 2025

