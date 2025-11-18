"""
Ejemplos de uso completo de todos los modelos de Veo en Vertex AI
Demuestra todas las funcionalidades disponibles en cada modelo

IMPORTANTE: Este archivo es solo de referencia. Para usar en producción,
integra estas funcionalidades en tu servicio Django (core/services.py)
"""

import sys
import os
import base64
from pathlib import Path

# Agregar el directorio raíz al path para importar
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai_services.gemini_veo import GeminiVeoClient, VEO_MODELS


def print_model_info():
    """Imprime información de todos los modelos disponibles"""
    print("=" * 80)
    print("MODELOS VEO DISPONIBLES")
    print("=" * 80)
    
    for model_id, config in VEO_MODELS.items():
        print(f"\n📹 {model_id}")
        print(f"   Versión: {config['version']}")
        print(f"   Descripción: {config['description']}")
        print(f"   Duración: {config['duration_range'][0]}-{config['duration_range'][1]}s", end="")
        if 'duration_options' in config:
            print(f" (opciones: {config['duration_options']})")
        else:
            print()
        
        features = []
        if config['supports_audio']:
            features.append("✅ Audio")
        if config['supports_resolution']:
            features.append("✅ Resolution (720p/1080p)")
        if config['supports_reference_images']:
            features.append("✅ Reference Images")
        if config['supports_last_frame']:
            features.append("✅ Last Frame (fill-in)")
        if config['supports_video_extension']:
            features.append("✅ Video Extension")
        if config['supports_mask']:
            features.append("✅ Mask Editing")
        if config.get('supports_resize_mode'):
            features.append("✅ Resize Mode")
        
        if features:
            print(f"   Características: {', '.join(features)}")
        else:
            print(f"   Características: Text-to-video básico")
    
    print("\n" + "=" * 80)


# ==============================================================================
# EJEMPLO 1: Text-to-Video Básico (todos los modelos)
# ==============================================================================
def example_text_to_video_basic():
    """Ejemplo básico de generación de video desde texto"""
    print("\n" + "=" * 80)
    print("EJEMPLO 1: Text-to-Video Básico")
    print("=" * 80)
    
    # Puedes usar cualquier modelo
    client = GeminiVeoClient(model_name='veo-3.1-generate-preview')
    
    result = client.generate_video(
        prompt="Un drone volando sobre una playa tropical al atardecer, con olas suaves y palmeras",
        title="Playa Tropical Drone Shot",
        duration=8,
        aspect_ratio="16:9",
        sample_count=1
    )
    
    print(f"✅ Video iniciado")
    print(f"   Operation ID: {result['video_id']}")
    print(f"   Status: {result['status']}")
    
    return result


# ==============================================================================
# EJEMPLO 2: Veo 3.1 con Audio y Alta Resolución
# ==============================================================================
def example_veo_3_1_with_audio():
    """Veo 3.1 con audio y resolución 1080p"""
    print("\n" + "=" * 80)
    print("EJEMPLO 2: Veo 3.1 con Audio y 1080p")
    print("=" * 80)
    
    client = GeminiVeoClient(model_name='veo-3.1-generate-preview')
    
    result = client.generate_video(
        prompt="Un músico tocando una guitarra acústica en un estudio con iluminación cálida, plano medio, ambiente íntimo",
        title="Músico en Estudio",
        duration=8,
        aspect_ratio="16:9",
        generate_audio=True,  # Genera audio sincronizado
        resolution="1080p",   # Alta resolución
        person_generation="allow_adult",
        negative_prompt="iluminación cenital, colores fríos, multitudes"
    )
    
    print(f"✅ Video con audio iniciado en 1080p")
    print(f"   Operation ID: {result['video_id']}")
    
    return result


# ==============================================================================
# EJEMPLO 3: Image-to-Video con Veo 3
# ==============================================================================
def example_image_to_video(image_path: str = None):
    """Genera video a partir de una imagen"""
    print("\n" + "=" * 80)
    print("EJEMPLO 3: Image-to-Video")
    print("=" * 80)
    
    if not image_path or not os.path.exists(image_path):
        print("⚠️  No se proporcionó imagen. Usa: example_image_to_video('ruta/imagen.jpg')")
        return None
    
    # Leer imagen y convertir a base64
    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')
    
    client = GeminiVeoClient(model_name='veo-3.0-generate-001')
    
    result = client.generate_video(
        prompt="La escena cobra vida con movimiento suave, luz natural y ambiente cinematográfico",
        title="Animación desde Imagen",
        duration=6,
        aspect_ratio="16:9",
        input_image_base64=image_data,
        input_image_mime_type="image/jpeg",
        resize_mode="pad",  # Agregar padding para mantener aspecto
        generate_audio=True,
        resolution="720p"
    )
    
    print(f"✅ Image-to-video iniciado")
    print(f"   Operation ID: {result['video_id']}")
    
    return result


