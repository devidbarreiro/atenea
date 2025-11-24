# Resumen de Servicios de Atenea

## Sistema de Créditos

Atenea utiliza un sistema de créditos para controlar el uso de servicios de generación de contenido audiovisual.

- **Equivalencia**: 100 créditos Atenea = 1 USD
- **Documentación técnica**: Ver [Sistema de Créditos](../overview/credits-system.md)
- **Guía de usuario**: Ver [Guía de Usuario de Créditos](../overview/credits-user-guide.md)

---

## Servicios Disponibles

### Generación de Video

- **[Google Gemini Veo](../google/gemini_video/)** - Generación de video desde texto o imagen
- **[OpenAI Sora](../openai/video/)** - Generación de video de alta calidad
- **[HeyGen](../heygen/)** - Avatares hablantes con IA
- **[Vuela.ai](../vuela/)** - Generación de video con scripts

### Generación de Imagen

- **[Google Gemini Image](../google/gemini_image/)** - Generación de imágenes desde texto

### Generación de Audio

- **[ElevenLabs TTS](../elevenlabs/)** - Texto a voz con voces naturales

### Recursos Externos

- **[Freepik](../freepik/)** - Búsqueda y descarga de imágenes, videos e iconos

---

## Arquitectura General

Todos los servicios siguen una arquitectura común:

- **Cliente Base**: `BaseAIClient` para servicios de IA
- **Servicio**: Clases de servicio en `core/services.py`
- **Modelos**: Modelos Django para almacenar contenido generado
- **Storage**: Google Cloud Storage (GCS) para almacenar archivos

---

## Más Información

Para detalles específicos de cada servicio, consulta la documentación en cada directorio.

