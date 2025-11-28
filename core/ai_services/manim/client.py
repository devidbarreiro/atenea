"""
Cliente Manim para generar videos animados
Soporta múltiples tipos de animaciones mediante sistema de registro
"""
import logging
import subprocess
import os
import sys
import base64
from pathlib import Path
from typing import Dict, Optional, Any

# Importar animaciones para que se registren automáticamente
from . import animations  # noqa: F401
from .registry import AnimationRegistry

logger = logging.getLogger(__name__)


class ManimClient:
    """
    Cliente para generar videos usando Manim
    
    Soporta múltiples tipos de animaciones mediante sistema de registro.
    Cada tipo de animación debe estar registrado en AnimationRegistry.
    """
    
    def __init__(self):
        """Inicializa el cliente Manim"""
        # El script principal está en el módulo animations
        # Necesitamos un archivo que pueda ser ejecutado por Manim
        # Usaremos un archivo wrapper que importa y ejecuta la animación correcta
        self.module_path = Path(__file__).parent
        self.script_path = self.module_path / "render_wrapper.py"
        
        # Asegurar que el wrapper existe
        self._ensure_render_wrapper()
    
    def _ensure_render_wrapper(self):
        """Crea el archivo wrapper si no existe"""
        if not self.script_path.exists():
            wrapper_content = '''"""
Wrapper para ejecutar animaciones Manim
Este archivo es generado automáticamente y permite ejecutar cualquier animación registrada
"""
import os
import sys
from pathlib import Path

# Añadir el directorio del proyecto al path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Importar Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'atenea.settings')
import django
django.setup()

# Importar animaciones para que se registren
from core.ai_services.manim import animations  # noqa: F401
from core.ai_services.manim.registry import AnimationRegistry
from manim import *

# Obtener el tipo de animación desde variable de entorno
animation_type = os.environ.get('MANIM_ANIMATION_TYPE', 'quote')
animation_class = AnimationRegistry.get(animation_type)

if not animation_class:
    raise ValueError(f"Tipo de animación '{animation_type}' no encontrado. "
                     f"Tipos disponibles: {AnimationRegistry.list_types()}")

# Crear y ejecutar la animación
scene = animation_class()
scene.render()
'''
            self.script_path.write_text(wrapper_content)
    
    def generate_video(
        self,
        animation_type: str,
        config: Dict[str, Any],
        quality: str = "k",
        scene_name: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Genera un video usando Manim con el tipo de animación especificado
        
        Args:
            animation_type: Tipo de animación (ej: 'quote', 'bar_chart', 'histogram')
            config: Configuración específica del tipo de animación
            quality: Calidad de renderizado (l/m/h/k, default: k)
            scene_name: Nombre de la escena (opcional, usa el nombre de la clase por defecto)
        
        Returns:
            Dict con 'video_path' (ruta local del video generado)
        
        Raises:
            ValueError: Si el tipo de animación no está registrado
            Exception: Si falla la generación
        """
        # Verificar que el tipo de animación esté registrado
        if not AnimationRegistry.is_registered(animation_type):
            available = AnimationRegistry.list_types()
            raise ValueError(
                f"Tipo de animación '{animation_type}' no está registrado. "
                f"Tipos disponibles: {available}"
            )
        
        # Configurar variables de entorno para la animación
        self._set_animation_config(animation_type, config)
        
        # Log de depuración (solo en desarrollo)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Configuración para animación '{animation_type}':")
            for key, value in config.items():
                if isinstance(value, str) and len(value) > 50:
                    logger.debug(f"  {key}: {value[:50]}...")
                else:
                    logger.debug(f"  {key}: {value}")
        
        # Determinar Python a usar
        python_cmd = sys.executable
        
        # Determinar directorio raíz del proyecto
        project_root = self.module_path.parent.parent.parent
        
        # Nombre de la escena (por defecto usa el nombre de la clase)
        if not scene_name:
            animation_class = AnimationRegistry.get(animation_type)
            scene_name = animation_class.__name__
        
        # Renderizar usando Manim
        # No usar -p para evitar preview (que causa errores en servidores sin interfaz gráfica)
        cmd = [
            python_cmd,
            "-m", "manim",
            f"-q{quality}",  # Quality: -ql, -qm, -qh, -qk
            str(self.script_path.absolute()),
            scene_name
        ]
        
        logger.info(f"Renderizando video tipo '{animation_type}' con Manim...")
        logger.info(f"Comando: {' '.join(cmd)}")
        logger.info(f"Directorio de trabajo: {project_root}")
        
        result = subprocess.run(
            cmd,
            cwd=str(project_root),
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
        
        # Manim genera videos en media/videos/{script_name}/{quality}/{scene_name}.mp4
        # El script_name es el nombre del archivo sin extensión
        script_name = self.script_path.stem  # "render_wrapper"
        video_path = project_root / "media" / "videos" / script_name / quality_folder / f"{scene_name}.mp4"
        
        # Si no se encuentra, intentar buscar en otras ubicaciones posibles
        # (por compatibilidad con código antiguo que usaba create_quote.py)
        if not video_path.exists():
            # Intentar con el nombre del módulo de animaciones
            alternative_paths = [
                project_root / "media" / "videos" / "manim" / quality_folder / f"{scene_name}.mp4",
                project_root / "media" / "videos" / "create_quote" / quality_folder / f"{scene_name}.mp4",
            ]
            
            for alt_path in alternative_paths:
                if alt_path.exists():
                    logger.info(f"Video encontrado en ubicación alternativa: {alt_path}")
                    video_path = alt_path
                    break
            else:
                # Si aún no se encuentra, buscar recursivamente en media/videos
                videos_dir = project_root / "media" / "videos"
                if videos_dir.exists():
                    found_video = None
                    for root, dirs, files in os.walk(videos_dir):
                        for file in files:
                            if file == f"{scene_name}.mp4":
                                found_video = Path(root) / file
                                break
                        if found_video:
                            break
                    
                    if found_video:
                        logger.info(f"Video encontrado mediante búsqueda recursiva: {found_video}")
                        video_path = found_video
                    else:
                        raise Exception(
                            f"Video generado no encontrado. Buscado en:\n"
                            f"  - {video_path}\n"
                            f"  - {alternative_paths[0]}\n"
                            f"  - {alternative_paths[1]}\n"
                            f"  - Búsqueda recursiva en {videos_dir}"
                        )
                else:
                    raise Exception(f"Video generado no encontrado en {video_path}")
        
        logger.info(f"✅ Video generado exitosamente: {video_path}")
        
        return {
            'video_path': str(video_path)
        }
    
    def _set_animation_config(self, animation_type: str, config: Dict[str, Any]):
        """
        Configura las variables de entorno para la animación
        
        Args:
            animation_type: Tipo de animación
            config: Configuración específica
        """
        # Establecer el tipo de animación
        os.environ['MANIM_ANIMATION_TYPE'] = animation_type
        
        # Configurar variables específicas según el tipo
        prefix = f'{animation_type.upper()}_ANIMATION'
        
        # Mapeo de nombres de configuración a nombres de variables de entorno
        # Esto permite usar nombres más naturales en config
        key_mapping = {
            'quote': {
                'text': 'TEXT',
                'author': 'AUTHOR',
                'duration': 'DURATION',
                'container_color': 'CONTAINER_COLOR',
                'text_color': 'TEXT_COLOR',
                'font_family': 'FONT_FAMILY',
            }
        }
        
        mapping = key_mapping.get(animation_type, {})
        
        for key, value in config.items():
            # Usar el mapeo si existe, sino usar el key directamente en mayúsculas
            env_key_suffix = mapping.get(key, key.upper())
            env_key = f'{prefix}_{env_key_suffix}'
            
            # Para duración, siempre establecerla (incluso si es None) para que la animación pueda calcularla automáticamente
            if key == 'duration':
                if value is None:
                    os.environ[env_key] = "None"
                else:
                    os.environ[env_key] = str(value)
            # Para otros valores None, omitirlos
            elif value is None:
                continue
            # Codificar strings en base64 para preservar caracteres especiales
            elif isinstance(value, str):
                encoded = base64.b64encode(value.encode('utf-8')).decode('ascii')
                os.environ[env_key] = encoded
                os.environ[f'{env_key}_ENCODED'] = '1'
            else:
                os.environ[env_key] = str(value)
    
    # Métodos de conveniencia para tipos específicos (mantener compatibilidad)
    
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
        Genera un video de cita usando Manim (método de conveniencia)
        
        Args:
            quote: Texto de la cita
            author: Nombre del autor (opcional)
            duration: Duración en segundos (opcional)
            quality: Calidad de renderizado (l/m/h/k, default: k)
            container_color: Color del contenedor en formato hex
            text_color: Color del texto en formato hex
            font_family: Tipo de fuente (normal/bold/italic/bold_italic)
        
        Returns:
            Dict con 'video_path'
        """
        if not quote or not quote.strip():
            raise ValueError("El texto de la cita es requerido")
        
        # Establecer variables de entorno directamente (como funcionaba antes)
        # Codificar en base64 para preservar caracteres especiales
        quote_encoded = base64.b64encode(quote.encode('utf-8')).decode('ascii')
        os.environ['QUOTE_ANIMATION_TEXT'] = quote_encoded
        os.environ['QUOTE_ANIMATION_TEXT_ENCODED'] = '1'
        
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
        
        # Establecer el tipo de animación para el wrapper
        os.environ['MANIM_ANIMATION_TYPE'] = 'quote'
        
        # Determinar Python a usar
        python_cmd = sys.executable
        
        # Determinar directorio raíz del proyecto
        project_root = self.module_path.parent.parent.parent
        
        # Limpiar caché de Manim antes de generar para forzar regeneración
        # Esto evita que use videos anteriores con diferentes parámetros
        self._clean_manim_cache(project_root, quality)
        
        # Renderizar usando Manim
        # No usar -p para evitar preview (que causa errores en servidores sin interfaz gráfica)
        # Usar --disable_caching para forzar regeneración completa
        # Formato: -ql, -qm, -qh, -qk (sin -p significa no preview)
        cmd = [
            python_cmd,
            "-m", "manim",
            f"-q{quality}",  # Quality: -ql, -qm, -qh, -qk
            "--disable_caching",  # Forzar regeneración completa
            str(self.script_path.absolute()),
            "QuoteAnimation"
        ]
        
        logger.info(f"Renderizando video de cita con Manim...")
        logger.info(f"Comando: {' '.join(cmd)}")
        logger.info(f"Directorio de trabajo: {project_root}")
        logger.info(f"Quote: {quote[:50]}...")
        logger.info(f"Author: {author}")
        logger.info(f"Duration: {duration}")
        logger.info(f"Container color: {container_color or '#0066CC'}")
        logger.info(f"Text color: {text_color or '#FFFFFF'}")
        logger.info(f"Font family: {font_family or 'normal'}")
        logger.info(f"Quality: {quality}")
        
        # Verificar variables de entorno antes de ejecutar
        logger.info(f"Variables de entorno configuradas:")
        logger.info(f"  QUOTE_ANIMATION_TEXT_ENCODED: {os.environ.get('QUOTE_ANIMATION_TEXT_ENCODED', 'NO SET')}")
        logger.info(f"  QUOTE_ANIMATION_AUTHOR: {os.environ.get('QUOTE_ANIMATION_AUTHOR', 'NO SET')[:50] if os.environ.get('QUOTE_ANIMATION_AUTHOR') else 'NO SET'}")
        logger.info(f"  QUOTE_ANIMATION_DURATION: {os.environ.get('QUOTE_ANIMATION_DURATION', 'NO SET')}")
        logger.info(f"  QUOTE_ANIMATION_CONTAINER_COLOR: {os.environ.get('QUOTE_ANIMATION_CONTAINER_COLOR', 'NO SET')}")
        logger.info(f"  QUOTE_ANIMATION_TEXT_COLOR: {os.environ.get('QUOTE_ANIMATION_TEXT_COLOR', 'NO SET')}")
        logger.info(f"  QUOTE_ANIMATION_FONT_FAMILY: {os.environ.get('QUOTE_ANIMATION_FONT_FAMILY', 'NO SET')}")
        logger.info(f"  MANIM_ANIMATION_TYPE: {os.environ.get('MANIM_ANIMATION_TYPE', 'NO SET')}")
        
        result = subprocess.run(
            cmd,
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutos máximo
            env=os.environ.copy()  # Asegurar que las variables de entorno se pasen al proceso hijo
        )
        
        # Log detallado de la salida
        if result.stdout:
            logger.info(f"Salida de Manim (stdout):\n{result.stdout[:1000]}")  # Primeros 1000 caracteres
        if result.stderr:
            logger.warning(f"Salida de Manim (stderr):\n{result.stderr[:1000]}")  # Primeros 1000 caracteres
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Error desconocido"
            logger.error(f"Error al renderizar con Manim (código {result.returncode}): {error_msg}")
            raise Exception(f"Error al renderizar video: {error_msg}")
        
        # Determinar ruta del video generado
        quality_folder = {
            "l": "480p15",
            "m": "720p30",
            "h": "1080p60",
            "k": "2160p60"
        }.get(quality, "2160p60")
        
        # Buscar el video en múltiples ubicaciones posibles
        script_name = self.script_path.stem  # "render_wrapper"
        video_path = project_root / "media" / "videos" / script_name / quality_folder / "QuoteAnimation.mp4"
        
        # Si no se encuentra, intentar buscar en otras ubicaciones
        if not video_path.exists():
            alternative_paths = [
                project_root / "media" / "videos" / "manim" / quality_folder / "QuoteAnimation.mp4",
                project_root / "media" / "videos" / "create_quote" / quality_folder / "QuoteAnimation.mp4",
            ]
            
            for alt_path in alternative_paths:
                if alt_path.exists():
                    logger.info(f"Video encontrado en ubicación alternativa: {alt_path}")
                    video_path = alt_path
                    break
            else:
                # Búsqueda recursiva como último recurso
                videos_dir = project_root / "media" / "videos"
                if videos_dir.exists():
                    found_video = None
                    for root, dirs, files in os.walk(videos_dir):
                        for file in files:
                            if file == "QuoteAnimation.mp4":
                                found_video = Path(root) / file
                                break
                        if found_video:
                            break
                    
                    if found_video:
                        logger.info(f"Video encontrado mediante búsqueda recursiva: {found_video}")
                        video_path = found_video
                    else:
                        raise Exception(
                            f"Video generado no encontrado. Buscado en:\n"
                            f"  - {video_path}\n"
                            f"  - {alternative_paths[0]}\n"
                            f"  - {alternative_paths[1]}\n"
                            f"  - Búsqueda recursiva en {videos_dir}"
                        )
                else:
                    raise Exception(f"Video generado no encontrado en {video_path}")
        
        logger.info(f"✅ Video generado exitosamente: {video_path}")
        
        return {
            'video_path': str(video_path)
        }


    def _clean_manim_cache(self, project_root: Path, quality: str):
        """
        Limpia el caché de Manim para forzar regeneración completa
        
        Args:
            project_root: Directorio raíz del proyecto
            quality: Calidad del video (l/m/h/k)
        """
        try:
            quality_folder = {
                "l": "480p15",
                "m": "720p30",
                "h": "1080p60",
                "k": "2160p60"
            }.get(quality, "2160p60")
            
            # Limpiar archivos de video anteriores
            cache_paths = [
                project_root / "media" / "videos" / "render_wrapper" / quality_folder,
                project_root / "media" / "videos" / "manim" / quality_folder,
                project_root / "media" / "videos" / "create_quote" / quality_folder,
            ]
            
            for cache_path in cache_paths:
                if cache_path.exists():
                    # Eliminar archivos parciales y el video final si existe
                    try:
                        import shutil
                        if (cache_path / "QuoteAnimation.mp4").exists():
                            (cache_path / "QuoteAnimation.mp4").unlink()
                            logger.info(f"Eliminado video anterior: {cache_path / 'QuoteAnimation.mp4'}")
                        
                        # Eliminar carpeta de archivos parciales si existe
                        partial_dir = cache_path / "partial_movie_files" / "QuoteAnimation"
                        if partial_dir.exists():
                            shutil.rmtree(partial_dir)
                            logger.info(f"Eliminada carpeta de archivos parciales: {partial_dir}")
                    except Exception as e:
                        logger.warning(f"No se pudo limpiar caché en {cache_path}: {e}")
            
            # Limpiar caché de texto SVG de Manim (usado para generar hash del texto)
            # Esto fuerza la regeneración del texto con nuevos parámetros
            text_cache_dir = project_root / "media" / "text"
            if text_cache_dir.exists():
                try:
                    import shutil
                    # Eliminar todos los archivos SVG del caché de texto
                    for svg_file in text_cache_dir.glob("*.svg"):
                        svg_file.unlink()
                    logger.info(f"Limpiado caché de texto SVG en: {text_cache_dir}")
                except Exception as e:
                    logger.warning(f"No se pudo limpiar caché de texto: {e}")
                    
        except Exception as e:
            logger.warning(f"Error al limpiar caché de Manim: {e}")
            # No fallar si no se puede limpiar el caché
