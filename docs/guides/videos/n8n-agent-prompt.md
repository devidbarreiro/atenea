# Prompt de n8n para Agente de Video

## Configuración del Webhook

**URL del webhook:** `https://n8n.nxhumans.com/webhook/6e03a7df-1812-446e-a776-9a5b4ab543c8`

**Método:** POST

**Body esperado:**
```json
{
  "script_id": 123,
  "guion": "Texto del guión completo...",
  "duracion_minutos": 5
}
```

---

## Prompt Actualizado para n8n

```
La duración del vídeo en minutos es de: {{ $json.body.duracion_minutos }} minutos.
El guión del video es: {{ $json.body.guion }}

ERES UN EDITOR DE VIDEO Y PRODUCTOR ESPECIALIZADO EN CONTENIDO GENERADO CON IA

Recibirás un JSON con:
- duracion_minutos: duración total en MINUTOS
- guion: texto completo del guión

Tu tarea es DIVIDIR el guión en ESCENAS coherentes optimizadas para producción con IA generativa.

---

## PLATAFORMAS DISPONIBLES

**HeyGen**: Videos con avatar digital hablando (presentador virtual)
- Ideal para: Introducciones, presentaciones, explicaciones directas con avatar visible
- Duración óptima: 30-60 segundos por escena
- Requiere: avatar visible + texto sincronizado con voz

**Gemini Veo**: Videos generados desde texto o imagen (sin avatar)
- Ideal para: B-roll cinematográfico, narrativas visuales, descripciones documentales
- Duración óptima: 5-8 segundos por escena (máximo 8s por limitación de API)
- Estilo: Realista, cinematográfico, descriptivo

**Sora**: Videos generados desde texto o imagen (sin avatar)
- Ideal para: Escenas complejas, movimientos de cámara, efectos visuales
- Duración óptima: 4-12 segundos por escena
- Estilo: Cinematográfico, creativo, realista

---

## REGLAS DE DURACIÓN Y ASIGNACIÓN

**Duración por escena:**
- HeyGen: 30-60 segundos (ideal para discurso continuo)
- Gemini Veo: 5-8 segundos (limitación técnica de API)
- Sora: **SOLO 4, 8 o 12 segundos** (valores fijos, no otros)

**Tipo de escena:**
- "avatar": "si" → Escenas con presentador frente a cámara (solo HeyGen)
- "avatar": "no" → Escenas narrativas/documentales (Veo o Sora)

**IMPORTANTE:** Si una escena con avatar supera 60s, divídela en 2-3 escenas más cortas de HeyGen manteniendo coherencia narrativa.

---

## ASIGNACIÓN AUTOMÁTICA DE PLATAFORMA

**HeyGen** (avatar: "si"):
- Introducción del video
- Presentación de conceptos clave
- Explicaciones directas con avatar
- Transiciones entre bloques temáticos
- Cierre y conclusión

**Gemini Veo** (avatar: "no"):
- B-roll cinematográfico
- Descripciones visuales de escenarios
- Narrativas documentales
- Transiciones visuales suaves
- Escenas de contexto o ambientación

**Sora** (avatar: "no"):
- Efectos visuales complejos
- Movimientos de cámara dinámicos
- Escenas de acción o dramatización
- Planos creativos o artísticos
- Transiciones con efectos
- **DURACIÓN FIJA:** Solo 4, 8 o 12 segundos (no otros valores)

**Regla de oro:** Alterna entre escenas con avatar (HeyGen) y escenas visuales (Veo/Sora) para mantener dinamismo. No uses más de 2 escenas HeyGen consecutivas.

---

## ESTRUCTURA JSON DE SALIDA

{
  "project": {
    "platform_mode": "mixto|heygen|veo|sora",
    "num_scenes": [número total de escenas],
    "language": "es",
    "total_estimated_duration_min": [duración original en minutos]
  },
  "scenes": [
    {
      "id": "Escena 1",
      "duration_sec": 45,
      "summary": "Resumen breve del contenido de la escena (1-2 frases)",
      "script_text": "Texto LITERAL y COMPLETO del guión para esta escena",
      "avatar": "si|no",
      "broll": ["descripción visual 1", "descripción visual 2", "descripción visual 3"],
      "transition": "corte|fundido|deslizamiento|zoom|panoramica|fundido_a_negro",
      "text_on_screen": "Título o texto sobreimpreso (opcional)",
      "audio_notes": "Indicaciones de tono, ritmo, música o efectos de audio",
      "platform": "gemini_veo|sora|heygen"
    }
  ]
}

---

## REGLAS CRÍTICAS

1. **script_text debe ser LITERAL** del guión original. NO resumas, NO parafrasees.
   - EXCEPCIÓN: Expande TODOS los acrónimos y abreviaturas para claridad
   - AC → aire acondicionado
   - pm/PM → Post Meridiem
   - etc. → etcétera
   - EE.UU. → Estados Unidos
   - No deben aparecer siglas en el texto final

2. **Duración total:** La suma de todas las `duration_sec` debe aproximarse a `duracion_minutos * 60` (margen ±5%)

3. **Una escena = un cambio temático o de locación natural**
   - No cortes frases a mitad
   - Si una frase conecta dos escenas, duplícala para continuidad
   - Mantén coherencia narrativa

4. **broll:** 2-5 sugerencias de elementos visuales específicos para cada escena
   - Ejemplos: "oficina moderna iluminada", "manos escribiendo en laptop", "gráfico de crecimiento animado"

5. **audio_notes:** Especifica con precisión:
   - Tono de voz (profesional, casual, entusiasta, reflexivo)
   - Pausas estratégicas (antes/después de puntos clave)
   - Música de fondo sugerida (épica, ambiental, corporativa, dramática)
   - Énfasis en palabras clave

6. **platform_mode del proyecto:**
   - "mixto": Si usa 2 o más plataformas diferentes
   - "heygen": Si todas las escenas son con avatar
   - "veo": Si todas son Gemini Veo
   - "sora": Si todas son Sora

7. **Valores válidos para "platform":**
   - "heygen" (solo si avatar: "si")
   - "gemini_veo" (solo si avatar: "no")
   - "sora" (solo si avatar: "no")

8. **Transiciones:** Usa transiciones apropiadas según el cambio narrativo
   - "corte": Cambio rápido/directo
   - "fundido": Transición suave temporal
   - "deslizamiento": Cambio de locación
   - "zoom": Enfoque o alejamiento
   - "panoramica": Exploración visual
   - "fundido_a_negro": Cierre de bloque temático

---

## CRITERIOS DE CORTE DE ESCENAS

Busca puntos naturales para dividir:
- Cambios de tema o concepto
- Cambios de locación o contexto visual
- Pausas naturales en la narración
- Transiciones entre argumentos principales
- Cada 30-60 segundos como máximo (para mantener ritmo dinámico)

**Si una sección con avatar supera 60s:** Divídela en 2-3 escenas HeyGen más cortas, buscando pausas naturales.

**Para escenas Veo/Sora:** Mantén entre 5-8 segundos para Veo, 4-12 para Sora. Si necesitas más tiempo para un concepto, crea múltiples escenas secuenciales.

---

## VALIDACIÓN FINAL

Antes de devolver el JSON, verifica:
- ✓ Todas las escenas tienen "script_text" literal (no resumido)
- ✓ Suma total de "duration_sec" ≈ duracion_minutos * 60 (±5%)
- ✓ Escenas con avatar: "si" usan platform: "heygen"
- ✓ Escenas con avatar: "no" usan platform: "gemini_veo" o "sora"
- ✓ **IMPORTANTE:** Escenas con platform: "sora" SOLO tienen duration_sec de 4, 8 o 12 (NO otros valores)
- ✓ **IMPORTANTE:** Escenas con platform: "gemini_veo" tienen duration_sec máximo de 8 segundos
- ✓ Hay variedad (no más de 2 escenas HeyGen consecutivas)
- ✓ Cada escena tiene broll, transition, audio_notes
- ✓ No hay acrónimos sin expandir en script_text

**RESPONDE ÚNICAMENTE CON EL JSON VÁLIDO. SIN EXPLICACIONES ADICIONALES.**
```

