# 📋 PLAN: Nueva UI de Creación y Biblioteca

## 🎯 Objetivo
Rediseñar las plantillas de creación de items (video, imagen, audio) con un nuevo layout estilo Freepik AI Suite:
- Sidebar general (izquierda) + Sidebar creación (izquierda, fijo) + Panel derecho (biblioteca)
- Formularios dinámicos según modelo seleccionado
- Modal para detalles de items
- Breadcrumbs globales
- Nueva estructura de URLs

---

## 📐 Estructura de URLs

### Cambios en URLs

**ANTES:**
- `/projects/2/videos/create/` → Crear video
- `/videos/create/` → Crear video standalone
- `/videos/28/` → Detalle video

**DESPUÉS:**
- `/projects/2/` → Vista general del proyecto (simple)
- `/projects/2/videos/` → Formulario creación + Biblioteca (mismo layout)
- `/videos/` → Formulario creación + Biblioteca standalone
- `/videos/28/` → Modal de detalle (mantiene URL, no nueva página)
- `/images/` → Formulario creación + Biblioteca standalone
- `/images/2/` → Modal de detalle
- `/audios/` → Formulario creación + Biblioteca standalone
- `/audios/3/` → Modal de detalle

### URLs a Eliminar
- `/projects/2/videos/create/`
- `/videos/create/`
- `/projects/2/images/create/`
- `/images/create/`
- `/projects/2/audios/create/`
- `/audios/create/`

---

## 🏗️ Arquitectura de Componentes

### 1. Sistema de Configuración de Modelos

**Archivo:** `core/ai_services/model_config.py`

Crear un sistema centralizado que defina las capacidades de cada modelo:

```python
MODEL_CAPABILITIES = {
    'gemini_veo_2.0': {
        'service': 'gemini_veo',
        'name': 'Veo 2.0',
        'type': 'video',
        'supports': {
            'text_to_video': True,
            'image_to_video': True,
            'duration': {'min': 5, 'max': 8, 'options': [5, 6, 7, 8]},
            'aspect_ratio': ['16:9', '9:16'],
            'resolution': False,
            'audio': False,
            'references': {
                'start_image': False,
                'end_image': False,
                'style_image': False,
                'asset_image': False,
            },
            'negative_prompt': True,
            'seed': True,
        },
        'logo': '/static/img/logos/google.svg',  # o '/static/images/logos/google.svg'
    },
    'higgsfield_dop_standard': {
        'service': 'higgsfield',
        'name': 'DoP Standard',
        'type': 'video',
        'supports': {
            'text_to_video': False,
            'image_to_video': True,
            'duration': {'fixed': 3},
            'aspect_ratio': ['16:9', '9:16', '1:1'],
            'resolution': ['720p'],
            'audio': False,
            'references': {
                'start_image': True,  # image_url
                'end_image': False,
            },
        },
        'logo': '/static/img/logos/higgsfield.svg',  # o '/static/images/logos/higgsfield.svg'
    },
    # ... más modelos
}
```

### 2. Sidebar de Creación (Componente Dinámico)

**Archivo:** `templates/includes/creation_sidebar.html`

Estructura:
- **Tabs:** Image / Video / Audio (solo en creación)
- **MODEL:** Dropdown con búsqueda, logos de servicios, info de cada modelo
- **REFERENCES:** Sección dinámica según modelo
  - Start image (upload o seleccionar de biblioteca)
  - End image (si soporta)
  - Style image (si soporta)
- **PROMPT:** 
  - Tab "Text" (textarea)
  - Tab "Visual" (futuro, por ahora disabled)
- **SETTINGS:** Campos dinámicos según modelo
  - Duration (si permite opciones)
  - Aspect ratio (si permite opciones)
  - Resolution (si permite opciones)
  - Audio toggle (si soporta)
  - Negative prompt (si soporta)
  - Seed (si soporta)

**JavaScript:** `static/js/creation_sidebar.js`
- Cambio de modelo → actualizar campos dinámicamente
- Validación de campos según modelo
- Submit del formulario

### 3. Panel Derecho (Biblioteca)

**Archivo:** `templates/includes/library_panel.html`

Muestra:
- Grid de cards (reutilizar `media_card.html`)
- Filtrado por tipo (video/image/audio)
- Filtrado por proyecto (si estamos en proyecto)
- Empty state cuando no hay items
- Click en card → abre modal de detalle

### 4. Modal de Detalle

**Archivo:** `templates/includes/item_detail_modal.html`

