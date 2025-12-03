# Arquitectura de Creation Tools - Enfoque Ligero

## 🎯 Principio: Tools como Wrappers Delgados

Los tools de creación son **wrappers delgados** que reutilizan la lógica existente en los servicios. No duplican código, solo exponen los servicios como herramientas para LangChain.

## 📐 Estructura

```
┌─────────────────────────────────────────┐
│         LangChain Agent                  │
│    (CreationAgent con tools)             │
└──────────────┬──────────────────────────┘
               │
               │ Llama tool
               ▼
┌─────────────────────────────────────────┐
│         Tool (Wrapper Delgado)           │
│    - Valida parámetros                   │
│    - Extrae user_id, project_id         │
│    - Maneja proyecto automático          │
│    - Llama al servicio                   │
└──────────────┬──────────────────────────┘
               │
               │ Usa servicio existente
               ▼
┌─────────────────────────────────────────┐
│         Service Layer                    │
│    (ImageService, VideoService, etc.)    │
│    - Crea objeto en BD                  │
│    - Genera contenido                    │
│    - Maneja storage (GCS)                │
│    - Maneja errores                      │
└──────────────┬──────────────────────────┘
               │
               │ Usa cliente de IA
               ▼
┌─────────────────────────────────────────┐
│         AI Service Clients              │
│    (GeminiImageClient, etc.)             │
└─────────────────────────────────────────┘
```

## 🔧 Patrón de Tool

Cada tool sigue este patrón:

```python
@tool
def create_X_tool(
    prompt: str,
    title: Optional[str] = None,
    project_id: Optional[int] = None,
    user_id: int = None  # Requerido, viene del contexto
) -> Dict:
    """
    Descripción clara para el LLM
    """
    # 1. Validaciones básicas
    if not prompt:
        return {'status': 'error', 'message': '...'}
    
    # 2. Obtener usuario
    user = User.objects.get(id=user_id)
    
    # 3. Obtener o crear proyecto
    project = get_or_create_project(project_id, user)
    
    # 4. Llamar al servicio existente
    service = XService()
    obj = service.create_X(...)
    service.generate_X(obj)
    
    # 5. Retornar resultado estructurado
    return {
        'status': 'success',
        'X_id': obj.id,
        'message': '...',
        'detail_url': f'/X/{obj.id}/'
    }
```

## ✅ Ventajas de este Enfoque

1. **Reutilización**: No duplicamos lógica, usamos servicios existentes
2. **Mantenibilidad**: Cambios en servicios se reflejan automáticamente
3. **Consistencia**: Mismo comportamiento que el resto de la app
4. **Ligero**: Tools son pequeños (~100 líneas cada uno)
5. **Escalable**: Fácil agregar nuevos tools siguiendo el patrón

## 📝 Responsabilidades

### Tool (Wrapper)
- ✅ Validar parámetros del LLM
- ✅ Extraer `user_id` del contexto
- ✅ Manejar proyecto automático si no se especifica
- ✅ Convertir errores de servicios a formato para LLM
- ✅ Retornar estructura consistente

### Service (Lógica de Negocio)
- ✅ Crear objeto en BD
- ✅ Generar contenido con APIs externas
- ✅ Manejar storage (GCS)
- ✅ Manejar estados (pending/processing/completed/error)
- ✅ Validaciones de negocio

### AI Service Client
- ✅ Comunicación con APIs externas
- ✅ Manejo de autenticación
- ✅ Parsing de respuestas

## 🔄 Flujo de Datos

```
Usuario: "Crea una imagen de un perro"
    ↓
LLM extrae: prompt="perro", user_id=123
    ↓
create_image_tool(prompt="perro", user_id=123)
    ↓
Tool valida → Obtiene usuario → Crea proyecto automático
    ↓
ImageService.create_image(...)
    ↓
ImageService.generate_image(...)
    ↓
GeminiImageClient.generate_image_from_text(...)
    ↓
Tool retorna: {status: 'success', image_id: 456, ...}
    ↓
LLM formatea respuesta para usuario
```

## 🎨 Ejemplo Real: create_image_tool

```python
@tool
def create_image_tool(
    prompt: str,
    title: Optional[str] = None,
    project_id: Optional[int] = None,
    user_id: int = None
) -> Dict:
    # 1. Validar
    if not prompt:
        return {'status': 'error', 'message': 'Prompt requerido'}
    
    # 2. Obtener usuario
    user = User.objects.get(id=user_id)
    
    # 3. Proyecto automático si no se especifica
    if not project_id:
        project, _ = Project.objects.get_or_create(
            name='Chat Creations',
            owner=user
        )
    
    # 4. Usar servicio existente
    image_service = ImageService()
    image = image_service.create_image(
        title=title or f"Imagen: {prompt[:50]}",
        image_type='text_to_image',
        prompt=prompt,
        config={'aspect_ratio': '16:9'},
        created_by=user,
        project=project
    )
    
    # 5. Generar
    image_service.generate_image(image)
    
    # 6. Retornar
    return {
        'status': 'success',
        'image_id': image.id,
        'message': f'Imagen "{image.title}" creada',
        'detail_url': f'/images/{image.id}/'
    }
```

## 🚀 Próximos Tools

Siguiendo el mismo patrón:

1. `create_video_tool.py` → Usa `VideoService`
2. `create_audio_tool.py` → Usa `AudioService`
3. `create_script_tool.py` → Usa `ScriptAgentService`

Todos siguen el mismo patrón ligero.

