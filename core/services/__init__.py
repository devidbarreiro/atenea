"""
Servicios de la aplicación
Importa y re-exporta todo desde services.py para mantener compatibilidad
"""

# Importar todo desde el módulo services.py usando importlib
# Esto permite que los imports existentes sigan funcionando: from core.services import ProjectService
import sys
import importlib.util
import os

# Obtener la ruta del archivo services.py (en el directorio padre de services/)
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
services_py_path = os.path.join(parent_dir, 'services.py')

# Cargar el módulo services.py
spec = importlib.util.spec_from_file_location("core.services_main", services_py_path)
services_main = importlib.util.module_from_spec(spec)

# Ejecutar el módulo para cargar todas las clases
spec.loader.exec_module(services_main)

# Re-exportar todas las clases y funciones públicas
for name in dir(services_main):
    if not name.startswith('_'):
        obj = getattr(services_main, name)
        # Solo exportar clases y funciones, no módulos ni variables internas
        if isinstance(obj, type) or callable(obj):
            setattr(sys.modules[__name__], name, obj)

# También exportar desde credits
from .credits import CreditService, InsufficientCreditsException, RateLimitExceededException
