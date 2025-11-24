# Investigación de Precios - Servicios de IA

## Equivalencia Base
- **100 créditos Atenea = 1 USD**
- Conversión directa: 1 USD = 100 créditos Atenea

---

## ⚠️ IMPORTANTE: Servicios que NO se cobran

**NO cobramos llamadas a LLM** (OpenAI GPT, Google Gemini para texto).
Solo cobramos cuando se hace **generación propia de contenido audiovisual** con servicios de IA.

---

## Tabla de Precios Confirmados - Servicios de Generación Audiovisual

### 1. Google Vertex AI Veo
**Fuente**: Google Cloud Vertex AI Pricing

| Modelo | Característica | Precio por Segundo | Créditos Atenea/segundo |
|--------|----------------|-------------------|------------------------|
| Veo 3 | Generación de video | $0.50 USD | **50 créditos** |
| Veo 3 | Generación de video + audio | $0.75 USD | **75 créditos** |
| Veo 2 | Generación de video | $0.50 USD | **50 créditos** |
| Veo 2 | Controles avanzados | $0.50 USD | **50 créditos** |

**Notas**:
- Precio basado en duración del video generado
- Veo 3 con audio tiene costo adicional de $0.25/segundo
- No varía según resolución (720p vs 1080p tienen mismo precio)

**Cálculo**:
- Veo 2/3 video: $0.50 / segundo × 100 créditos/USD = **50 créditos/segundo**
- Veo 3 video+audio: $0.75 / segundo × 100 créditos/USD = **75 créditos/segundo**

---

### 2. OpenAI Sora 2
**Fuente**: OpenAI Pricing Page

| Modelo | Resolución | Precio por Segundo | Créditos Atenea/segundo |
|--------|------------|-------------------|------------------------|
| Sora-2 | 720x1280 o 1280x720 | $0.10 USD | **10 créditos** |
| Sora-2 Pro | 1024x1792 o 1792x1024 | $0.50 USD | **50 créditos** |

**Cálculo**:
- Sora-2: $0.10 / segundo × 100 créditos/USD = **10 créditos/segundo**
- Sora-2 Pro: $0.50 / segundo × 100 créditos/USD = **50 créditos/segundo**

**Nota**: Precio basado en duración del video generado.

---

### 3. Google Vertex AI Imagen (Gemini Image Generation)
**Fuente**: Google Cloud Vertex AI Pricing

| Modelo | Precio por Imagen | Créditos Atenea/imagen |
|--------|------------------|----------------------|
| Imagen 4 Ultra | $0.06 USD | **6 créditos** |
| Imagen 4 | $0.04 USD | **4 créditos** |
| Imagen 4 Fast | $0.02 USD | **2 créditos** |
| Imagen 3 | $0.04 USD | **4 créditos** |
| Imagen 3 rápida | $0.02 USD | **2 créditos** |
| Imagen 2 | $0.020 USD | **2 créditos** |

**Notas**:
- Precio fijo por imagen generada
- No varía según aspect ratio
- Usamos **Imagen 4 Fast** o **Imagen 3 rápida** por defecto: **2 créditos/imagen**

**Cálculo**:
- Imagen 4 Fast: $0.02 / imagen × 100 créditos/USD = **2 créditos/imagen**
- Imagen 4: $0.04 / imagen × 100 créditos/USD = **4 créditos/imagen**

---

### 4. HeyGen API
**Fuente**: Información proporcionada + HeyGen API Pricing

| Tipo | Costo Real | Precio a Cliente | Créditos Atenea/segundo |
|------|------------|-----------------|------------------------|
| Avatar V2 (normal) | ~$0.03 USD/s | $0.05 USD/s | **5 créditos** |
| Avatar IV (premium) | ~$0.10 USD/s | $0.15-0.20 USD/s | **15-20 créditos** |

**Notas**:
- Precio basado en duración del video generado
- Aplicamos margen sobre costo real
- Avatar IV es más premium, podemos cobrar más

**Cálculo**:
- Avatar V2: $0.05 / segundo × 100 créditos/USD = **5 créditos/segundo**
- Avatar IV: $0.15-0.20 / segundo × 100 créditos/USD = **15-20 créditos/segundo**

**Recomendación**: Usar **5 créditos/segundo** para Avatar V2 y **15 créditos/segundo** para Avatar IV.

---

### 5. ElevenLabs TTS
**Fuente**: ElevenLabs Pricing Page

| Plan | Precio Mensual | Coste por Carácter | Créditos Atenea/carácter |
|------|----------------|-------------------|-------------------------|
| Starter | $5 USD | ~$0.00017 USD | **0.017 créditos** |
| Creator | $11 USD | ~$0.00011 USD | **0.011 créditos** |
| Pro | $99 USD | ~$0.000198 USD | **0.020 créditos** |
| Scale | $330 USD | ~$0.000165 USD | **0.017 créditos** |

**Notas**:
- Precio basado en **caracteres procesados** (no segundos de audio)
- Usaremos plan **Starter** como referencia: **$0.00017 USD por carácter**
- 1 minuto de audio ≈ 1,500 caracteres ≈ $0.26 USD ≈ **26 créditos**

**Cálculo**:
- Por carácter: $0.00017 / carácter × 100 créditos/USD = **0.017 créditos/carácter**
- Por minuto (estimado): 1,500 caracteres × 0.017 créditos = **~26 créditos/minuto**

**Recomendación**: Usar **0.017 créditos por carácter** (redondeado a 0.02 para simplificar).

---

### 6. Vuela.ai
**Estado**: ⚠️ **COSTOS ORIENTATIVOS** (verificar más adelante)

**Información**:
- El usuario indicó que "es barato"
- Basado en que es similar a otros servicios de video, estimamos precios orientativos

