"""
Cliente para generar videos de citas con Manim
"""
import logging
import subprocess
import os
import sys
import base64
from pathlib import Path
from typing import Dict, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class ManimClient:
    """Cliente para generar videos de citas usando Manim"""
    
    def __init__(self):
        """Inicializa el cliente Manim"""
        self.script_path = Path(__file__).parent.parent.parent / "create_quote.py"
        if not self.script_path.exists():
            raise ValueError(f"Script create_quote.py no encontrado en {self.script_path}")
    
    def generate_quote_video(
        self,
        quote: str,
        author: Optional[str] = None,
        duration: Optional[float] = None,
        quality: str = "k",
        container_color: Optional[str] = None,
        text_color: Optional[str] = None,
        font_family: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Genera un video de cita usando Manim
        
        Args:
            quote: Texto de la cita
            author: Nombre del autor (opcional)
            duration: Duración en segundos (opcional, se calcula automáticamente)
            quality: Calidad de renderizado (l/m/h/k, default: k)
            container_color: Color del contenedor en formato hex (ej: #0066CC, default: #0066CC)
            text_color: Color del texto en formato hex (ej: #FFFFFF, default: #FFFFFF)
            font_family: Tipo de fuente (normal/bold/italic/bold_italic, default: normal)
        
        Returns:
            Dict con 'video_path' (ruta local del video generado)
        
        Raises:
            Exception: Si falla la generación
        """
        if not quote or not quote.strip():
            raise ValueError("El texto de la cita es requerido")
        
        # Codificar en base64 para preservar caracteres especiales
        quote_encoded = base64.b64encode(quote.encode('utf-8')).decode('ascii')
        os.environ['QUOTE_ANIMATION_TEXT'] = quote_encoded
        os.environ['QUOTE_ANIMATION_ENCODED'] = '1'
        
        if author and author.strip():
            author_encoded = base64.b64encode(author.encode('utf-8')).decode('ascii')
            os.environ['QUOTE_ANIMATION_AUTHOR'] = author_encoded
            os.environ['QUOTE_ANIMATION_AUTHOR_ENCODED'] = '1'
        else:
            os.environ['QUOTE_ANIMATION_AUTHOR'] = "None"
            os.environ['QUOTE_ANIMATION_AUTHOR_ENCODED'] = '0'
        
        if duration is not None:
            os.environ['QUOTE_ANIMATION_DURATION'] = str(duration)
        else:
            os.environ['QUOTE_ANIMATION_DURATION'] = "None"
        
        # Configurar colores y fuente (valores por defecto si no se especifican)
        os.environ['QUOTE_ANIMATION_CONTAINER_COLOR'] = container_color or '#0066CC'
        os.environ['QUOTE_ANIMATION_TEXT_COLOR'] = text_color or '#FFFFFF'
        os.environ['QUOTE_ANIMATION_FONT_FAMILY'] = font_family or 'normal'
        
        # Determinar Python a usar
        python_cmd = sys.executable
        
        # Renderizar usando Manim
        cmd = [
            python_cmd,
            "-m", "manim",
            f"-pq{quality}",
            str(self.script_path.absolute()),
            "QuoteAnimation"
        ]
        
        logger.info(f"Renderizando video de cita con Manim...")
        logger.info(f"Comando: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutos máximo
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Error desconocido"
            logger.error(f"Error al renderizar con Manim: {error_msg}")
            raise Exception(f"Error al renderizar video: {error_msg}")
        
        # Determinar ruta del video generado
        quality_folder = {
            "l": "480p15",
            "m": "720p30",
            "h": "1080p60",
            "k": "2160p60"
        }.get(quality, "2160p60")
        
        video_path = self.script_path.parent / "media" / "videos" / "create_quote" / quality_folder / "QuoteAnimation.mp4"
        
        if not video_path.exists():
            raise Exception(f"Video generado no encontrado en {video_path}")
        
        logger.info(f"✅ Video generado exitosamente: {video_path}")
        
        return {
            'video_path': str(video_path)
        }

