# N8N Prompt Actualizado - Generación de Escenas con Script y Visual Prompt

## Objetivo
Genera un conjunto de escenas para un video educativo o promocional, separando claramente el **guión narrativo** (script_text) del **prompt visual cinematográfico** (visual_prompt).

## Estructura de Salida JSON

```json
{
  "script_id": [ID del script],
  "scenes": [
    {
      "scene_id": "Escena X",
      "summary": "Resumen breve de la escena",
      "script_text": "Texto narrativo que se leerá con ElevenLabs TTS o voz de avatar HeyGen",
      "visual_prompt": "Descripción visual cinematográfica en INGLÉS para generación de video",
      "broll": ["elemento1", "elemento2", "elemento3"],
      "ai_service": "gemini_veo|sora|heygen_v2|heygen_avatar_iv|vuela_ai",
      "duration_sec": 8,
      "ai_config": {
        // Configuración específica según el servicio
      }
    }
  ]
}
```

## Campos Principales

### 1. `script_text` (GUIÓN NARRATIVO)
- **Idioma**: Español (o idioma del video)
- **Propósito**: Texto que será narrado por:
  - ElevenLabs TTS para Veo/Sora/Vuela
  - Voz del avatar en HeyGen
- **Características**:
  - Natural y conversacional
  - Claro y directo
  - Apropiado para ser leído en voz alta
  - Máximo 1000 caracteres (límite técnico de Sora/Veo)
- **Ejemplo**:
  ```
  "Bienvenidos a nuestro video sobre inteligencia artificial. Hoy exploraremos cómo la IA está transformando el mundo moderno en áreas como medicina, educación y transporte."
  ```

### 2. `visual_prompt` (DESCRIPCIÓN VISUAL)
- **Idioma**: INGLÉS (requerido para mejores resultados en Veo/Sora)
- **Propósito**: Descripción detallada para generación del video
- **Características**:
  - Descriptivo y cinematográfico
  - Incluye elementos visuales específicos
  - Estilo fotográfico/artístico
  - Iluminación, composición, atmósfera
  - Combina elementos de `broll` con creatividad
  - Máximo 2000 caracteres
- **NO aplica a**: HeyGen (usa avatar + background config)
- **Ejemplo**:
  ```
  "Modern tech office with large screens displaying colorful AI visualizations, natural lighting through floor-to-ceiling windows, diverse team collaborating around holographic displays, professional and innovative atmosphere, cinematic 4K quality, wide shot with shallow depth of field"
  ```

### 3. `broll` (ELEMENTOS VISUALES)
- **Propósito**: Lista de elementos visuales clave para la escena
- **Uso**: El sistema combina estos elementos al generar `visual_prompt`
- **Ejemplo**: `["tech office", "AI screens", "modern workspace", "natural lighting"]`

## Reglas de Generación

### Para Escenas de Veo/Sora (Videos cinematográficos)
```json
{
  "scene_id": "Escena 1",
  "summary": "Introducción visual impactante",
  "script_text": "El futuro de la tecnología está aquí, transformando cada aspecto de nuestras vidas.",
  "visual_prompt": "Stunning futuristic cityscape at golden hour with flying vehicles and holographic billboards, busy streets with people using AR glasses, sleek modern architecture, warm sunset lighting creating dramatic shadows, cinematic wide shot in 4K resolution",
  "broll": ["futuristic city", "holographic displays", "AR technology", "sunset"],
  "ai_service": "gemini_veo",
  "duration_sec": 8
}
```

### Para Escenas de HeyGen (Avatar hablando)
```json
{
  "scene_id": "Escena 2",
  "summary": "Experto explicando conceptos",
  "script_text": "Las redes neuronales artificiales imitan el funcionamiento del cerebro humano, permitiendo a las máquinas aprender patrones complejos.",
  "visual_prompt": "Professional female presenter in business casual attire standing in modern tech studio with soft key lighting, clean minimalist background with subtle tech-themed elements, confident and engaging posture, looking directly at camera",
  "broll": [],
  "ai_service": "heygen_v2",
  "ai_config": {
    "avatar_id": "Anna_public_3_20240108",
    "voice_id": "2b568345afd74c8baed88c640c0758d1"
  }
}
```

