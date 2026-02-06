from langchain.tools import tool
from typing import List, Dict
from core.ai_services.manim.registry import AnimationRegistry

@tool
def list_manim_templates_tool() -> List[Dict[str, str]]:
    """
    Lista los templates de diseños Manim disponibles.
    Útil para saber qué tipos de animaciones o gráficos se pueden generar.
    
    Returns:
        Lista de diccionarios con 'type' (identificador) y 'description' (docstring).
    """
    templates = []
    for anim_type in AnimationRegistry.list_types():
        anim_class = AnimationRegistry.get(anim_type)
        if anim_class:
            # Obtener el docstring de la clase y limpiarlo un poco
            doc = anim_class.__doc__ or "Sin descripción"
            doc = doc.strip().split('\n')[0]  # Tomar solo la primera línea
            
            # Obtener parámetros si están disponibles
            params = {}
            if hasattr(anim_class, 'get_parameters'):
                params = anim_class.get_parameters()
            
            templates.append({
                "type": anim_type,
                "description": doc,
                "parameters": params
            })
            
    return templates