# ==============================================================================
# EJEMPLO 4: Reference Images con Veo 3.1 (Asset)
# ==============================================================================
def example_reference_images_asset(ref_image_path: str = None):
    """Usa imágenes de referencia para mantener consistencia visual"""
    print("\n" + "=" * 80)
    print("EJEMPLO 4: Reference Images (Asset)")
    print("=" * 80)
    
    if not ref_image_path or not os.path.exists(ref_image_path):
        print("⚠️  No se proporcionó imagen de referencia.")
        return None
    
    # Leer imagen de referencia
    with open(ref_image_path, 'rb') as f:
        ref_image_data = base64.b64encode(f.read()).decode('utf-8')
    
    client = GeminiVeoClient(model_name='veo-3.1-generate-preview')
    
    reference_images = [
        {
            "base64": ref_image_data,
            "mime_type": "image/jpeg",
            "reference_type": "asset"  # Personaje, objeto o escena de referencia
        }
    ]
    
    result = client.generate_video(
        prompt="El personaje camina por una ciudad futurista con edificios altos y luces de neón",
        title="Video con Personaje de Referencia",
        duration=8,  # DEBE ser 8 segundos con reference images
        aspect_ratio="16:9",
        reference_images=reference_images,
        generate_audio=True,
        resolution="720p"
    )
    
    print(f"✅ Video con reference images iniciado")
    print(f"   Operation ID: {result['video_id']}")
    
    return result


# ==============================================================================
# EJEMPLO 5: Reference Images con Veo 2.0-exp (Style)
# ==============================================================================
def example_reference_images_style(style_image_path: str = None):
    """Usa imagen de estilo para transferencia de estilo artístico"""
    print("\n" + "=" * 80)
    print("EJEMPLO 5: Reference Images (Style) - Solo Veo 2.0-exp")
    print("=" * 80)
    
    if not style_image_path or not os.path.exists(style_image_path):
        print("⚠️  No se proporcionó imagen de estilo.")
        return None
    
    # Leer imagen de estilo
    with open(style_image_path, 'rb') as f:
        style_image_data = base64.b64encode(f.read()).decode('utf-8')
    
    client = GeminiVeoClient(model_name='veo-2.0-generate-exp')
    
    reference_images = [
        {
            "base64": style_image_data,
            "mime_type": "image/jpeg",
            "reference_type": "style"  # Transferencia de estilo
        }
    ]
    
    result = client.generate_video(
        prompt="Un paisaje de montañas con un lago tranquilo, nubes suaves y luz dorada",
        title="Video con Estilo Artístico",
        duration=8,
        aspect_ratio="16:9",
        reference_images=reference_images
    )
    
    print(f"✅ Video con style transfer iniciado")
    print(f"   Operation ID: {result['video_id']}")
    
    return result