### Para Escenas de Vuela.ai (Animación con voz)
```json
{
  "scene_id": "Escena 3",
  "summary": "Visualización de datos",
  "script_text": "Los datos fluyen constantemente, creando patrones que las máquinas pueden reconocer y aprender.",
  "visual_prompt": "Abstract data visualization with flowing particles forming neural network patterns, blue and purple color scheme with glowing connections, smooth camera movement through 3D space, elegant and technical aesthetic",
  "broll": ["data visualization", "neural networks", "particle effects"],
  "ai_service": "vuela_ai",
  "ai_config": {
    "voice_id": "VUELA_VOICE_ID"
  }
}
```

## Mejores Prácticas

### Script Text (Guión)
1. **Longitud apropiada**: 50-200 palabras por escena de 8 segundos
2. **Ritmo natural**: 150-180 palabras por minuto
3. **Puntuación clara**: Facilita la entonación correcta del TTS
4. **Contexto completo**: Cada script_text debe tener sentido por sí solo

### Visual Prompt (Descripción Visual)
1. **Especificidad**: Cuanto más detallado, mejores resultados
2. **Términos cinematográficos**: 
   - "wide shot", "close-up", "aerial view"
   - "shallow depth of field", "bokeh background"
   - "golden hour lighting", "dramatic shadows"
   - "4K quality", "cinematic composition"
3. **Atmósfera**: Incluye emociones y sensaciones visuales
4. **Colores y tonos**: Especifica paletas de color cuando sea relevante
5. **Movimiento**: Describe cámara y acción si es importante

## Servicios de IA Disponibles

1. **gemini_veo**: Videos realistas de alta calidad (5s o 8s)
2. **sora**: Videos cinematográficos de OpenAI (4s, 8s o 12s)
3. **heygen_v2**: Avatar realista V2 (requiere avatar_id y voice_id)
4. **heygen_avatar_iv**: Avatar IV de HeyGen (requiere avatar_id y voice_id)
5. **vuela_ai**: Animación con voz integrada (requiere voice_id)

## Flujo de Procesamiento

1. **n8n recibe el contenido** del usuario
2. **Genera las escenas** con:
   - `script_text`: Narrativa en español
   - `visual_prompt`: Descripción visual en inglés
   - `broll`: Elementos visuales clave
3. **Sistema Atenea**:
   - Usa `visual_prompt` para generar video (Veo/Sora/Vuela)
   - Usa `script_text` para generar audio (ElevenLabs)
   - Combina video + audio automáticamente
   - Para HeyGen: usa `script_text` para la voz del avatar

## Ejemplo Completo de Escena

```json
{
  "scene_id": "Escena 5",
  "summary": "Revolución de la inteligencia artificial",
  "script_text": "Estamos presenciando una revolución tecnológica sin precedentes. La inteligencia artificial ya no es ciencia ficción, sino una realidad que mejora nuestras vidas cada día.",
  "visual_prompt": "Dynamic montage of AI applications in real world: doctor analyzing medical scans with AI assistance, students learning with adaptive educational software, autonomous vehicles navigating busy city streets, all connected by flowing data streams, bright optimistic color grading, energetic pace with smooth transitions, professional documentary style in 4K",
  "broll": [
    "AI in healthcare",
    "educational technology",
    "autonomous vehicles",
    "data connections"
  ],
  "ai_service": "sora",
  "duration_sec": 12,
  "ai_config": {
    "duration": 12,
    "sora_model": "sora-2",
    "size": "1280x720"
  }
}
```

## Notas Importantes

- **Separación clara**: script_text es SOLO para audio, visual_prompt es SOLO para video
- **Coherencia**: Ambos campos deben complementarse pero son independientes
- **Idiomas**: script_text en español, visual_prompt en inglés para mejores resultados
- **Creatividad**: visual_prompt puede ser más creativo y cinematográfico que script_text
- **HeyGen**: Para avatares, visual_prompt describe el ambiente/fondo, no el avatar mismo

---

**Recuerda**: El objetivo es producir videos profesionales donde la narración y las imágenes se complementen perfectamente, creando una experiencia audiovisual coherente y atractiva.

