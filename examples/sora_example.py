"""
Ejemplos de uso de OpenAI Sora API
Crear videos con text-to-video e image-to-video
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'atenea.settings')
import django
django.setup()

from core.ai_services.sora import SoraClient
from django.conf import settings
import time


def example_text_to_video():
    """
    Ejemplo 1: Text-to-Video básico
    Genera un video a partir de un prompt de texto
    """
    print("\n" + "="*70)
    print("EJEMPLO 1: Text-to-Video básico")
    print("="*70)
    
    client = SoraClient(api_key=settings.OPENAI_API_KEY)
    
    # Crear video
    prompt = "A beautiful sunset over mountains with gentle clouds moving, cinematic lighting, 4k quality"
    
    print(f"\n📝 Prompt: {prompt}")
    print(f"🎬 Modelo: sora-2")
    print(f"⏱️  Duración: 8 segundos (opciones: 4, 8, 12)")
    print(f"📐 Tamaño: 1280x720 (horizontal)")
    
    try:
        result = client.generate_video(
            prompt=prompt,
            model="sora-2",
            seconds=8,
            size="1280x720"
        )
        
        video_id = result['video_id']
        print(f"\n✅ Video creado exitosamente!")
        print(f"   Video ID: {video_id}")
        print(f"   Status: {result['status']}")
        
        # Esperar a que se complete
        print(f"\n⏳ Esperando a que el video se complete...")
        final_status = client.wait_for_completion(video_id, max_wait_seconds=600)
        
        if final_status['status'] == 'completed':
            print(f"\n✅ ¡Video completado!")
            print(f"   Expira en: {final_status.get('expires_at')}")
            
            # Descargar video
            output_path = f"video_{video_id}.mp4"
            if client.download_video(video_id, output_path):
                print(f"\n📥 Video descargado: {output_path}")
            
            # Descargar thumbnail
            thumb_path = f"thumbnail_{video_id}.webp"
            if client.download_thumbnail(video_id, thumb_path):
                print(f"📥 Thumbnail descargado: {thumb_path}")
        else:
            print(f"\n❌ Video falló: {final_status.get('error')}")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def example_text_to_video_pro():
    """
    Ejemplo 2: Text-to-Video con Sora 2 Pro
    Mayor calidad, más tiempo de render
    """
    print("\n" + "="*70)
    print("EJEMPLO 2: Text-to-Video con Sora 2 Pro")
    print("="*70)
    
    client = SoraClient(api_key=settings.OPENAI_API_KEY)
    
    prompt = (
        "Close-up shot of a steaming coffee cup on a wooden table, "
        "morning light streaming through window blinds creating dramatic shadows, "
        "soft focus background, cinematic depth of field, professional product photography"
    )
    
    print(f"\n📝 Prompt: {prompt}")
    print(f"🎬 Modelo: sora-2-pro (alta calidad)")
    print(f"⏱️  Duración: 12 segundos (opciones: 4, 8, 12)")
    print(f"📐 Tamaño: 720x1280 (vertical)")
    
    try:
        result = client.generate_video(
            prompt=prompt,
            model="sora-2-pro",
            seconds=12,
            size="720x1280"
        )
        
        video_id = result['video_id']
        print(f"\n✅ Video creado con Sora 2 Pro!")
        print(f"   Video ID: {video_id}")
        print(f"   Status: {result['status']}")
        
        # Solo monitorear sin esperar completamente
        print(f"\n⏳ Monitoreando progreso (primeros 60 segundos)...")
        for i in range(6):
            time.sleep(10)
            status = client.get_video_status(video_id)
            print(f"   [{i*10}s] Status: {status['status']} - Progress: {status.get('progress', 0)}%")
            
            if status['status'] == 'completed':
                print(f"\n✅ ¡Video completado en {i*10} segundos!")
                break
            elif status['status'] == 'failed':
                print(f"\n❌ Video falló: {status.get('error')}")
                break
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def example_image_to_video():
    """
    Ejemplo 3: Image-to-Video
    Genera un video a partir de una imagen de referencia
    """
    print("\n" + "="*70)
    print("EJEMPLO 3: Image-to-Video (requiere imagen)")
    print("="*70)
    
    # Nota: Este ejemplo requiere una imagen física
    image_path = "sample_image.jpg"
    
    if not os.path.exists(image_path):
        print(f"\n⚠️  Este ejemplo requiere una imagen: {image_path}")
        print(f"   Crea una imagen o cambia la ruta en el código.")
        print(f"\n💡 IMPORTANTE: La imagen debe tener exactamente 1280x720 píxeles")
        return
    
    client = SoraClient(api_key=settings.OPENAI_API_KEY)
    
    prompt = "She turns around and smiles, then slowly walks out of the frame"
    
    print(f"\n📝 Prompt: {prompt}")
    print(f"🖼️  Imagen: {image_path}")
    print(f"🎬 Modelo: sora-2-pro")
    print(f"⏱️  Duración: 8 segundos")
    print(f"📐 Tamaño: 1280x720")
    print(f"\n⚠️  IMPORTANTE: La imagen debe ser exactamente 1280x720 píxeles")
    
    try:
        result = client.generate_video_with_image(
            prompt=prompt,
            input_reference_path=image_path,
            model="sora-2-pro",
            seconds=8,
            size="1280x720"
        )
        
        video_id = result['video_id']
        print(f"\n✅ Video con imagen creado!")
        print(f"   Video ID: {video_id}")
        print(f"   Status: {result['status']}")
        
        # Esperar a que se complete
        print(f"\n⏳ Esperando completar...")
        final_status = client.wait_for_completion(video_id)
        
        if final_status['status'] == 'completed':
            output_path = f"video_from_image_{video_id}.mp4"
            if client.download_video(video_id, output_path):
                print(f"\n✅ Video descargado: {output_path}")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def example_list_videos():
    """
    Ejemplo 4: Listar videos creados
    """
    print("\n" + "="*70)
    print("EJEMPLO 4: Listar videos recientes")
    print("="*70)
    
    client = SoraClient(api_key=settings.OPENAI_API_KEY)
    
    try:
        result = client.list_videos(limit=10)
        videos = result.get('data', [])
        
        print(f"\n📋 Videos recientes: {len(videos)}")
        
        for idx, video in enumerate(videos[:5], 1):
            print(f"\n{idx}. Video ID: {video.get('id')}")
            print(f"   Status: {video.get('status')}")
            print(f"   Model: {video.get('model')}")
            print(f"   Size: {video.get('size')}")
            print(f"   Duration: {video.get('seconds')}s")
            print(f"   Created: {video.get('created_at')}")
            
            if video.get('status') == 'completed':
                print(f"   Expires: {video.get('expires_at')}")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def example_polling_manual():
    """
    Ejemplo 5: Polling manual del estado
    """
    print("\n" + "="*70)
    print("EJEMPLO 5: Polling manual del estado")
    print("="*70)
    
    client = SoraClient(api_key=settings.OPENAI_API_KEY)
    
    # Crear video
    prompt = "A doorcam like video, a postman reaches, a dog opens the door and goes after the postman"
    
    print(f"\n📝 Prompt: {prompt}")
    
    try:
        # 1. Crear video
        result = client.generate_video(
            prompt=prompt,
            model="sora-2",
            seconds=8,
            size="720x1280"
        )
        
        video_id = result['video_id']
        print(f"\n✅ Video creado: {video_id}")
        
        # 2. Polling manual
        print(f"\n⏳ Polling manual cada 10 segundos...")
        max_attempts = 60  # 10 minutos máximo
        attempt = 0
        
        while attempt < max_attempts:
            attempt += 1
            
            # Consultar estado
            status = client.get_video_status(video_id)
            current_status = status['status']
            progress = status.get('progress', 0)
            
            print(f"[{attempt*10}s] Status: {current_status} | Progress: {progress}%")
            
            if current_status == 'completed':
                print(f"\n✅ ¡Video completado!")
                
                # Descargar
                output = f"video_polling_{video_id}.mp4"
                if client.download_video(video_id, output):
                    print(f"📥 Descargado: {output}")
                break
                
            elif current_status == 'failed':
                print(f"\n❌ Video falló: {status.get('error')}")
                break
            
            time.sleep(10)
        
        if attempt >= max_attempts:
            print(f"\n⏱️  Timeout: Video aún procesando después de {max_attempts*10}s")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def example_aspect_ratios():
    """
    Ejemplo 6: Diferentes aspect ratios
    """
    print("\n" + "="*70)
    print("EJEMPLO 6: Diferentes aspect ratios")
    print("="*70)
    
    client = SoraClient(api_key=settings.OPENAI_API_KEY)
    
    prompt = "A rotating product showcase of a modern smartwatch on a white background"
    
    aspect_ratios = [
        ("1280x720", "Horizontal 16:9 (YouTube, TV)"),
        ("720x1280", "Vertical 9:16 (TikTok, Instagram Stories)"),
        ("1024x1024", "Cuadrado 1:1 (Instagram Post)")
    ]
    
    print(f"\n📝 Prompt: {prompt}")
    print(f"🎬 Creando 3 videos con diferentes aspect ratios...\n")
    
    video_ids = []
    
    for size, description in aspect_ratios:
        print(f"📐 {description} ({size})")
        
        try:
            result = client.generate_video(
                prompt=prompt,
                model="sora-2",
                seconds=8,  # Usar duración permitida (4, 8 o 12)
                size=size
            )
            
            video_id = result['video_id']
            video_ids.append((video_id, size, description))
            print(f"   ✅ Video creado: {video_id}\n")
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}\n")
    
    print(f"\n📋 Videos creados: {len(video_ids)}")
    for vid, size, desc in video_ids:
        print(f"   - {vid} ({desc})")


# ====================
# MEJORES PRÁCTICAS
# ====================

def best_practices_prompts():
    """
    Tips y mejores prácticas para escribir prompts efectivos
    """
    print("\n" + "="*70)
    print("💡 MEJORES PRÁCTICAS PARA PROMPTS DE SORA")
    print("="*70)
    
    tips = [
        "1. TIPO DE PLANO: Especifica 'close-up', 'wide shot', 'medium shot'",
        "2. SUJETO: Describe qué hay en la escena",
        "3. ACCIÓN: Qué está haciendo el sujeto",
        "4. ESCENARIO: Dónde ocurre la acción",
        "5. ILUMINACIÓN: 'golden hour', 'soft light', 'dramatic shadows'",
        "6. CÁMARA: 'camera slowly pans', 'static shot', 'dolly zoom'",
        "7. ESTILO: 'cinematic', '4k quality', 'professional photography'",
    ]
    
    print("\n⚠️  IMPORTANTE - Imágenes de Referencia:")
    print("   Si usas imagen de referencia (image-to-video):")
    print("   - La imagen DEBE tener exactamente las mismas dimensiones que el video")
    print("   - Video 1280x720 → Imagen 1280x720")
    print("   - Video 720x1280 → Imagen 720x1280")
    print("   - Video 1024x1024 → Imagen 1024x1024")
    
    print("\n✨ Tips para mejores resultados:")
    for tip in tips:
        print(f"   {tip}")
    
    print("\n❌ Contenido PROHIBIDO:")
    print("   - Personas reales (celebridades, figuras públicas)")
    print("   - Contenido con copyright (personajes, música)")
    print("   - Imágenes con caras humanas (para input_reference)")
    print("   - Solo contenido apto para menores de 18 años")
    print("   - Contenido violento, explícito o político")
    
    print("\n✅ Ejemplos de buenos prompts:")
    
    examples = [
        {
            "tipo": "Product Showcase",
            "prompt": "Close-up of a steaming coffee cup on wooden table, morning light through blinds, soft depth of field"
        },
        {
            "tipo": "Nature Scene",
            "prompt": "Wide shot of ocean waves crashing on rocky shore, golden hour sunset, slow motion, cinematic 4k"
        },
        {
            "tipo": "Urban Scene",
            "prompt": "Time-lapse of busy city street at night, car lights creating light trails, wide angle shot"
        },
        {
            "tipo": "Abstract",
            "prompt": "Colorful ink diffusing in water, macro shot, black background, high contrast lighting"
        },
    ]
    
    for ex in examples:
        print(f"\n   • {ex['tipo']}:")
        print(f"     \"{ex['prompt']}\"")


# ====================
# MENU PRINCIPAL
# ====================

def main():
    """Menú principal de ejemplos"""
    print("\n" + "="*70)
    print(" 🎬 EJEMPLOS DE OPENAI SORA API")
    print("="*70)
    
    print("\nElige un ejemplo:")
    print("  1. Text-to-Video básico (Sora 2)")
    print("  2. Text-to-Video Pro (Sora 2 Pro)")
    print("  3. Image-to-Video (requiere imagen)")
    print("  4. Listar videos recientes")
    print("  5. Polling manual del estado")
    print("  6. Diferentes aspect ratios")
    print("  7. Mejores prácticas para prompts")
    print("  0. Ejecutar todos los ejemplos")
    
    choice = input("\nOpción (1-7, 0 para todos): ").strip()
    
    if choice == "1":
        example_text_to_video()
    elif choice == "2":
        example_text_to_video_pro()
    elif choice == "3":
        example_image_to_video()
    elif choice == "4":
        example_list_videos()
    elif choice == "5":
        example_polling_manual()
    elif choice == "6":
        example_aspect_ratios()
    elif choice == "7":
        best_practices_prompts()
    elif choice == "0":
        example_text_to_video()
        example_text_to_video_pro()
        example_list_videos()
        example_aspect_ratios()
        best_practices_prompts()
    else:
        print("\n❌ Opción no válida")
    
    print("\n" + "="*70)
    print(" ✅ Ejemplos finalizados")
    print("="*70 + "\n")


if __name__ == '__main__':
    # Verificar que hay API key
    if not settings.OPENAI_API_KEY:
        print("\n❌ Error: OPENAI_API_KEY no está configurada")
        print("   Por favor, configúrala en tu archivo .env:\n")
        print("   OPENAI_API_KEY=tu-api-key-aqui\n")
        exit(1)
    
    main()