| Tipo | Precio Orientativo | Créditos Atenea/segundo |
|------|-------------------|------------------------|
| Basic | ~$0.03 USD/s | **3 créditos** |
| Premium | ~$0.05 USD/s | **5 créditos** |

**Notas**:
- ⚠️ **COSTOS ORIENTATIVOS** - Verificar con Vuela.ai más adelante
- Precio basado en duración del video generado
- Usaremos **3 créditos/segundo** como referencia (similar a HeyGen Avatar V2)

**Cálculo Orientativo**:
- Basic: $0.03 / segundo × 100 créditos/USD = **3 créditos/segundo**
- Premium: $0.05 / segundo × 100 créditos/USD = **5 créditos/segundo**

**Recomendación**: Usar **3 créditos/segundo** por defecto hasta confirmar precios oficiales.

---

## Resumen de Precios por Servicio

| Servicio | Tipo | Unidad | Precio USD | Créditos Atenea |
|----------|------|--------|------------|----------------|
| **Veo 2/3** | Video | Por segundo | $0.50 | 50 créditos |
| **Veo 3 + Audio** | Video+Audio | Por segundo | $0.75 | 75 créditos |
| **Sora-2** | Video | Por segundo | $0.10 | 10 créditos |
| **Sora-2 Pro** | Video | Por segundo | $0.50 | 50 créditos |
| **Gemini Image** | Imagen | Por imagen | $0.02-0.04 | 2-4 créditos |
| **HeyGen Avatar V2** | Video | Por segundo | $0.05 | 5 créditos |
| **HeyGen Avatar IV** | Video | Por segundo | $0.15 | 15 créditos |
| **ElevenLabs TTS** | Audio | Por carácter | $0.00017 | 0.017 créditos |
| **Vuela.ai** | Video | Por segundo | ~$0.03 (orientativo) | 3 créditos |

---

## Cálculo de Conversión USD → Créditos Atenea

**Fórmula Base**:
```
Créditos Atenea = Costo USD × 100
```

**Ejemplos**:
- Veo video de 8 segundos: 8s × 50 créditos/s = **400 créditos**
- Sora-2 video de 8 segundos: 8s × 10 créditos/s = **80 créditos**
- Imagen generada: **2 créditos** (Imagen 4 Fast)
- HeyGen Avatar IV de 30 segundos: 30s × 15 créditos/s = **450 créditos**
- ElevenLabs texto de 500 caracteres: 500 × 0.017 créditos = **8.5 créditos** (redondeado a 9)

---

## Casos Especiales de Cálculo

### Video con Agente (múltiples servicios)
Cuando se genera un video completo con el agente, se cobran **todos los servicios utilizados**:

1. **Script generation** (LLM): ❌ NO se cobra
2. **Imágenes preview** (Gemini Image): ✅ Se cobra cada imagen
3. **Videos de escenas** (Veo/Sora/HeyGen): ✅ Se cobra cada video por segundo
4. **Audios** (ElevenLabs): ✅ Se cobra por caracteres
5. **Combinación final**: ❌ NO se cobra (proceso interno)

**Ejemplo**: Video de 5 escenas de 8 segundos cada una:
- 5 imágenes preview: 5 × 2 créditos = **10 créditos**
- 5 videos Veo de 8s: 5 × 8s × 50 créditos/s = **2,000 créditos**
- 5 audios de ~200 caracteres: 5 × 200 × 0.017 = **17 créditos**
- **Total: ~2,027 créditos**

---

## Próximos Pasos

1. ✅ **Completado**: Documentar estructura de precios confirmados
2. ⏳ **Pendiente**: Verificar precio de Vuela.ai
3. ⏳ **Pendiente**: Crear tabla de conversión definitiva en código
4. ⏳ **Pendiente**: Implementar cálculo de costos en servicios
5. ⏳ **Pendiente**: Crear sistema de tracking y deducción

---

## Notas Importantes

- ✅ **Precios confirmados** para Veo, Sora, Gemini Image, HeyGen, ElevenLabs
- ⚠️ **Pendiente**: Vuela.ai necesita verificación
- 💰 **Margen aplicado** en HeyGen (cobramos más que costo real)
- 📊 **Tracking necesario**: Cada llamada debe registrar costo exacto
- 🔄 **Flexibilidad**: Sistema debe permitir actualizar precios fácilmente
- 📈 **Escalabilidad**: Considerar descuentos por volumen en el futuro

---

## Implementación Técnica

### Servicios que necesitan adaptación:

1. **Gemini Veo** (`core/ai_services/gemini_veo.py`)
   - ✅ Precio confirmado: $0.50/s (video), $0.75/s (video+audio)
   - ⏳ Adaptar para devolver costo en créditos

2. **Sora** (`core/ai_services/sora.py`)
   - ✅ Precio confirmado: $0.10/s (Sora-2), $0.50/s (Sora-2 Pro)
   - ⏳ Adaptar para devolver costo en créditos

3. **Gemini Image** (`core/ai_services/gemini_image.py`)
   - ✅ Precio confirmado: $0.02/imagen (Fast), $0.04/imagen (Standard)
   - ⏳ Adaptar para devolver costo en créditos

4. **HeyGen** (`core/ai_services/heygen.py`)
   - ✅ Precio confirmado: $0.05/s (V2), $0.15/s (IV)
   - ⏳ Adaptar para devolver costo en créditos

5. **ElevenLabs** (`core/ai_services/elevenlabs.py`)
   - ✅ Precio confirmado: $0.00017/carácter
   - ⏳ Adaptar para devolver costo en créditos basado en caracteres

6. **Vuela.ai** (`core/ai_services/vuela_ai.py`)
   - ⚠️ Pendiente verificación de precios
   - ⏳ Adaptar cuando se confirme precio