Estructura similar a la captura de la rana:
- Imagen/video grande a la izquierda
- Panel de detalles a la derecha:
  - PROMPT
  - REFERENCE (si tiene)
  - SETTINGS (modelo usado, resolución, etc.)
  - Acciones: Recreate, Upscale, Create video, Variations, Edit
- Navegación prev/siguiente
- Cerrar (X)
- Mantiene URL: `/videos/28/` pero es modal

**JavaScript:** `static/js/item_detail_modal.js`
- Abrir modal desde URL
- Navegación con teclado (flechas, ESC)
- Push state para URL sin recargar

### 5. Breadcrumbs Globales

**Archivo:** `templates/includes/breadcrumbs.html`

Estructura:
- `/projects/2/videos/` → `Proyectos / Proyecto X / Video Generator`
- `/videos/` → `Video Generator`
- `/videos/28/` → `Video Generator / Video 28`
- `/images/2/` → `Biblioteca / Imagen 2`
- `/chat` → `Chat`
- `/biblioteca/` → `Biblioteca`

**No mostrar breadcrumbs en:**
- `/stock/` y rutas relacionadas

---

## 📁 Estructura de Archivos

### Nuevos Templates

```
templates/
├── creation/
│   ├── base_creation.html          # Layout base con sidebars + panel
│   ├── video_creation.html         # Vista de creación de video
│   ├── image_creation.html         # Vista de creación de imagen
│   └── audio_creation.html         # Vista de creación de audio
├── includes/
│   ├── creation_sidebar.html       # Sidebar de creación (dinámico)
│   ├── library_panel.html          # Panel derecho con biblioteca
│   ├── item_detail_modal.html      # Modal de detalle
│   └── breadcrumbs.html            # Breadcrumbs globales
└── projects/
    └── overview.html                # Vista general de proyecto (/projects/2/)
```

### Nuevos Archivos JavaScript

```
static/js/
├── creation_sidebar.js             # Lógica del sidebar de creación
├── model_config.js                 # Configuración de modelos (JSON)
├── item_detail_modal.js            # Lógica del modal de detalle
└── library_panel.js                # Lógica del panel de biblioteca
```

### Nuevos Archivos Python

```
core/
├── ai_services/
│   └── model_config.py             # Configuración centralizada de modelos
├── views/
│   ├── creation_views.py           # Vistas de creación unificadas
│   └── library_views.py            # Vistas de biblioteca
└── utils/
    └── model_capabilities.py       # Utilidades para capacidades de modelos
```

---

## 🔄 Flujo de Implementación

### Fase 1: Configuración de Modelos
1. ✅ Crear `core/ai_services/model_config.py`
2. ✅ Extraer capacidades de cada servicio existente
3. ✅ Crear estructura JSON/JSON para frontend
4. ✅ Endpoint API para obtener configuración de modelos

### Fase 2: Sidebar de Creación
1. ✅ Crear template `creation_sidebar.html`
2. ✅ Implementar dropdown de modelos con búsqueda
3. ✅ Implementar sección REFERENCES dinámica
4. ✅ Implementar sección PROMPT
5. ✅ Implementar sección SETTINGS dinámica
6. ✅ JavaScript para actualización dinámica de campos

### Fase 3: Panel de Biblioteca
1. ✅ Crear template `library_panel.html`
2. ✅ Reutilizar `media_card.html` para grid
3. ✅ Implementar filtrado por tipo/proyecto
4. ✅ Implementar empty state
5. ✅ Click en card → preparar para modal

### Fase 4: Modal de Detalle
1. ✅ Crear template `item_detail_modal.html`
2. ✅ Implementar estructura de dos columnas
3. ✅ Mostrar todos los detalles del item
4. ✅ Implementar navegación prev/siguiente
5. ✅ Integrar con URLs (pushState)

### Fase 5: Breadcrumbs
1. ✅ Crear template `breadcrumbs.html`
2. ✅ Integrar en `base.html`
3. ✅ Actualizar `BreadcrumbMixin` en views
4. ✅ Implementar lógica de breadcrumbs según contexto

### Fase 6: Vistas y URLs
1. ✅ Crear nuevas vistas unificadas
2. ✅ Actualizar `urls.py`
3. ✅ Migrar lógica de formularios existentes
4. ✅ Implementar submit AJAX o tradicional

### Fase 7: Vista General de Proyecto
1. ✅ Crear `projects/overview.html`
2. ✅ Mostrar resumen simple del proyecto
3. ✅ Links a videos/images/audios

