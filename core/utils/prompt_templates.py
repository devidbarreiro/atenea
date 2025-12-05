"""
Utilidades para trabajar con Prompt Templates
"""
import logging
from typing import Optional
from core.models import PromptTemplate
from core.llm.factory import LLMFactory

logger = logging.getLogger(__name__)


def apply_prompt_template(user_prompt: str, template_id: Optional[str] = None) -> str:
    """
    Aplica un template de prompt al prompt del usuario usando LLM remix
    
    Siempre usa GPT-4o-mini para combinar y optimizar el template con el prompt del usuario.
    Si el LLM falla, hace fallback a concatenación simple.
    
    Args:
        user_prompt: Prompt del usuario
        template_id: UUID del template a aplicar (opcional)
        
    Returns:
        Prompt final optimizado por LLM o concatenación simple si falla
    """
    if not template_id:
        logger.info(f"⚠️ PROMPT SIN TEMPLATE - Usando prompt del usuario directamente: {user_prompt[:100]}...")
        return user_prompt
    
    try:
        template = PromptTemplate.objects.get(uuid=template_id, is_active=True)
        
        # Log del prompt inicial
        logger.info("=" * 80)
        logger.info(f"🎬 APLICANDO TEMPLATE: {template.name} (UUID: {template_id})")
        logger.info("-" * 80)
        logger.info(f"📝 TEMPLATE ORIGINAL:\n{template.prompt_text}")
        logger.info("-" * 80)
        logger.info(f"👤 PROMPT DEL USUARIO:\n{user_prompt}")
        logger.info("-" * 80)
        
        # SIEMPRE usar LLM remix para combinar template + user prompt
        try:
            final_prompt = _remix_prompt_with_llm(template.prompt_text, user_prompt)
            logger.info(f"✅ PROMPT FINAL (LLM REMIX):\n{final_prompt}")
            logger.info("=" * 80)
        except Exception as llm_error:
            # Fallback seguro: concatenación simple
            logger.warning(f"⚠️ LLM remix falló para template {template_id}, usando concatenación: {llm_error}")
            final_prompt = f"{template.prompt_text}\n\n{user_prompt}"
            logger.info(f"✅ PROMPT FINAL (FALLBACK - CONCATENACIÓN):\n{final_prompt}")
            logger.info("=" * 80)
        
        # Incrementar contador de uso
        template.increment_usage()
        
        return final_prompt
    
    except PromptTemplate.DoesNotExist:
        logger.warning(f"Template no encontrado o inactivo: {template_id}")
        return user_prompt
    except Exception as e:
        logger.error(f"Error aplicando template {template_id}: {e}")
        return user_prompt


def _remix_prompt_with_llm(template_text: str, user_prompt: str) -> str:
    """
    Usa GPT-4o-mini para combinar y optimizar template + user prompt
    
    El LLM rellena variables del template (si las hay) y mejora/expande el prompt
    basándose en el contexto del template y el prompt del usuario.
    
    Args:
        template_text: Texto del template (puede tener variables {variable})
        user_prompt: Prompt del usuario
        
    Returns:
        Prompt final optimizado por el LLM
        
    Raises:
        Exception: Si falla la llamada al LLM
    """
    try:
        # Crear instancia de LLM (GPT-4o-mini)
        llm = LLMFactory.get_llm(
            provider='openai',
            model_name='gpt-4o-mini',
            temperature=0.7,
            max_tokens=1000,  # Suficiente para prompts largos
            fallback=False  # No hacer fallback aquí, lo manejamos arriba
        )
        
        # Crear prompt para el LLM remixer
        remix_prompt = f"""Eres un experto en optimización de prompts para generación de contenido con IA (videos, imágenes).

Tu tarea es combinar un template de prompt con el prompt del usuario para crear un prompt final optimizado y listo para usar.

Template de prompt:
{template_text}

Prompt del usuario:
{user_prompt}

Instrucciones:
1. **IDIOMA CONSISTENTE**: Detecta el idioma del prompt del usuario. Todo el prompt final debe estar en el MISMO idioma. Si el usuario escribe en español, traduce el template completo al español. Si escribe en inglés, mantén todo en inglés. Si es otro idioma, traduce todo a ese idioma.

2. Si el template tiene variables como {{variable}}, rellénalas basándote en el prompt del usuario y contexto apropiado. Usa valores creativos y descriptivos si el usuario no especifica algo.

3. Si el template no tiene variables, combina ambos de forma natural y coherente, manteniendo el estilo del template pero en el idioma del usuario.

4. Mejora y expande el prompt final para que sea más descriptivo, específico y efectivo para generación de contenido.

5. Mantén el estilo, tono y estructura del template original, pero traducido al idioma del usuario.

6. El prompt final debe ser claro, específico y optimizado para el servicio de IA que lo recibirá.

7. **EVITAR CONTENIDO SENSIBLE**: Reformula cualquier referencia a:
   - Nombres de personas famosas o reales (usa descripciones genéricas: "un hombre", "una mujer", "una persona")
   - Marcas comerciales específicas (usa términos genéricos: "coche deportivo" en lugar de marca específica)
   - Contenido violento, sexual o controversial
   - Referencias políticas o religiosas específicas
   Usa términos artísticos, técnicos y descriptivos en su lugar.

8. NO añadas explicaciones, comentarios ni texto adicional. Solo genera el prompt final.

IMPORTANTE: 
- Responde ÚNICAMENTE con el prompt final optimizado, sin prefijos como "Prompt final:" o explicaciones.
- TODO el prompt debe estar en el mismo idioma que el prompt del usuario.
- El prompt debe ser seguro y apropiado para servicios de IA de Google (evita contenido sensible)."""

        # Invocar LLM
        response = llm.invoke(remix_prompt)
        
        # Extraer contenido de la respuesta
        if hasattr(response, 'content'):
            final_prompt = response.content.strip()
        else:
            final_prompt = str(response).strip()
        
        # Limpiar respuesta: eliminar prefijos comunes que el LLM podría añadir
        prefixes_to_remove = [
            "Prompt final:",
            "Prompt optimizado:",
            "Aquí está el prompt:",
            "Prompt:",
        ]
        for prefix in prefixes_to_remove:
            if final_prompt.startswith(prefix):
                final_prompt = final_prompt[len(prefix):].strip()
        
        # Validar que no esté vacío
        if not final_prompt:
            raise ValueError("LLM retornó prompt vacío")
        
        logger.debug(f"LLM remix completado. Longitud: {len(final_prompt)} caracteres")
        logger.info(f"📊 Estadísticas: Template={len(template_text)} chars, User={len(user_prompt)} chars, Final={len(final_prompt)} chars")
        
        return final_prompt
        
    except Exception as e:
        logger.error(f"Error en LLM remix: {e}", exc_info=True)
        raise


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

