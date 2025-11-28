"""
Wrapper para ejecutar animaciones Manim
Este archivo permite ejecutar cualquier animación registrada leyendo configuración
desde un archivo JSON temporal (evita problemas de concurrencia con variables de entorno)
"""
import os
import sys
import json
from pathlib import Path

# Añadir el directorio del proyecto al path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Importar Django settings si es necesario
django_available = False
try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'atenea.settings')
    import django
    django.setup()
    django_available = True
except ImportError:
    # Django no está disponible, pero puede que no sea necesario
    pass
except Exception as e:
    # Otros errores de Django (configuración, etc.) - log pero continuar
    print(f"Advertencia: No se pudo inicializar Django: {e}", file=sys.stderr)

# Importar animaciones para que se registren automáticamente
try:
    from core.ai_services.manim import animations  # noqa: F401
    from core.ai_services.manim.registry import AnimationRegistry
except ImportError as e:
    print(f"Error: No se pudieron importar las animaciones: {e}", file=sys.stderr)
    sys.exit(1)

try:
    from manim import *
except ImportError:
    print("Error: manim no está instalado. Instala con: pip install manim", file=sys.stderr)
    sys.exit(1)

# Obtener ruta del archivo de configuración desde argumento o variable de entorno
config_file_path = None
if len(sys.argv) > 1:
    # El primer argumento después del nombre del script es la ruta del archivo de config
    config_file_path = Path(sys.argv[1])
elif 'MANIM_CONFIG_FILE' in os.environ:
    # Fallback a variable de entorno (solo para compatibilidad)
    config_file_path = Path(os.environ['MANIM_CONFIG_FILE'])

if not config_file_path or not config_file_path.exists():
    print(f"Error: Archivo de configuración no encontrado: {config_file_path}", file=sys.stderr)
    print("Uso: python render_wrapper.py <ruta_al_config.json>", file=sys.stderr)
    sys.exit(1)

# Leer configuración desde archivo JSON
try:
    with open(config_file_path, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
except Exception as e:
    print(f"Error al leer archivo de configuración: {e}", file=sys.stderr)
    sys.exit(1)

# Obtener tipo de animación desde config
animation_type = config_data.get('animation_type', 'quote')

if not animation_type:
    print("Error: animation_type no está configurado en el archivo de configuración", file=sys.stderr)
    sys.exit(1)

animation_class = AnimationRegistry.get(animation_type)

if not animation_class:
    available = AnimationRegistry.list_types()
    print(f"Error: Tipo de animación '{animation_type}' no encontrado.", file=sys.stderr)
    print(f"Tipos disponibles: {available}", file=sys.stderr)
    sys.exit(1)

# Extraer configuración específica de la animación (sin animation_type)
animation_config = {k: v for k, v in config_data.items() if k != 'animation_type'}

# Crear y ejecutar la animación con configuración
try:
    scene = animation_class(config=animation_config)
    scene.render()
except Exception as e:
    print(f"Error al ejecutar animación '{animation_type}': {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    # Limpiar archivo temporal después de usar
    try:
        if config_file_path.exists():
            config_file_path.unlink()
    except Exception as e:
        # No fallar si no se puede eliminar
        print(f"Advertencia: No se pudo eliminar archivo temporal: {e}", file=sys.stderr)

