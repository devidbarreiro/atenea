# 🚀 PLAN DE EJECUCIÓN: Nueva UI de Creación

## 📋 Resumen Ejecutivo

Este documento detalla el plan paso a paso para implementar la nueva UI de creación de items (video, imagen, audio) con layout estilo Freepik AI Suite.

**Objetivo:** Rediseñar completamente las plantillas de creación con sidebar dinámico + panel de biblioteca.

---

## 🎯 Orden de Implementación

### **FASE 1: Configuración de Modelos (Backend)** ✅ COMPLETADA
**Objetivo:** Centralizar todas las capacidades de modelos en un sistema único

#### Paso 1.1: Crear `core/ai_services/model_config.py`
- [x] Crear archivo con estructura `MODEL_CAPABILITIES`
- [x] Extraer capacidades de cada servicio existente
- [x] Definir estructura de capacidades

#### Paso 1.2: Crear endpoint API para configuración
- [x] Crear vista `ModelConfigAPIView` en `core/views.py`
- [x] Endpoint: `/api/models/config/`
- [x] Retornar JSON con todas las capacidades
- [x] Filtrar por tipo si se pasa parámetro `?type=video`

#### Paso 1.3: Crear utilidades para capacidades
- [x] Crear `core/utils/model_capabilities.py`
- [x] Función `get_models_by_type(type: str) -> List[Dict]`
- [x] Función `get_model_capabilities(model_id: str) -> Dict`
- [x] Función `get_supported_fields(model_id: str) -> List[str]`

**Tiempo estimado:** 2-3 horas ✅

---

### **FASE 2: Estructura Base de Templates** ✅ COMPLETADA
**Objetivo:** Crear el layout base con sidebars + panel

#### Paso 2.1: Crear `templates/creation/base_creation.html`
- [x] Layout con 3 columnas
- [x] Estructura HTML básica
- [x] Estilos base con Tailwind

#### Paso 2.2: Crear `templates/includes/creation_sidebar.html`
- [x] Estructura básica del sidebar
- [x] Tabs Image/Video/Audio en la parte superior
- [x] Secciones: MODEL, REFERENCES, PROMPT, SETTINGS

#### Paso 2.3: Crear `templates/includes/library_panel.html`
- [x] Grid básico para cards
- [x] Empty state placeholder
- [x] Scroll independiente

**Tiempo estimado:** 1-2 horas ✅

---

### **FASE 3: Sidebar de Creación - MODEL Dropdown** ✅ COMPLETADA
**Objetivo:** Implementar dropdown de modelos con búsqueda y logos

#### Paso 3.1: Crear componente dropdown de modelos
- [x] HTML del dropdown con Alpine.js
- [x] Búsqueda/filtro de modelos
- [x] Mostrar logos de servicios
- [x] Mostrar información de cada modelo
- [x] Agrupar por servicio

#### Paso 3.2: Cargar configuración de modelos
- [x] JavaScript para cargar desde `/api/models/config/`
- [x] Filtrar modelos según tab activo
- [x] Almacenar en estado Alpine.js

#### Paso 3.3: Selección de modelo
- [x] Al seleccionar modelo, actualizar estado
- [x] Preparar para actualizar campos dinámicos

**Tiempo estimado:** 2-3 horas ✅

---

### **FASE 4: Sidebar de Creación - Campos Dinámicos** ✅ COMPLETADA
**Objetivo:** Implementar campos que cambian según modelo seleccionado

#### Paso 4.1: Sección REFERENCES
- [x] Detectar si modelo soporta referencias
- [x] Mostrar campos según capacidades del modelo
- [x] Botón "Añadir" con opciones "Biblioteca / Dispositivo"
- [x] Preview de imagen seleccionada
- [x] Upload directo desde dispositivo

#### Paso 4.2: Sección PROMPT
- [x] Textarea para prompt de texto
- [x] Validación de campo requerido

#### Paso 4.3: Sección SETTINGS
- [x] Duration: mostrar si modelo permite opciones
- [x] Aspect Ratio: mostrar si modelo permite opciones
- [x] Resolution: mostrar si modelo permite opciones
- [x] Audio toggle: mostrar si modelo soporta audio
- [x] Negative Prompt: mostrar si modelo lo soporta
- [x] Seed: mostrar si modelo lo soporta

#### Paso 4.4: JavaScript para actualización dinámica
- [x] Función `updateFieldsForModel(modelId)`
- [x] Ocultar/mostrar campos según capacidades
- [x] Resetear valores al cambiar modelo