### Fase 8: Integración y Testing
1. ✅ Probar creación de video/imagen/audio
2. ✅ Probar modal de detalle
3. ✅ Probar breadcrumbs en todas las rutas
4. ✅ Probar filtrado de biblioteca
5. ✅ Ajustes de UI/UX

---

## 🎨 Detalles de UI/UX

### Sidebar de Creación
- **Ancho:** ~320px fijo
- **Posición:** Izquierda, después del sidebar general
- **Scroll:** Independiente si contenido es largo
- **Tabs:** Image/Video/Audio en la parte superior
- **Secciones:** MODEL, REFERENCES, PROMPT, SETTINGS (en ese orden)

### Panel de Biblioteca
- **Ancho:** Resto del espacio disponible
- **Scroll:** Independiente
- **Grid:** Responsive, mínimo 3 columnas en desktop
- **Cards:** Mismo estilo que `media_card.html`

### Modal de Detalle
- **Tamaño:** ~90% del viewport
- **Centrado:** Vertical y horizontal
- **Overlay:** Fondo oscuro semitransparente
- **Cerrar:** X en esquina superior derecha, ESC para cerrar
- **Navegación:** Flechas izquierda/derecha para navegar items

### Breadcrumbs
- **Posición:** Debajo del header, antes del contenido
- **Estilo:** Links separados por `/`
- **Último item:** No clickeable (texto normal)

---

## 🔧 Consideraciones Técnicas

### Campos Dinámicos
- Los campos del sidebar deben actualizarse en tiempo real al cambiar modelo
- Usar Alpine.js o vanilla JS para reactividad
- Validar campos según modelo antes de submit

### Referencias (Upload vs Biblioteca)
- Opción 1: Upload directo desde dispositivo
- Opción 2: Seleccionar de biblioteca del usuario
- Opción 3: Seleccionar de biblioteca del proyecto (si estamos en proyecto)
- Implementar selector modal para opciones 2 y 3

### Submit del Formulario
- Opción A: Form tradicional (POST, redirect)
- Opción B: AJAX (fetch/HTMX)
- **Recomendación:** Empezar con tradicional, luego migrar a AJAX si necesario

### URLs y PushState
- Modal debe mantener URL sin recargar página
- Usar `history.pushState()` al abrir modal
- Usar `popstate` event para cerrar modal al hacer back

### Filtrado de Biblioteca
- Por ahora: solo por tipo y proyecto
- Futuro: búsqueda, filtros avanzados
- Usar HTMX para filtrado sin recargar

---

## 📝 Checklist de Implementación

### Preparación
- [ ] Revisar todos los servicios AI y sus capacidades
- [ ] Documentar campos soportados por cada modelo
- [ ] Crear logos de servicios (o usar placeholders)

### Desarrollo Backend
- [ ] Crear `model_config.py` con todas las capacidades
- [ ] Crear endpoint API para configuración de modelos
- [ ] Crear nuevas vistas unificadas
- [ ] Actualizar `urls.py`
- [ ] Migrar lógica de formularios

### Desarrollo Frontend
- [ ] Crear template base `base_creation.html`
- [ ] Crear `creation_sidebar.html`
- [ ] Crear `library_panel.html`
- [ ] Crear `item_detail_modal.html`
- [ ] Crear `breadcrumbs.html`
- [ ] Crear JavaScript para sidebar dinámico
- [ ] Crear JavaScript para modal
- [ ] Integrar en templates existentes

### Testing
- [ ] Probar creación de video con cada modelo
- [ ] Probar creación de imagen con cada modelo
- [ ] Probar creación de audio
- [ ] Probar modal de detalle
- [ ] Probar breadcrumbs en todas las rutas
- [ ] Probar filtrado de biblioteca
- [ ] Probar responsive (móvil)

### Ajustes Finales
- [ ] Ajustar estilos según diseño
- [ ] Optimizar rendimiento
- [ ] Revisar accesibilidad
- [ ] Documentar cambios

---

## 🚀 Orden de Implementación Recomendado

1. **Semana 1:** Fase 1 (Configuración de Modelos) + Fase 2 (Sidebar)
2. **Semana 2:** Fase 3 (Panel Biblioteca) + Fase 4 (Modal)
3. **Semana 3:** Fase 5 (Breadcrumbs) + Fase 6 (Vistas/URLs)
4. **Semana 4:** Fase 7 (Vista Proyecto) + Fase 8 (Testing/Ajustes)