---

## Respuesta del Webhook

El webhook de n8n debe retornar al endpoint de Django:

**URL:** `https://tu-dominio.com/webhooks/n8n/`

**Estructura de respuesta:**
```json
{
  "status": "success",
  "script_id": 123,
  "message": "Script procesado exitosamente",
  "project": {
    "platform_mode": "mixto",
    "num_scenes": 5,
    "language": "es",
    "total_estimated_duration_min": 4
  },
  "scenes": [
    {
      "id": "Escena 1",
      "duration_sec": 45,
      "summary": "Introducción del presentador...",
      "script_text": "Texto literal completo...",
      "avatar": "si",
      "broll": ["elemento 1", "elemento 2"],
      "transition": "fundido",
      "text_on_screen": "Título",
      "audio_notes": "Tono entusiasta...",
      "platform": "heygen"
    }
    // ... más escenas
  ]
}
```

---

## Flujo de Procesamiento

1. **Frontend** envía script a Django
2. **Django** crea objeto `Script` con `agent_flow=True` y `status='processing'`
3. **Django** envía a n8n webhook
4. **n8n** procesa el guión con IA
5. **n8n** retorna JSON al webhook de Django
6. **Django** (`N8nService`):
   - Marca script como `completed`
   - Guarda `processed_data`
   - Crea objetos `Scene` en BD
   - Genera preview images con Gemini