**Tiempo estimado:** 4-5 horas ✅

---

### **FASE 5: Panel de Biblioteca** ✅ COMPLETADA
**Objetivo:** Mostrar grid de items con filtrado

#### Paso 5.1: Cargar items en el panel
- [x] Endpoint API `/api/library/items/`
- [x] Filtrar por tipo (video/image/audio)
- [x] Filtrar por proyecto si estamos en proyecto

#### Paso 5.2: Grid de cards
- [x] Grid responsive
- [x] Click en card → preparar para modal

#### Paso 5.3: Empty state
- [x] Mensaje cuando no hay items
- [x] Diseño simple y claro

**Tiempo estimado:** 2-3 horas ✅

---

### **FASE 6: Modal de Detalle** ✅ COMPLETADA
**Objetivo:** Modal fullscreen para ver detalles de items

#### Paso 6.1: Crear `templates/includes/item_detail_modal.html`
- [x] Estructura de dos columnas
- [x] Overlay oscuro semitransparente
- [x] Botón cerrar (X)
- [x] Navegación prev/siguiente (flechas)

#### Paso 6.2: Panel de detalles
- [x] PROMPT: mostrar prompt usado
- [x] SETTINGS: mostrar configuración
- [x] Acciones: Generar, Eliminar

#### Paso 6.3: JavaScript para modal
- [x] Abrir modal desde URL (`/videos/28/`)
- [x] Push state al abrir modal
- [x] Manejar `popstate` para cerrar al hacer back
- [x] Navegación con teclado (flechas, ESC)
- [x] Cargar datos del item vía AJAX

**Tiempo estimado:** 3-4 horas ✅

---

### **FASE 7: Breadcrumbs Globales** ✅ COMPLETADA
**Objetivo:** Implementar breadcrumbs en toda la aplicación

#### Paso 7.1: Crear `templates/includes/breadcrumbs.html`
- [x] Estructura HTML básica
- [x] Links separados por `/`
- [x] Último item no clickeable

#### Paso 7.2: Actualizar `BreadcrumbMixin`
- [x] Revisar implementación actual
- [x] Asegurar que todas las vistas lo usan
- [x] Actualizar breadcrumbs según nuevas URLs

#### Paso 7.3: Integrar en `base.html`
- [x] Incluir breadcrumbs después del header
- [x] Condicionar mostrar según ruta

#### Paso 7.4: Actualizar breadcrumbs en todas las vistas
- [x] Crear vistas: `Proyectos / Proyecto X / Video Generator`
- [x] Standalone: `Video Generator`
- [x] Detalle: `Video Generator / Video 28`

**Tiempo estimado:** 2 horas ✅

---

### **FASE 8: Vistas y URLs** ✅ COMPLETADA
**Objetivo:** Crear nuevas vistas unificadas y actualizar URLs

#### Paso 8.1: Crear nuevas vistas de creación
- [x] `VideoLibraryView` - unifica creación + biblioteca
- [x] `ImageLibraryView` - unifica creación + biblioteca
- [x] `AudioLibraryView` - unifica creación + biblioteca
- [x] Usar nuevo template `base_creation.html`

#### Paso 8.2: Actualizar `core/urls.py`
- [x] Eliminar rutas `/create` para videos, imágenes, audios
- [x] Nuevas rutas:
  - `/videos/` → VideoLibraryView
  - `/images/` → ImageLibraryView
  - `/audios/` → AudioLibraryView
  - `/projects/<id>/videos/` → VideoLibraryView (con proyecto)
  - `/projects/<id>/images/` → ImageLibraryView (con proyecto)
  - `/projects/<id>/audios/` → AudioLibraryView (con proyecto)
- [x] Mantener rutas de detalle: `/videos/<id>/`, `/images/<id>/`, etc.

#### Paso 8.3: Migrar lógica de formularios
- [x] Extraer lógica de formularios existentes
- [x] Adaptar a nuevo sistema dinámico
- [x] Validación según modelo seleccionado

#### Paso 8.4: Implementar submit AJAX
- [x] Usar fetch para submit
- [x] Mostrar loading state
- [x] Manejar errores
- [x] Recargar biblioteca al completar

**Tiempo estimado:** 4-5 horas ✅

---

### **FASE 9: Vista General de Proyecto** ✅ COMPLETADA
**Objetivo:** Crear vista simple para `/projects/<id>/`

#### Paso 9.1: Crear `templates/projects/overview.html`
- [x] Layout simple
- [x] Estadísticas: X videos, Y imágenes, Z audios
- [x] Links rápidos a cada sección
- [x] Últimos 3-5 items creados

