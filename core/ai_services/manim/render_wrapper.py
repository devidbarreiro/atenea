"""
Wrapper para ejecutar animaciones Manim
Este archivo permite ejecutar cualquier animación registrada mediante variables de entorno
"""
import os
import sys
from pathlib import Path

# Añadir el directorio del proyecto al path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Importar Django settings si es necesario
try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'atenea.settings')
    import django
    django.setup()
except:
    # Si Django no está disponible, continuar sin él
    pass

# Importar animaciones para que se registren automáticamente
from core.ai_services.manim import animations  # noqa: F401
from core.ai_services.manim.registry import AnimationRegistry

try:
    from manim import *
except ImportError:
    print("Error: manim no está instalado")
    sys.exit(1)

# Obtener el tipo de animación desde variable de entorno
animation_type = os.environ.get('MANIM_ANIMATION_TYPE', 'quote')
animation_class = AnimationRegistry.get(animation_type)

if not animation_class:
    available = AnimationRegistry.list_types()
    print(f"Error: Tipo de animación '{animation_type}' no encontrado.")
    print(f"Tipos disponibles: {available}")
    sys.exit(1)

# Crear y ejecutar la animación
scene = animation_class()
scene.render()

