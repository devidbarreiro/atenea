# Plan: Creation Agent - Agente de Creación de Contenido

## 🎯 Objetivo

Crear un chat en la ruta raíz (`/`) donde un agente con acceso a las herramientas de creación de contenido audiovisual pueda:
- Crear videos (Gemini Veo, Sora, HeyGen, Vuela.ai)
- Crear imágenes (Gemini Image, Freepik)
- Crear audios (ElevenLabs TTS)
- Crear guiones (Scripts)
- Renderizar diferentes tipos de contenido en el chat (imágenes, videos, audios, guiones)

## 📋 Análisis de Viabilidad

### ✅ **MUY REALISTA** - Razones:

1. **Infraestructura existente:**
   - ✅ Servicios de creación ya implementados (`VideoService`, `ImageService`, `AudioService`)
   - ✅ Sistema de agentes con tools (`core/agents/tools/`)
   - ✅ Sistema RAG ya funcional (`core/rag/`)
   - ✅ LLM Factory para múltiples proveedores
   - ✅ Sistema de proyectos y permisos

2. **Patrón similar ya implementado:**
   - ✅ Ya existe `DocumentationAssistant` (RAG para docs)
   - ✅ Ya existe `AgentAIAssistant` (para guiones)
   - ✅ Estructura de chat ya probada

3. **Herramientas necesarias:**
   - ✅ Todas las herramientas de creación ya existen como servicios
   - ✅ Solo necesitamos exponerlas como "tools" para LangChain

## 🏗️ Arquitectura Propuesta

### 1. Estructura de Archivos

```
core/
├── agents/
│   ├── creation_agent.py          # Nuevo: Agente principal de creación
│   └── tools/
│       ├── create_video_tool.py   # Nuevo: Tool para crear videos
│       ├── create_image_tool.py   # Nuevo: Tool para crear imágenes
│       ├── create_audio_tool.py   # Nuevo: Tool para crear audios
│       └── create_script_tool.py  # Nuevo: Tool para crear guiones
├── views.py                       # Agregar: CreationAgentView
├── urls.py                        # Agregar: ruta '/'
└── services.py                    # Ya existe (usar servicios existentes)

templates/
└── chat/
    └── creation_agent.html        # Nuevo: Template del chat
```

### 2. Flujo de Funcionamiento

```
Usuario escribe en chat
    ↓
CreationAgent procesa mensaje
    ↓
LLM decide qué tool usar (create_video, create_image, etc.)
    ↓
Tool ejecuta servicio correspondiente
    ↓
Servicio crea objeto (Video/Image/Audio/Script) en BD
    ↓
Servicio inicia generación (asíncrona o síncrona según servicio)
    ↓
Agent retorna respuesta con:
    - Mensaje de confirmación
    - Preview del contenido creado (si está disponible)
    - Link al detalle del contenido
    ↓
Frontend renderiza respuesta según tipo de contenido
```

### 3. Modelo de Datos

**No necesitamos nuevos modelos**, usamos los existentes:
- `Video` (para videos generados)
- `Image` (para imágenes generadas)
- `Audio` (para audios generados)
- `Script` (para guiones generados)
- `Project` (necesitamos un proyecto por defecto o crear uno automático)

**Consideración importante:** 
- ¿Crear contenido en un proyecto específico o crear un proyecto automático "Chat Creations"?
- **Propuesta:** Crear proyecto automático "Chat Creations" si no se especifica uno

### 4. Tools para LangChain

Cada tool será una función decorada con `@tool` que:
1. Recibe parámetros del LLM (extraídos del mensaje del usuario)
2. Valida parámetros
3. Llama al servicio correspondiente
4. Retorna resultado estructurado para el LLM

**Ejemplo de tool:**

```python
@tool
def create_video_tool(
    prompt: str,
    video_type: str = "gemini_veo",  # gemini_veo, sora, heygen
    project_id: int = None,
    duration_sec: int = None,
    orientation: str = "16:9"
) -> Dict:
    """
    Crea un video usando IA generativa.
    
    Args:
        prompt: Descripción del video a crear
        video_type: Tipo de servicio (gemini_veo, sora, heygen_avatar_v2, etc.)
        project_id: ID del proyecto (opcional, se crea uno automático si no se especifica)
        duration_sec: Duración en segundos (opcional, depende del servicio)
        orientation: Orientación del video (16:9 o 9:16)
    
    Returns:
        Dict con 'status', 'video_id', 'message', 'preview_url' (si disponible)
    """
    # Implementación...
```