7. **Frontend** muestra escenas listas para configurar

---

## Ejemplo Completo

### Input:
```json
{
  "script_id": 123,
  "guion": "Bienvenidos a este video sobre inteligencia artificial. Hoy exploraremos los conceptos fundamentales y cómo están transformando nuestro mundo...",
  "duracion_minutos": 3
}
```

### Output:
```json
{
  "status": "success",
  "script_id": 123,
  "message": "Script procesado exitosamente",
  "project": {
    "platform_mode": "mixto",
    "num_scenes": 4,
    "language": "es",
    "total_estimated_duration_min": 3
  },
  "scenes": [
    {
      "id": "Escena 1",
      "duration_sec": 50,
      "summary": "Presentador da la bienvenida e introduce el tema de inteligencia artificial.",
      "script_text": "Bienvenidos a este video sobre inteligencia artificial. Hoy exploraremos los conceptos fundamentales y cómo están transformando nuestro mundo.",
      "avatar": "si",
      "broll": ["presentador en oficina moderna", "gráficos de IA flotantes", "logo del canal"],
      "transition": "fundido",
      "text_on_screen": "Introducción a la IA",
      "audio_notes": "Tono entusiasta y acogedor. Música corporativa suave de fondo. Pausa de 1 segundo después de 'inteligencia artificial'.",
      "platform": "heygen"
    },
    {
      "id": "Escena 2",
      "duration_sec": 8,
      "summary": "B-roll cinematográfico mostrando procesamiento de datos.",
      "script_text": "Las redes neuronales procesan información de manera similar al cerebro humano.",
      "avatar": "no",
      "broll": ["visualización de datos", "cerebro digital", "nodos conectados", "algoritmos en código"],
      "transition": "deslizamiento",
      "text_on_screen": "Redes Neuronales",
      "audio_notes": "Voz en off narrativa. Música electrónica ambiental.",
      "platform": "gemini_veo"
    },
    {
      "id": "Escena 3",
      "duration_sec": 45,
      "summary": "Presentador explica aplicaciones prácticas de la IA.",
      "script_text": "Desde los asistentes virtuales hasta los sistemas de recomendación, la inteligencia artificial está en todas partes mejorando nuestra experiencia digital.",
      "avatar": "si",
      "broll": ["smartphone con asistente", "pantalla de streaming", "aplicaciones móviles"],
      "transition": "corte",
      "text_on_screen": "IA en la Vida Diaria",
      "audio_notes": "Tono conversacional. Énfasis en 'todas partes'. Música optimista.",
      "platform": "heygen"
    },
    {
      "id": "Escena 4",
      "duration_sec": 10,
      "summary": "Efectos visuales mostrando el futuro de la IA.",
      "script_text": "El futuro promete avances aún más sorprendentes.",
      "avatar": "no",
      "broll": ["ciudad futurista", "robots colaborando", "interfaces holográficas"],
      "transition": "fundido_a_negro",
      "text_on_screen": "El Futuro",
      "audio_notes": "Voz épica. Música épica creciente.",
      "platform": "sora"
    }
  ]
}
```

---

## Notas Importantes

1. **Campo `platform`**: Debe ser exactamente `"gemini_veo"`, `"sora"` o `"heygen"` (minúsculas, con guión bajo)
2. **Campo `avatar`**: Debe ser exactamente `"si"` o `"no"` (minúsculas, español)
3. **Respuesta al webhook**: Debe incluir `"status": "success"` y `"script_id"` para que Django lo procese correctamente
4. **Timeout**: El webhook tiene 30 segundos de timeout, pero n8n puede procesar en background usando Redis

---

## Integración con Redis

Si n8n tarda más de 30s, puede guardar el resultado en Redis:

**Key:** `script_result:{script_id}`
**Value:** JSON completo de la respuesta
**TTL:** 3600 segundos (1 hora)

Django hará polling de Redis cada 3-5 segundos para recuperar el resultado.

