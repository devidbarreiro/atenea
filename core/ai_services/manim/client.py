"""
Cliente Manim para generar videos animados
Soporta múltiples tipos de animaciones mediante sistema de registro

Ejecuta Manim directamente desde Python sin subprocess ni archivos temporales.
Los parámetros se pasan directamente al constructor de la animación (thread-safe).

Soporta múltiples usuarios simultáneos usando paths únicos por request.
"""
import logging
import os
import threading
import shutil
import uuid
from pathlib import Path
from typing import Dict, Optional, Any

# Importar Manim y configurar
from manim import tempconfig

# Importar animaciones para que se registren automáticamente
from . import animations  # noqa: F401
from .registry import AnimationRegistry

logger = logging.getLogger(__name__)

class ManimEnvironmentError(Exception):
    """Excepción para errores de configuración del entorno (dependencias faltantes)"""
    pass

# Lock global para operaciones críticas de Manim (si es necesario)
_manim_lock = threading.Lock()


class ManimClient:
    """
    Cliente para generar videos usando Manim
    
    Soporta múltiples tipos de animaciones mediante sistema de registro.
    Cada tipo de animación debe estar registrado en AnimationRegistry.
    
    Ejecuta Manim directamente desde Python sin necesidad de subprocess.
    """
    
    def __init__(self):
        """Inicializa el cliente Manim"""
        self.module_path = Path(__file__).parent
        self._dependencies_verified = False

    def _verify_dependencies(self):
        """
        Verifica que las dependencias externas (FFmpeg, etc.) estén instaladas
        
        Raises:
            ManimEnvironmentError: Si faltan dependencias críticas
        """
        if self._dependencies_verified:
            return

        dependencies = {
            'ffmpeg': 'Requerido para codificar video y audio.',
            'ffprobe': 'Requerido para analizar archivos multimedia.',
        }
        
        missing = []
        for cmd, reason in dependencies.items():
            if not shutil.which(cmd):
                missing.append(f"- {cmd}: {reason}")
        
        if missing:
            msg = "No se encontraron dependencias críticas de Manim en el sistema:\n" + "\n".join(missing)
            msg += "\n\nPor favor, instala FFmpeg y asegúrate de que esté en tu PATH de Windows."
            msg += "\nDescárgalo de: https://ffmpeg.org/download.html"
            logger.error(msg)
            raise ManimEnvironmentError(msg)
        
        self._dependencies_verified = True
        logger.info("Dependencias de Manim verificadas correctamente.")
    
    def generate_video(
        self,
        animation_type: str,
        config: Dict[str, Any],
        quality: str = "k",
        scene_name: Optional[str] = None,
        unique_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Genera un video usando Manim con el tipo de animación especificado
        
        ... (docstring truncada) ...
        """
        # Verificar dependencias antes de empezar
        self._verify_dependencies()

        # Validar calidad
        valid_qualities = ['l', 'm', 'h', 'k']
        if quality not in valid_qualities:
            raise ValueError(
                f"Calidad inválida: '{quality}'. Debe ser una de: {valid_qualities}"
            )
        
        # Verificar que el tipo de animación esté registrado
        if not AnimationRegistry.is_registered(animation_type):
            available = AnimationRegistry.list_types()
            raise ValueError(
                f"Tipo de animación '{animation_type}' no está registrado. "
                f"Tipos disponibles: {available}"
            )
        
        # Obtener clase de animación
        animation_class = AnimationRegistry.get(animation_type)
        if not animation_class:
            raise ValueError(f"No se pudo obtener la clase de animación para '{animation_type}'")
        
        # Nombre de la escena (por defecto usa el nombre de la clase)
        if not scene_name:
            scene_name = animation_class.__name__
        
        # Generar ID único para este render si no se proporciona
        # Esto evita colisiones cuando múltiples usuarios renderizan simultáneamente
        if not unique_id:
            unique_id = uuid.uuid4().hex[:8]  # 8 caracteres es suficiente
        
        # Determinar directorio raíz del proyecto
        project_root = self.module_path.parent.parent.parent
        
        # Validar que el directorio raíz existe
        if not project_root.exists():
            raise FileNotFoundError(f"Directorio raíz del proyecto no encontrado: {project_root}")
        
        # Mapear calidad corta a nombres de calidad de Manim
        quality_mapping = {
            'l': 'low_quality',        # 480p15
            'm': 'medium_quality',      # 720p30
            'h': 'high_quality',        # 1080p60
            'k': 'fourk_quality',       # 2160p60
        }
        
        manim_quality = quality_mapping.get(quality, 'fourk_quality')
        
        # Configurar paths de salida ÚNICOS por request
        # Usar unique_id para evitar colisiones entre renders simultáneos
        media_dir = project_root / "media" / "videos" / f"{scene_name}_{unique_id}"
        media_dir.mkdir(parents=True, exist_ok=True)
        
        # Log de depuración
        logger.info(f"Renderizando video tipo '{animation_type}' con Manim...")
        logger.info(f"Calidad: {quality} -> {manim_quality}")
        logger.info(f"Directorio de salida único: {media_dir}")
        logger.info(f"ID único del render: {unique_id}")
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Configuración para animación '{animation_type}':")
            for key, value in config.items():
                if isinstance(value, str) and len(value) > 50:
                    logger.debug(f"  {key}: {value[:50]}...")
                else:
                    logger.debug(f"  {key}: {value}")
        
        # Configurar Manim temporalmente para este render
        # tempconfig es thread-safe (usa contextvars internamente)
        # Cada thread/request tiene su propia configuración temporal
        with tempconfig({
            'quality': manim_quality,  # Usar nombre de calidad de Manim
            'media_dir': str(media_dir),
            'preview': False,  # No mostrar preview
            'disable_caching': True,  # Forzar regeneración completa
        }):
            # Crear instancia de la animación con configuración
            # Cada instancia es independiente y thread-safe
            scene = animation_class(config=config)
            
            # Renderizar directamente
            # Manim maneja la concurrencia internamente usando paths únicos
            scene.render()
        
        # Determinar ruta del video generado
        # Manim genera videos en media_dir/{scene_name}/{quality_folder}/{scene_name}.mp4
        quality_folder = {
            "l": "480p15",
            "m": "720p30",
            "h": "1080p60",
            "k": "2160p60"
        }.get(quality, "2160p60")
        
        video_path = media_dir / scene_name / quality_folder / f"{scene_name}.mp4"
        
        # Verificar que el video se generó correctamente
        if not video_path.exists():
            # Buscar recursivamente como fallback
            found_video = None
            for root, dirs, files in os.walk(media_dir):
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
                    f"Video generado no encontrado. Esperado en: {video_path}\n"
                    f"Búsqueda recursiva en: {media_dir}"
                )
        
        logger.info(f"✅ Video generado exitosamente: {video_path}")
        logger.info(f"   Path único: {unique_id}")
        
        return {
            'video_path': str(video_path),
            'unique_id': unique_id  # Devolver también el ID único por si se necesita
        }
    
    # Métodos de conveniencia para tipos específicos (mantener compatibilidad)
    
    def generate_quote_video(
        self,
        quote: str,
        author: Optional[str] = None,
        duration: Optional[float] = None,
        quality: str = "k",
        container_color: Optional[str] = None,
        text_color: Optional[str] = None,
        font_family: Optional[str] = None,
        display_time: Optional[float] = None,
        unique_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Genera un video de cita usando Manim (método de conveniencia)
        
        Args:
            quote: Texto de la cita
            author: Nombre del autor (opcional)
            duration: Duración en segundos (opcional, debe ser positivo)
            quality: Calidad de renderizado (l/m/h/k, default: k)
            container_color: Color del contenedor en formato hex (ej: #0066CC)
            text_color: Color del texto en formato hex (ej: #FFFFFF)
            font_family: Tipo de fuente (normal/bold/italic/bold_italic)
            display_time: Tiempo de visualización en pantalla (segundos)
        
        Returns:
            Dict con 'video_path'
        
        Raises:
            ValueError: Si los parámetros son inválidos
        """
        # Validar quote
        if not quote or not quote.strip():
            raise ValueError("El texto de la cita es requerido")
        
        # Validar calidad
        valid_qualities = ['l', 'm', 'h', 'k']
        if quality not in valid_qualities:
            raise ValueError(f"Calidad inválida: '{quality}'. Debe ser una de: {valid_qualities}")
        
        # Validar duración si se proporciona
        if duration is not None and duration <= 0:
            raise ValueError(f"Duración debe ser positiva, recibido: {duration}")
        
        # Validar colores hex si se proporcionan
        def _is_valid_hex_color(color: str) -> bool:
            """Valida formato de color hex (#RRGGBB)"""
            if not color:
                return False
            if not color.startswith('#'):
                return False
            if len(color) != 7:
                return False
            try:
                int(color[1:], 16)
                return True
            except ValueError:
                return False
        
        if container_color and not _is_valid_hex_color(container_color):
            raise ValueError(f"Color de contenedor inválido: '{container_color}'. Debe ser formato hex (#RRGGBB)")
        
        if text_color and not _is_valid_hex_color(text_color):
            raise ValueError(f"Color de texto inválido: '{text_color}'. Debe ser formato hex (#RRGGBB)")
        
        # Validar font_family
        valid_fonts = ['normal', 'bold', 'italic', 'bold_italic']
        if font_family and font_family not in valid_fonts:
            logger.warning(f"Font family '{font_family}' no reconocido, usando 'normal'")
            font_family = 'normal'
        
        # Crear configuración para pasar a la animación
        config = {
            'text': quote,
            'author': author if author and author.strip() else None,
            'duration': duration,
            'display_time': display_time,
            'container_color': container_color or '#0066CC',
            'text_color': text_color or '#FFFFFF',
            'font_family': font_family or 'normal',
        }
        
        # Usar el método genérico generate_video
        return self.generate_video(
            animation_type='quote',
            config=config,
            quality=quality,
            scene_name='QuoteAnimation',
            unique_id=unique_id
        )


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
