"""
Utilidades para trabajar con Prompt Templates
"""
import logging
from typing import Optional
from core.models import PromptTemplate

logger = logging.getLogger(__name__)


def apply_prompt_template(user_prompt: str, template_id: Optional[str] = None) -> str:
    """
    Aplica un template de prompt al prompt del usuario
    
    El template se añade como prefijo al user prompt, ya que todos los servicios
    de IA solo tienen un campo 'prompt' (no soportan system prompt separado).
    
    Args:
        user_prompt: Prompt del usuario
        template_id: UUID del template a aplicar (opcional)
        
    Returns:
        Prompt final combinado (template + user prompt)
        
    Ejemplo:
        Template: "Create a cinematic video with smooth camera movements..."
        User prompt: "Un perro surfeando en una ola gigante"
        
        Resultado:
        "Create a cinematic video with smooth camera movements...
        
        Un perro surfeando en una ola gigante"
    """
    if not template_id:
        return user_prompt
    
    try:
        template = PromptTemplate.objects.get(uuid=template_id, is_active=True)
        
        # Combinar template como prefijo
        combined_prompt = f"{template.prompt_text}\n\n{user_prompt}"
        
        # Incrementar contador de uso
        template.increment_usage()
        
        logger.info(f"✓ Template aplicado: {template.name} (UUID: {template_id})")
        
        return combined_prompt
    
    except PromptTemplate.DoesNotExist:
        logger.warning(f"Template no encontrado o inactivo: {template_id}")
        return user_prompt
    except Exception as e:
        logger.error(f"Error aplicando template {template_id}: {e}")
        return user_prompt


def get_template_by_id(template_id: str) -> Optional[PromptTemplate]:
    """
    Obtiene un template por su UUID
    
    Args:
        template_id: UUID del template
        
    Returns:
        PromptTemplate o None si no existe
    """
    try:
        return PromptTemplate.objects.get(uuid=template_id, is_active=True)
    except PromptTemplate.DoesNotExist:
        return None


def get_default_template(template_type: str, recommended_service: Optional[str] = None) -> Optional[PromptTemplate]:
    """
    Obtiene el template "General" por defecto para un tipo y servicio
    
    Args:
        template_type: Tipo de template ('video', 'image', 'agent')
        recommended_service: Servicio recomendado (opcional)
        
    Returns:
        PromptTemplate "General" o None si no existe
    """
    filters = {
        'name': 'General',
        'template_type': template_type,
        'is_public': True,
        'is_active': True
    }
    
    if recommended_service:
        filters['recommended_service'] = recommended_service
    
    try:
        return PromptTemplate.objects.filter(**filters).first()
    except Exception as e:
        logger.error(f"Error obteniendo template por defecto: {e}")
        return None