### 5. Renderizado de Contenido en Chat

El chat debe poder renderizar:

**Imágenes:**
```html
<div class="chat-image">
    <img src="{{ signed_url }}" alt="Imagen generada">
    <a href="{% url 'core:image_detail' image_id %}">Ver detalles</a>
</div>
```

**Videos:**
```html
<div class="chat-video">
    <video controls src="{{ signed_url }}"></video>
    <a href="{% url 'core:video_detail' video_id %}">Ver detalles</a>
</div>
```

**Audios:**
```html
<div class="chat-audio">
    <audio controls src="{{ signed_url }}"></audio>
    <a href="{% url 'core:audio_detail' audio_id %}">Ver detalles</a>
</div>
```

**Guiones:**
```html
<div class="chat-script">
    <div class="script-preview">{{ script.preview }}</div>
    <a href="{% url 'core:script_detail' script_id %}">Ver guión completo</a>
</div>
```

### 6. Gestión de Proyectos

**Opción A: Proyecto automático "Chat Creations"**
- Crear proyecto automático cuando el usuario usa el chat por primera vez
- Todos los contenidos del chat van a este proyecto
- Ventaja: Simple, no requiere selección
- Desventaja: Menos control

**Opción B: Seleccionar proyecto antes de usar**
- Mostrar selector de proyectos al inicio
- Usuario elige dónde crear contenido
- Ventaja: Más control, mejor organización
- Desventaja: Un paso extra

**Opción C: Híbrido (RECOMENDADO)**
- Por defecto: proyecto "Chat Creations"
- Opción de cambiar proyecto en la UI del chat
- Mejor de ambos mundos

### 7. Prompt del Agente

El agente necesita un prompt claro que:
- Explique qué puede hacer (crear videos, imágenes, audios, guiones)
- Liste los servicios disponibles y sus características
- Indique cómo interpretar las solicitudes del usuario
- Proporcione ejemplos de uso

**Ejemplo de prompt:**

```
Eres un asistente especializado en creación de contenido audiovisual con IA.

Puedes crear:
1. VIDEOS:
   - Gemini Veo: Videos realistas 5-8 segundos, sin avatar
   - Sora: Videos creativos 4, 8 o 12 segundos, sin avatar
   - HeyGen: Videos con avatar hablando 30-60 segundos
   - Vuela.ai: Videos con avatar hablando

2. IMÁGENES:
   - Gemini Image: Imágenes desde texto
   - Freepik: Búsqueda de imágenes stock

3. AUDIOS:
   - ElevenLabs TTS: Narración con voces realistas

4. GUIONES:
   - Scripts completos para videos

Cuando el usuario solicite crear contenido:
1. Identifica el tipo de contenido
2. Extrae parámetros del mensaje (prompt, duración, tipo, etc.)
3. Usa la tool correspondiente
4. Informa al usuario del resultado

Si falta información, pregunta al usuario antes de crear.
```

## 🔧 Implementación por Fases

### Fase 1: Estructura Base (MVP)
1. ✅ Crear `CreationAgent` básico
2. ✅ Crear template del chat (`/`)
3. ✅ Implementar 1 tool (ej: `create_image_tool`)
4. ✅ Renderizar imágenes en el chat
5. ✅ Sistema de proyectos automático

### Fase 2: Tools Completas
1. ✅ Implementar todas las tools (video, audio, script)
2. ✅ Mejorar prompt del agente
3. ✅ Manejo de errores robusto
4. ✅ Validación de parámetros

### Fase 3: UX Avanzada
1. ✅ Selector de proyecto en UI
2. ✅ Preview mejorado de contenido
3. ✅ Historial de conversación persistente
4. ✅ Estados de carga para generaciones asíncronas

### Fase 4: Optimizaciones
1. ✅ Caché de respuestas
2. ✅ Streaming de respuestas
3. ✅ Mejoras en renderizado de contenido
4. ✅ Analytics y métricas

## 🎨 Diseño UI/UX

### Layout del Chat

