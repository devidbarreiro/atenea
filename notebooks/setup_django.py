"""
Script de configuración para usar Django en notebooks de Jupyter.

Uso:
    En un notebook, ejecuta:
    
    %run notebooks/setup_django.py
    
    O importa directamente:
    
    from notebooks.setup_django import setup_django
    setup_django()
"""
import os
import sys
from pathlib import Path

def setup_django():
    """
    Configura Django para poder usarlo en notebooks de Jupyter.
    """
    # Obtener el directorio raíz del proyecto
    project_root = Path(__file__).resolve().parent.parent
    
    # Añadir al path si no está
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # Configurar Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'atenea.settings')
    
    # Inicializar Django
    import django
    django.setup()
    
    print("✅ Django configurado correctamente")
    print(f"   Proyecto: {project_root}")
    print(f"   Settings: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
    
    return project_root

if __name__ == '__main__':
    setup_django()

