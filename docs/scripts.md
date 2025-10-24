# Script Management Feature

## Descripción General

Este pull request introduce una funcionalidad completa de gestión de guiones con integración de webhook n8n y polling de resultados basado en Redis. Añade modelos, formularios, servicios, vistas y plantillas para crear, procesar y gestionar guiones, mientras elimina archivos de configuración de Tailwind CSS y simplifica la configuración de base de datos a solo SQLite.

## Changes

| Categoría / Archivos | Resumen |
|----------------------|---------|
| **Script Model & Migrations**<br/>`core/migrations/0005_script.py`<br/>`core/migrations/0006_script_desired_duration_min.py`<br/>`core/models.py` | Nuevo modelo Script con ciclo de vida de estados (pending/processing/completed/error), timestamps y campos de metadata; propiedades añadidas a Project para conteo de scripts; introducción de la constante SCRIPT_STATUS; migraciones crean la tabla y añaden el campo desired_duration_min. |
| **Script Forms & Data Handling**<br/>`core/forms.py` | Nuevo ScriptForm con campos title, original_script y desired_duration_min; incluye validación, widgets, labels y textos de ayuda. |
| **Integration Services**<br/>`core/services.py` | Añadido N8nService para comunicación webhook con n8n y RedisService para caché de resultados; importación del modelo Script para referencias de tipo. |
| **Script URL Routing**<br/>`core/urls.py` | Nuevas rutas para operaciones CRUD de scripts (create, detail, delete, retry), partial HTMX de estado, y endpoint webhook de n8n. |
| **Script Views & Webhooks**<br/>`core/views.py` | Cinco nuevas vistas de script (create, detail, delete, retry, status partial) con soporte HTMX; N8nWebhookView para manejo de webhooks; contextos de dashboard y detalle de proyecto extendidos con métricas de scripts; polling de Redis para actualizaciones de estado. |
| **Script Templates**<br/>`templates/partials/script_actions.html`<br/>`templates/partials/script_status.html`<br/>`templates/scripts/create.html`<br/>`templates/scripts/create_modal.html`<br/>`templates/scripts/delete.html`<br/>`templates/scripts/detail.html` | Plantillas de visualización e interacción para scripts; badges de estado, botones de acción, contadores de caracteres, manejo de formularios y UI de expansión de escenas. |
| **Project Detail & Templates**<br/>`templates/projects/detail.html` | Añadida tarjeta de métricas de scripts, sección de scripts con toggle grid/list, botón de crear guión y estado vacío condicional. |
| **Settings & Environment**<br/>`atenea/settings.py`<br/>`env.example` | Base de datos simplificada a solo SQLite; añadida configuración de Redis (REDIS_URL, REDIS_PASSWORD); configuración de logging expandida con handlers de archivo y consola. |
| **Git Configuration**<br/>`.gitignore` | Añadidos patrones de ignore para .cursor y .cursorrules. |
| **Removed Build Configuration**<br/>`theme/static/css/tailwind.css`<br/>`theme/static_src/package.json`<br/>`theme/static_src/tailwind.config.js` | Eliminado pipeline de build de Tailwind CSS, incluyendo estilos compilados, configuración npm y config de Tailwind. |

## Flujo de Procesamiento de Scripts

```mermaid
sequenceDiagram
    actor User
    participant Web as Django Web<br/>(ScriptCreateView)
    participant N8n as n8n Webhook
    participant Redis as Redis
    participant App as Django<br/>(Polling)
    
    User->>Web: Create script + submit
    activate Web
    Web->>Web: Save Script (status=pending)
    Web->>N8n: send_script_for_processing()
    N8n-->>Web: Queued (200)
    Web->>User: Return redirect/response
    deactivate Web
    
    User->>App: Poll script status (every 3s)
    activate App
    App->>Redis: get_script_result(script_id)
    alt Result in Redis
        Redis-->>App: result_data found
        App->>App: process_webhook_response(data)
        App->>App: Update Script (status=completed)
        App->>User: Return updated status partial
    else No result yet
        Redis-->>App: nil
        App->>User: Return "processing..." state
    end
    deactivate App
    
    rect rgb(200, 220, 255)
    Note over N8n,Redis: Async Processing<br/>(Independent)
    N8n->>N8n: Process script
    N8n->>Web: POST /webhook/n8n
    activate Web
    Web->>Web: process_webhook_response(data)
    Web->>Web: Update Script + metadata
    Web->>Redis: set_script_result(script_id, data)
    Web-->>N8n: 200 OK
    deactivate Web
    end
```

## Características Principales

- **Gestión completa de guiones**: CRUD completo para scripts con estados de procesamiento
- **Integración n8n**: Webhook bidireccional para procesamiento asíncrono
- **Redis para caché**: Sistema de polling eficiente para actualizaciones en tiempo real
- **HTMX**: Actualizaciones parciales de UI sin recargar página
- **Validación robusta**: Formularios con validación de campos y límites de caracteres
