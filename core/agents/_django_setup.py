"""
Módulo de inicialización de Django para LangGraph
Debe importarse ANTES de cualquier módulo que use Django
"""
import os
import sys

def setup_django():
    """Configura Django si no está ya configurado"""
    if 'django' not in sys.modules:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'atenea.settings')
        import django
        django.setup()
    else:
        import django
        if not hasattr(django, 'apps') or not django.apps.apps.ready:
            if not os.environ.get('DJANGO_SETTINGS_MODULE'):
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'atenea.settings')
            django.setup()

# Configurar Django automáticamente al importar este módulo
setup_django()