# ==============================================================================
# EJEMPLO 6: Multiple Reference Images (hasta 3 assets)
# ==============================================================================
def example_multiple_reference_images(image_paths: list = None):
    """Usa múltiples imágenes de referencia (hasta 3)"""
    print("\n" + "=" * 80)
    print("EJEMPLO 6: Multiple Reference Images (hasta 3 assets)")
    print("=" * 80)
    
    if not image_paths or len(image_paths) == 0:
        print("⚠️  No se proporcionaron imágenes de referencia.")
        return None
    
    reference_images = []
    for idx, img_path in enumerate(image_paths[:3]):  # Max 3 imágenes
        if os.path.exists(img_path):
            with open(img_path, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode('utf-8')
            
            reference_images.append({
                "base64": img_data,
                "mime_type": "image/jpeg",
                "reference_type": "asset"
            })
    
    client = GeminiVeoClient(model_name='veo-3.1-generate-preview')
    
    result = client.generate_video(
        prompt="Los personajes interactúan en una escena cinematográfica con movimiento fluido",
        title="Video con Múltiples Referencias",
        duration=8,
        aspect_ratio="16:9",
        reference_images=reference_images,
        generate_audio=True,
        resolution="720p"
    )
    
    print(f"✅ Video con {len(reference_images)} imágenes de referencia iniciado")
    print(f"   Operation ID: {result['video_id']}")
    
    return result


# ==============================================================================
# EJEMPLO 7: Last Frame (Fill-in-the-blank)
# ==============================================================================
def example_last_frame(first_frame_path: str = None, last_frame_path: str = None):
    """Genera video entre dos frames (fill-in-the-blank)"""
    print("\n" + "=" * 80)
    print("EJEMPLO 7: Last Frame (Fill-in-the-blank)")
    print("=" * 80)
    
    if not first_frame_path or not last_frame_path:
        print("⚠️  Se necesitan ambos frames (primero y último).")
        return None
    
    # Leer ambos frames
    with open(first_frame_path, 'rb') as f:
        first_frame_data = base64.b64encode(f.read()).decode('utf-8')
    
    with open(last_frame_path, 'rb') as f:
        last_frame_data = base64.b64encode(f.read()).decode('utf-8')
    
    client = GeminiVeoClient(model_name='veo-3.1-generate-preview')
    
    result = client.generate_video(
        prompt="Transición suave y natural entre los dos momentos, con movimiento fluido",
        title="Video Fill-in-the-blank",
        duration=8,
        aspect_ratio="16:9",
        input_image_base64=first_frame_data,
        input_image_mime_type="image/jpeg",
        last_frame_base64=last_frame_data,
        last_frame_mime_type="image/jpeg",
        generate_audio=True,
        resolution="720p"
    )
    
    print(f"✅ Fill-in-the-blank iniciado")
    print(f"   Operation ID: {result['video_id']}")
    
    return result


# ==============================================================================
# EJEMPLO 8: Video Extension
# ==============================================================================
def example_video_extension(video_path: str = None):
    """Extiende la duración de un video existente"""
    print("\n" + "=" * 80)
    print("EJEMPLO 8: Video Extension")
    print("=" * 80)
    
    if not video_path or not os.path.exists(video_path):
        print("⚠️  No se proporcionó video base.")
        return None
    
    # Leer video
    with open(video_path, 'rb') as f:
        video_data = base64.b64encode(f.read()).decode('utf-8')
    
    client = GeminiVeoClient(model_name='veo-3.0-generate-preview')
    
    result = client.generate_video(
        prompt="Continúa la acción de forma natural, manteniendo la coherencia visual",
        title="Video Extendido",
        duration=8,
        aspect_ratio="16:9",
        video_base64=video_data,
        video_mime_type="video/mp4",
        generate_audio=True,
        resolution="720p"
    )
    
    print(f"✅ Video extension iniciado")
    print(f"   Operation ID: {result['video_id']}")
    
    return result


# ==============================================================================
# EJEMPLO 9: Mask Editing (veo-2.0-generate-preview)
# ==============================================================================
def example_mask_editing(video_or_image_path: str = None, mask_path: str = None):
    """Edita video usando máscara para añadir/quitar objetos"""
    print("\n" + "=" * 80)
    print("EJEMPLO 9: Mask Editing")
    print("=" * 80)
    
    if not video_or_image_path or not mask_path:
        print("⚠️  Se necesita video/imagen base y máscara.")
        return None
    
    # Leer imagen base
    with open(video_or_image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')
    
    # Leer máscara
    with open(mask_path, 'rb') as f:
        mask_data = base64.b64encode(f.read()).decode('utf-8')
    
    client = GeminiVeoClient(model_name='veo-2.0-generate-preview')
    
    result = client.generate_video(
        prompt="Un objeto mágico aparece en la escena con efectos visuales",
        title="Video con Mask Editing",
        duration=8,
        aspect_ratio="16:9",
        input_image_base64=image_data,
        input_image_mime_type="image/jpeg",
        mask_base64=mask_data,
        mask_mime_type="image/png",
        mask_mode="foreground"  # o "background"
    )
    
    print(f"✅ Mask editing iniciado")
    print(f"   Operation ID: {result['video_id']}")
    
    return result


# ==============================================================================
# EJEMPLO 10: Configuración Avanzada con Todos los Parámetros
# ==============================================================================
def example_advanced_configuration():
    """Ejemplo con configuración completa y avanzada"""
    print("\n" + "=" * 80)
    print("EJEMPLO 10: Configuración Avanzada Completa")
    print("=" * 80)
    
    client = GeminiVeoClient(model_name='veo-3.1-fast-generate-preview')
    
    result = client.generate_video(
        # Prompt
        prompt=(
            "Un astronauta camina por una estación espacial futurista con ventanas "
            "panorámicas que muestran la Tierra, iluminación azul suave, movimiento "
            "lento y elegante, ambiente cinematográfico de ciencia ficción"
        ),
        title="Astronauta en Estación Espacial",
        
        # Configuración básica
        duration=8,
        aspect_ratio="16:9",
        sample_count=2,  # Genera 2 variaciones
        
        # Prompts avanzados
        negative_prompt="personas adicionales, armas, violencia, colores saturados",
        enhance_prompt=True,  # Gemini mejora el prompt
        
        # Configuración de personas y calidad
        person_generation="allow_adult",
        compression_quality="optimized",
        
        # Veo 3.1 features
        generate_audio=True,
        resolution="1080p",
        
        # Reproducibilidad
        seed=42,  # Para resultados reproducibles
        
        # Storage (opcional)
        # storage_uri="gs://mi-bucket/videos/astronauta/"
    )
    
    print(f"✅ Video avanzado iniciado")
    print(f"   Operation ID: {result['video_id']}")
    print(f"   Samples: 2 variaciones")
    print(f"   Resolution: 1080p")
    print(f"   Audio: Sí")
    
    return result


# ==============================================================================
# EJEMPLO 11: Consultar Estado de Video
# ==============================================================================
def example_check_status(operation_name: str):
    """Consulta el estado de un video en proceso"""
    print("\n" + "=" * 80)
    print("EJEMPLO 11: Consultar Estado del Video")
    print("=" * 80)
    
    client = GeminiVeoClient(model_name='veo-3.1-generate-preview')
    
    status = client.get_video_status(operation_name)
    
    print(f"Status: {status['status']}")
    
    if status['status'] == 'completed':
        print(f"✅ Video completado!")
        print(f"   URL principal: {status.get('video_url')}")
        
        all_videos = status.get('all_video_urls', [])
        if len(all_videos) > 1:
            print(f"   Total de variaciones: {len(all_videos)}")
            for idx, video_info in enumerate(all_videos):
                print(f"   Video {idx + 1}: {video_info['url']}")
        
        rai_filtered = status.get('rai_filtered_count', 0)
        if rai_filtered > 0:
            print(f"   ⚠️  Videos filtrados por IA Responsable: {rai_filtered}")
    
    elif status['status'] == 'processing':
        print(f"⏳ Video aún procesando...")
    
    elif status['status'] == 'failed':
        print(f"❌ Error: {status.get('error')}")
    
    return status


# ==============================================================================
# FUNCIÓN PRINCIPAL
# ==============================================================================
def main():
    """Función principal con menú de ejemplos"""
    print("\n" + "=" * 80)
    print("EJEMPLOS DE USO DE TODOS LOS MODELOS VEO")
    print("=" * 80)
    
    # Mostrar información de modelos
    print_model_info()
    
    print("\n📚 EJEMPLOS DISPONIBLES:")
    print("   1. Text-to-Video Básico")
    print("   2. Veo 3.1 con Audio y 1080p")
    print("   3. Image-to-Video")
    print("   4. Reference Images (Asset)")
    print("   5. Reference Images (Style) - Veo 2.0-exp")
    print("   6. Multiple Reference Images")
    print("   7. Last Frame (Fill-in-the-blank)")
    print("   8. Video Extension")
    print("   9. Mask Editing")
    print("   10. Configuración Avanzada Completa")
    print("   11. Consultar Estado de Video")
    
    print("\n💡 Para ejecutar un ejemplo:")
    print("   from examples.veo_all_models_example import example_text_to_video_basic")
    print("   result = example_text_to_video_basic()")
    
    print("\n🔍 Para consultar estado:")
    print("   from examples.veo_all_models_example import example_check_status")
    print("   status = example_check_status('projects/.../operations/...')")
    
    print("\n" + "=" * 80)


if __name__ == '__main__':
    main()