---

## ✅ Decisiones Tomadas

1. **Vista general de proyecto:** Resumen simple con estadísticas (X videos, Y imágenes, Z audios), links rápidos a cada sección, y últimos 3-5 items creados
2. **Referencias:** Simple - cuando se hace clic en "Añadir", mostrar opciones: "Biblioteca / Dispositivo"
3. **Submit:** AJAX desde el inicio (mejor UX)
4. **Empty state:** Mensaje simple ("Aún no has creado nada" o similar)
5. **Logos de servicios:** Guardar en `static/images/logos/` (o `static/img/logos/` si prefieres mantener consistencia con `static/img/logo.png` existente)

---

## ⚠️ Riesgos Identificados y Mitigaciones

### 1. Layout con 3 Paneles (Ancho de Pantalla)
**Riesgo:** En pantallas < 1366px puede quedar apretado
**Mitigación:** 
- Sidebar general colapsable (ya existe)
- Considerar hacer sidebar creación colapsable también
- En móvil: ocultar sidebars, mostrar solo panel principal

### 2. Complejidad de Campos Dinámicos
**Riesgo:** Bugs por validación incorrecta, UX confusa
**Mitigación:**
- Empezar con modelos más simples (1-2 modelos por servicio)
- Testing exhaustivo de cada modelo
- Mensajes de error claros
- Documentar bien cada capacidad

### 3. Vista General de Proyecto
**Estado:** ✅ **DEFINIDO**
**Implementación:**
- Resumen simple con:
  - Estadísticas (X videos, Y imágenes, Z audios)
  - Links rápidos a cada sección
  - Últimos 3-5 items creados

### 4. Referencias (Upload vs Biblioteca)
**Estado:** ✅ **DEFINIDO**
**Implementación:**
- Opciones simples "Biblioteca / Dispositivo" al hacer clic en "Añadir"
- Preview de imagen seleccionada siempre visible

### 5. PushState en Modal
**Riesgo:** Problemas con navegación del navegador
**Mitigación:**
- Manejar correctamente `popstate` event
- Fallback si JavaScript falla (degradar a página normal)
- Testing en diferentes navegadores

### 6. Submit Tradicional vs AJAX
**Estado:** ✅ **DECIDIDO - AJAX desde el inicio**
**Implementación:**
- Usar HTMX o fetch para AJAX
- Mostrar loading state durante generación
- Redirigir a detalle cuando termine (o abrir modal)

---

## 💡 Recomendaciones Adicionales

### Fase 0: Definiciones (ANTES de empezar)
1. ✅ **DEFINIDO:** Vista general de proyecto con resumen simple
2. ✅ **DEFINIDO:** Referencias con opciones "Biblioteca / Dispositivo"
3. ✅ **DEFINIDO:** AJAX desde el inicio
4. ✅ **DEFINIDO:** Logos en `static/img/logos/` o `static/images/logos/`

### Implementación Incremental
1. **MVP Primero:** 
   - Un solo tipo (ej: videos) con 2-3 modelos simples
   - Layout básico funcionando
   - Sin modal (usar página normal primero)
2. **Luego Expandir:**
   - Añadir más modelos
   - Añadir modal
   - Añadir imágenes y audios

### Testing Continuo
- Probar cada modelo después de añadirlo
- Probar en diferentes tamaños de pantalla
- Probar navegación (breadcrumbs, URLs, modal)
- Probar con datos reales (no solo empty states)

---

## 📁 Ubicación de Logos/Iconos

**Decisión:** Guardar logos de servicios en `static/img/logos/` (manteniendo consistencia con `static/img/logo.png` existente)

**Estructura:**
```
static/
└── img/
    ├── logo.png          # Logo existente
    └── logos/            # Nuevos logos de servicios
        ├── google.svg
        ├── openai.svg
        ├── higgsfield.svg
        ├── kling.svg
        └── ...
```

**Alternativa:** Si prefieres separar, usar `static/images/logos/` también es válido.

**Nota:** Los logos deben ser SVG preferiblemente (escalables) o PNG de alta resolución. Tamaño recomendado: 24x24px o 32x32px para el dropdown.

---

## 📚 Referencias

- Capturas de Freepik AI Suite (proporcionadas por usuario)
- Captura de modal de detalle (rana)
- Templates actuales: `videos/create.html`, `images/create.html`, `audios/create.html`
- Componentes existentes: `media_card.html`, `project_tabs_bar.html`
- Servicios AI: `core/ai_services/*.py`

