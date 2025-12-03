# Manim

<div class="flex items-center gap-3 mb-4">
  <img src="/static/img/logos/manim.png" alt="Manim" class="w-12 h-12 object-contain">
  <div>
    <h2 class="text-xl font-bold">Manim</h2>
    <p class="text-sm text-gray-600">Generación de videos animados con citas</p>
  </div>
</div>

## Descripción

Manim es una biblioteca de Python para crear animaciones matemáticas y visuales. En Atenea, utilizamos Manim para generar videos animados con citas textuales.

## Características

- ✅ Generación de videos con citas animadas
- ✅ Personalización de colores y fuentes
- ✅ Múltiples calidades de renderizado
- ✅ Soporte para autor de la cita

## Tipo de Contenido

**Video** - Videos animados con texto

## Precio

**~1 crédito por video** (independiente de la duración)

---

## Endpoints Disponibles

### Video Generation

- **[Generar Video de Cita](video/generate_quote_video.md)** - Crea un video animado con una cita

---

## Configuración

### Calidades Disponibles

- `l` - 480p15 (baja calidad, rápido)
- `m` - 720p30 (calidad media)
- `h` - 1080p60 (alta calidad)
- `k` - 2160p60 (4K, máxima calidad) - **Por defecto**

### Personalización

- **Colores**: Contenedor y texto personalizables
- **Fuentes**: Normal, bold, italic, bold_italic
- **Duración**: Automática o personalizada

---

## Ejemplos de Uso

### Video Simple

```python
from core.ai_services.manim import ManimClient

client = ManimClient()
result = client.generate_quote_video(
    quote="La creatividad es la inteligencia divirtiéndose",
    author="Albert Einstein"
)
```

### Video Personalizado

```python
result = client.generate_quote_video(
    quote="El único modo de hacer un gran trabajo es amar lo que haces",
    author="Steve Jobs",
    quality="h",  # 1080p60
    container_color="#0066CC",
    text_color="#FFFFFF",
    font_family="bold"
)
```

---

## Más Información

- [Documentación de Manim](https://docs.manim.community/)
- [Generar Video de Cita](video/generate_quote_video.md)

