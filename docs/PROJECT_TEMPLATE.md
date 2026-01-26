# 👉️ Plantilla de Proyecto - Atenea 🎬

---

## 💫 Información general

**Atenea** es una plataforma centralizada para la generación de contenido de video e imágenes con IA. Integra múltiples servicios de inteligencia artificial como HeyGen, Gemini Veo y OpenAI para crear contenido de forma automatizada y eficiente.

### Contexto
El proyecto surge de la necesidad de unificar múltiples servicios de generación de contenido multimedia con IA en una sola plataforma, simplificando el flujo de trabajo y permitiendo a los usuarios crear videos profesionales con avatares AI, imágenes generadas y más.

### Escala de tiempo sugerida
- **Fase 1**: MVP con integración básica de HeyGen y Gemini Veo
- **Fase 2**: Dashboard completo y gestión de proyectos
- **Fase 3**: Optimización y escalabilidad

> *"La creatividad es la inteligencia divirtiéndose"* — Albert Einstein

---

## 🎯️ Objetivos

| #  | Objetivo | Prioridad |
|----|----------|-----------|
| 1  | Gestión centralizada de proyectos de video | Alta |
| 2  | Integración con múltiples APIs de IA (HeyGen, Gemini Veo, OpenAI) | Alta |
| 3  | Almacenamiento en la nube con Google Cloud Storage | Alta |
| 4  | Dashboard intuitivo y moderno | Media |
| 5  | Tracking completo del proceso de generación | Media |
| 6  | Sistema de colas con Celery para procesamiento asíncrono | Alta |
| 7  | Preview de videos completados | Media |

---

## 🧑💻 Miembros del equipo

| Nombre | Rol | Ubicación | Horario laboral |
|--------|-----|-----------|-----------------|
| David Barreiro | Lead Developer | España | Lun-Vie 9:00-18:00 CET |
|  |  |  |  |
|  |  |  |  |

---

## 🛠️ Resultados del proyecto

| Tarea | Asignado a | Fecha de vencimiento | Estado |
|-------|------------|---------------------|--------|
| Configurar backend Django con arquitectura Service Layer | David | - | ✅ Completado |
| Integrar API de HeyGen para avatares AI | David | - | ✅ Completado |
| Integrar Gemini Veo para generación de video | David | - | ✅ Completado |
| Configurar Google Cloud Storage | David | - | ✅ Completado |
| Implementar sistema de colas con Celery + Redis | David | - | ✅ Completado |
| Crear dashboard con Tailwind + HTMX + Alpine.js | David | - | ✅ Completado |
| Documentación del proyecto | David | - | 📝 En progreso |
| Sistema de RAG y AI Agents | David | - | 📝 En progreso |
| Tests de integración | - | - | ⏳ Tareas pendientes |
| Optimización de rendimiento | - | - | ⏳ Tareas pendientes |
| Deploy a producción | - | - | ⏳ Tareas pendientes |

---

## 🔗 Vínculos relevantes

| Recurso | Enlace | Descripción |
|---------|--------|-------------|
| 📖 Documentación Principal | [docs/README.md](./README.md) | Hub principal de documentación |
| 🎨 Guía Frontend | [docs/frontend/GETTING_STARTED.md](./frontend/GETTING_STARTED.md) | Stack: Tailwind + HTMX + Alpine.js |
| 🔧 Arquitectura Backend | [docs/architecture/](./architecture/) | Django, Service Layer |
| 📋 Guías | [docs/guides/](./guides/) | Tutoriales para tareas específicas |
| 🚀 Getting Started | [docs/getting-started/](./getting-started/) | Cómo empezar con el proyecto |
| 🧹 Celery Cleanup | [docs/guides/celery-cleanup.md](./guides/celery-cleanup.md) | Limpiar colas atascadas |

### APIs y Servicios Externos
- [HeyGen API](https://heygen.com) - Avatares AI
- [Google Gemini/Veo](https://ai.google.dev) - Generación de video con IA
- [OpenAI](https://openai.com) - Modelos de lenguaje
- [Google Cloud Storage](https://cloud.google.com/storage) - Almacenamiento

---

*Última actualización: 19 de enero de 2026*