#### Paso 9.2: Crear vista `ProjectOverviewView`
- [x] Obtener estadísticas del proyecto
- [x] Obtener últimos items
- [x] Renderizar template

#### Paso 9.3: Actualizar URL
- [x] `/projects/<id>/` → ProjectOverviewView
- [x] Mantener `/projects/<id>/videos/` para creación

**Tiempo estimado:** 1-2 horas ✅

---

### **FASE 10: Integración y Testing** 🔄 EN PROGRESO
**Objetivo:** Probar todo el flujo y ajustar

#### Paso 10.1: Testing de creación
- [ ] Probar creación de video con cada modelo
- [ ] Probar creación de imagen con cada modelo
- [ ] Probar creación de audio
- [ ] Verificar campos dinámicos funcionan correctamente
- [ ] Verificar validación según modelo

#### Paso 10.2: Testing de biblioteca
- [ ] Verificar grid muestra items correctamente
- [ ] Verificar filtrado por tipo/proyecto
- [ ] Verificar empty state

#### Paso 10.3: Testing de modal
- [ ] Verificar modal se abre desde URL
- [ ] Verificar navegación prev/siguiente
- [ ] Verificar pushState funciona
- [ ] Verificar cerrar con ESC/back

#### Paso 10.4: Testing de breadcrumbs
- [ ] Verificar breadcrumbs en todas las rutas
- [ ] Verificar no aparecen en `/stock/`
- [ ] Verificar estructura correcta

#### Paso 10.5: Testing responsive
- [ ] Probar en diferentes tamaños de pantalla
- [ ] Verificar sidebars se comportan bien
- [ ] Verificar modal en móvil

#### Paso 10.6: Ajustes finales
- [ ] Ajustar estilos según diseño
- [ ] Optimizar rendimiento
- [ ] Revisar accesibilidad
- [ ] Documentar cambios

**Tiempo estimado:** 3-4 horas

---

## 📊 Resumen de Tiempos

| Fase | Estado | Tiempo Estimado | Tiempo Real |
|------|--------|----------------|-------------|
| Fase 1: Configuración de Modelos | ✅ | 2-3 horas | ~3 horas |
| Fase 2: Estructura Base Templates | ✅ | 1-2 horas | ~2 horas |
| Fase 3: MODEL Dropdown | ✅ | 2-3 horas | ~3 horas |
| Fase 4: Campos Dinámicos | ✅ | 4-5 horas | ~5 horas |
| Fase 5: Panel Biblioteca | ✅ | 2-3 horas | ~2 horas |
| Fase 6: Modal Detalle | ✅ | 3-4 horas | ~4 horas |
| Fase 7: Breadcrumbs | ✅ | 2 horas | ~2 horas |
| Fase 8: Vistas y URLs | ✅ | 4-5 horas | ~5 horas |
| Fase 9: Vista Proyecto | ✅ | 1-2 horas | ~1 hora |
| Fase 10: Testing | 🔄 | 3-4 horas | - |
| **TOTAL** | **9/10** | **24-33 horas** | **~27 horas** |

---

## ✅ Checklist de Completado

- [x] Fase 1: Configuración de Modelos
- [x] Fase 2: Estructura Base Templates
- [x] Fase 3: MODEL Dropdown
- [x] Fase 4: Campos Dinámicos
- [x] Fase 5: Panel Biblioteca
- [x] Fase 6: Modal Detalle
- [x] Fase 7: Breadcrumbs
- [x] Fase 8: Vistas y URLs
- [x] Fase 9: Vista Proyecto
- [ ] Fase 10: Testing y Ajustes Finales

---

## 🚨 Problemas Resueltos

1. ✅ Error `AttributeError: 'Project' object has no attribute 'music'` - Corregido usando `music_tracks`
2. ✅ Rutas `/create` eliminadas según plan
3. ✅ Errores JavaScript de null en modal corregidos
4. ✅ Referencias a rutas legacy actualizadas

---

## 📝 Notas de Implementación

- ✅ Usar Alpine.js para reactividad en sidebar
- ✅ Usar fetch para AJAX
- ✅ Mantener compatibilidad con código existente durante transición
- ✅ Commits pequeños y frecuentes

---

## 🎯 Próximos Pasos

1. **Testing completo** de todas las funcionalidades
2. **Ajustes de UI/UX** según feedback
3. **Optimización** de rendimiento
4. **Documentación** de cambios

---

¿Continuamos con la Fase 10 (Testing)? 🚀
