# Prompt Templates - Archivos por Defecto

Esta carpeta contiene los templates de prompts que la aplicación ofrece por defecto.

## Estructura

```
prompt_templates/
  default/
    video/
      sora.md
      gemini_veo.md
      higgsfield.md
    image/
      gemini_image.md
    agent/
      general.md
```

## Formato de los Archivos

Cada archivo Markdown contiene un template con frontmatter YAML:

```markdown
---
name: Nombre del Template
description: Descripción del template
recommended_service: sora|gemini_veo|higgsfield|agent
is_public: true
---

Texto del prompt aquí (máx 800 caracteres).
Puede tener múltiples líneas.
```

## Campos Requeridos

- `name`: Nombre del template (único por servicio)
- `prompt_text`: Texto del prompt (máximo 800 caracteres)
- `recommended_service`: Servicio recomendado
- `is_public`: Si es público (default: true para templates por defecto)

## Campos Opcionales

- `description`: Descripción del template
- `preview_url`: URL del preview (se puede añadir después)

## Cargar Templates

Los templates se cargan automáticamente al ejecutar:

```bash
python manage.py load_default_prompt_templates
```

Este comando:
1. Lee todos los archivos JSON de `default/`
2. Crea los templates en la base de datos
3. Si ya existen (por nombre y servicio), los actualiza
4. Los marca como públicos

## Añadir Nuevos Templates

1. Edita o crea el archivo JSON correspondiente
2. Ejecuta el comando de carga
3. Los templates estarán disponibles en la aplicación

## Notas

- Los templates por defecto se crean con `created_by` = usuario del sistema (o None)
- Se pueden añadir múltiples templates por archivo
- El formato es fácil de mantener y versionar en git