```
┌─────────────────────────────────────────┐
│  [Logo] Chat de Creación con IA        │
│  [Selector de Proyecto] [Config]       │
├─────────────────────────────────────────┤
│                                         │
│  [Mensajes del chat]                    │
│                                         │
│  Usuario: "Crea un video de un perro   │
│           haciendo surf"               │
│                                         │
│  Asistente: [Video preview]            │
│            "He creado el video..."      │
│                                         │
├─────────────────────────────────────────┤
│  [Input de mensaje] [Enviar]            │
└─────────────────────────────────────────┘
```

### Componentes Clave

1. **Chat Container**: Contenedor principal con scroll
2. **Message Bubble**: Burbujas de mensaje (usuario/asistente)
3. **Content Renderer**: Componente que renderiza según tipo (image/video/audio/script)
4. **Project Selector**: Dropdown para cambiar proyecto
5. **Loading States**: Indicadores de carga para generaciones

## 🚨 Consideraciones Importantes

### 1. Generaciones Asíncronas
- Algunos servicios son asíncronos (videos, algunos audios)
- Necesitamos polling o WebSockets para actualizar estado
- **Solución:** Mostrar "Generando..." y hacer polling cada 5s

### 2. Costos de API
- Cada creación consume créditos de APIs externas
- **Solución:** Validar antes de crear, mostrar estimación de costos

### 3. Permisos
- Usuario debe estar autenticado
- Validar permisos del proyecto seleccionado
- **Solución:** Middleware de autenticación, validación en tools

### 4. Límites de Rate
- APIs externas tienen límites de rate
- **Solución:** Rate limiting, cola de procesamiento

### 5. Manejo de Errores
- Errores de API, validación, permisos
- **Solución:** Try-catch en tools, mensajes claros al usuario

## 📊 Métricas de Éxito

1. **Usabilidad:**
   - Tiempo promedio para crear contenido
   - Tasa de éxito de creación
   - Satisfacción del usuario

2. **Técnicas:**
   - Latencia de respuesta del agente
   - Tasa de errores
   - Uso de recursos

3. **Negocio:**
   - Contenido creado por usuario
   - Conversión a proyectos completos
   - Retención de usuarios

## 🔄 Integración con Sistema Existente

### Reutilizar:
- ✅ `VideoService`, `ImageService`, `AudioService`
- ✅ `ProjectService` para gestión de proyectos
- ✅ Sistema de autenticación Django
- ✅ Sistema de storage (GCS)
- ✅ Templates base existentes

### Nuevo:
- ⚠️ `CreationAgent` (nuevo agente)
- ⚠️ Tools de creación (nuevas tools)
- ⚠️ Template del chat (nuevo template)
- ⚠️ Vista del chat (nueva vista)

## 🤔 ¿MCP (Model Context Protocol)?

### Análisis de MCP vs LangChain Tools

**MCP (Model Context Protocol):**
- ✅ Protocolo estándar de Anthropic
- ✅ Permite exponer herramientas a múltiples clientes (Claude Desktop, etc.)
- ✅ Útil si queremos que nuestras herramientas sean accesibles externamente
- ❌ Overkill para un chat interno
- ❌ Requiere servidor MCP adicional
- ❌ Más complejidad sin beneficio claro para nuestro caso

**LangChain Tools (Recomendado):**
- ✅ Ya lo estamos usando (`ScriptAgent` usa LangChain tools)
- ✅ Integración directa con LangChain agents
- ✅ Más simple y directo
- ✅ Suficiente para nuestro chat interno
- ✅ Consistente con el resto de la arquitectura

**Conclusión:** 
- ❌ **NO usar MCP** - Es overkill para un chat interno
- ✅ **Usar LangChain Tools** - Ya lo tenemos, es suficiente y más simple
- 💡 **Futuro:** Si algún día queremos exponer nuestras herramientas externamente, podemos considerar MCP, pero no es necesario ahora

## ✅ Conclusión

**Este feature es MUY REALISTA** porque:
1. La infraestructura ya existe
2. Los servicios ya están implementados
3. Solo necesitamos exponerlos como tools
4. El patrón ya está probado (DocumentationAssistant)

**Tiempo estimado de implementación:**
- Fase 1 (MVP): 2-3 días
- Fase 2 (Completo): 1-2 días adicionales
- Fase 3 (UX): 1-2 días adicionales
- **Total: 4-7 días de desarrollo**

**¿Procedemos con la implementación?**

