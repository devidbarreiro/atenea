"""
Ejemplos de uso de ffmpeg-python en el proyecto Atenea

ffmpeg-python es un wrapper Pythonic para ffmpeg que permite
procesar videos de manera sencilla y eficiente.
"""

import ffmpeg
import os


# ==============================================================================
# EJEMPLO 1: Información de un video
# ==============================================================================
def get_video_info(input_path):
    """
    Obtiene información básica de un video.
    
    Args:
        input_path: Ruta al archivo de video
        
    Returns:
        dict: Información del video (duración, resolución, codec, etc.)
    """
    try:
        probe = ffmpeg.probe(input_path)
        video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
        
        return {
            'duration': float(probe['format']['duration']),
            'width': int(video_info['width']),
            'height': int(video_info['height']),
            'codec': video_info['codec_name'],
            'fps': eval(video_info['r_frame_rate']),
            'bitrate': int(probe['format']['bit_rate'])
        }
    except ffmpeg.Error as e:
        print(f"Error al obtener info del video: {e.stderr.decode()}")
        return None


# ==============================================================================
# EJEMPLO 2: Convertir formato de video
# ==============================================================================
def convert_video(input_path, output_path, video_codec='libx264', audio_codec='aac'):
    """
    Convierte un video a otro formato.
    
    Args:
        input_path: Ruta al video de entrada
        output_path: Ruta al video de salida
        video_codec: Codec de video (libx264, libx265, etc.)
        audio_codec: Codec de audio (aac, mp3, etc.)
    """
    try:
        (
            ffmpeg
            .input(input_path)
            .output(output_path, vcodec=video_codec, acodec=audio_codec)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        print(f"Video convertido exitosamente: {output_path}")
    except ffmpeg.Error as e:
        print(f"Error al convertir video: {e.stderr.decode()}")


# ==============================================================================
# EJEMPLO 3: Redimensionar video
# ==============================================================================
def resize_video(input_path, output_path, width=1280, height=720):
    """
    Redimensiona un video a una resolución específica.
    
    Args:
        input_path: Ruta al video de entrada
        output_path: Ruta al video de salida
        width: Ancho deseado
        height: Alto deseado
    """
    try:
        (
            ffmpeg
            .input(input_path)
            .filter('scale', width, height)
            .output(output_path)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        print(f"Video redimensionado a {width}x{height}")
    except ffmpeg.Error as e:
        print(f"Error al redimensionar: {e.stderr.decode()}")


# ==============================================================================
# EJEMPLO 4: Extraer audio de un video
# ==============================================================================
def extract_audio(input_path, output_path, audio_codec='mp3'):
    """
    Extrae el audio de un video.
    
    Args:
        input_path: Ruta al video de entrada
        output_path: Ruta al archivo de audio de salida
        audio_codec: Formato del audio (mp3, aac, wav, etc.)
    """
    try:
        (
            ffmpeg
            .input(input_path)
            .output(output_path, acodec=audio_codec, vn=None)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        print(f"Audio extraído: {output_path}")
    except ffmpeg.Error as e:
        print(f"Error al extraer audio: {e.stderr.decode()}")


# ==============================================================================
# EJEMPLO 5: Recortar video (trim)
# ==============================================================================
def trim_video(input_path, output_path, start_time, duration):
    """
    Recorta un video desde un tiempo inicial con una duración específica.
    
    Args:
        input_path: Ruta al video de entrada
        output_path: Ruta al video de salida
        start_time: Tiempo inicial en segundos
        duration: Duración del corte en segundos
    """
    try:
        (
            ffmpeg
            .input(input_path, ss=start_time, t=duration)
            .output(output_path, c='copy')  # c='copy' evita re-encodear
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        print(f"Video recortado: {output_path}")
    except ffmpeg.Error as e:
        print(f"Error al recortar: {e.stderr.decode()}")


# ==============================================================================
# EJEMPLO 6: Agregar marca de agua (watermark)
# ==============================================================================
def add_watermark(input_video, watermark_image, output_path, position='10:10'):
    """
    Agrega una marca de agua a un video.
    
    Args:
        input_video: Ruta al video de entrada
        watermark_image: Ruta a la imagen de marca de agua
        output_path: Ruta al video de salida
        position: Posición de la marca (formato 'x:y')
    """
    try:
        video = ffmpeg.input(input_video)
        watermark = ffmpeg.input(watermark_image)
        
        (
            ffmpeg
            .overlay(video, watermark, x=position.split(':')[0], y=position.split(':')[1])
            .output(output_path)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        print(f"Marca de agua agregada: {output_path}")
    except ffmpeg.Error as e:
        print(f"Error al agregar marca de agua: {e.stderr.decode()}")


# ==============================================================================
# EJEMPLO 7: Comprimir video
# ==============================================================================
def compress_video(input_path, output_path, crf=23):
    """
    Comprime un video usando el parámetro CRF (Constant Rate Factor).
    CRF: 0 (mejor calidad) - 51 (peor calidad). Recomendado: 23 (default)
    
    Args:
        input_path: Ruta al video de entrada
        output_path: Ruta al video de salida
        crf: Factor de calidad (18-28 es un buen rango)
    """
    try:
        (
            ffmpeg
            .input(input_path)
            .output(output_path, vcodec='libx264', crf=crf, preset='medium')
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        print(f"Video comprimido con CRF={crf}")
    except ffmpeg.Error as e:
        print(f"Error al comprimir: {e.stderr.decode()}")


# ==============================================================================
# EJEMPLO 8: Generar thumbnail (miniatura)
# ==============================================================================
def generate_thumbnail(input_path, output_path, time_position='00:00:01'):
    """
    Genera una miniatura (imagen) de un video en un tiempo específico.
    
    Args:
        input_path: Ruta al video de entrada
        output_path: Ruta a la imagen de salida
        time_position: Posición de tiempo (formato HH:MM:SS)
    """
    try:
        (
            ffmpeg
            .input(input_path, ss=time_position)
            .filter('scale', 320, -1)  # -1 mantiene el aspect ratio
            .output(output_path, vframes=1)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        print(f"Thumbnail generado: {output_path}")
    except ffmpeg.Error as e:
        print(f"Error al generar thumbnail: {e.stderr.decode()}")


# ==============================================================================
# EJEMPLO 9: Concatenar videos
# ==============================================================================
def concatenate_videos(video_paths, output_path):
    """
    Concatena múltiples videos en uno solo.
    
    Args:
        video_paths: Lista de rutas a los videos a concatenar
        output_path: Ruta al video de salida
    """
    try:
        # Crear archivo temporal con la lista de videos
        with open('concat_list.txt', 'w') as f:
            for video in video_paths:
                f.write(f"file '{video}'\n")
        
        (
            ffmpeg
            .input('concat_list.txt', format='concat', safe=0)
            .output(output_path, c='copy')
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        
        # Limpiar archivo temporal
        os.remove('concat_list.txt')
        print(f"Videos concatenados: {output_path}")
    except ffmpeg.Error as e:
        print(f"Error al concatenar: {e.stderr.decode()}")


# ==============================================================================
# EJEMPLO 10: Uso en Django - Integración con el proyecto Atenea
# ==============================================================================
def process_uploaded_video(video_file_path):
    """
    Ejemplo de procesamiento de video en Django.
    Podría usarse en core/services.py para procesar videos subidos.
    
    Args:
        video_file_path: Ruta al video subido
        
    Returns:
        dict: Información procesada del video
    """
    import tempfile
    import shutil
    from pathlib import Path
    
    try:
        # Obtener información del video
        info = get_video_info(video_file_path)
        
        if not info:
            return None
        
        # Crear directorio de salida temporal
        output_dir = Path(tempfile.gettempdir()) / 'atenea_processed'
        output_dir.mkdir(exist_ok=True)
        
        # Generar thumbnail
        thumbnail_path = output_dir / f"thumb_{Path(video_file_path).stem}.jpg"
        generate_thumbnail(video_file_path, str(thumbnail_path))
        
        # Comprimir si el video es muy grande (> 100MB)
        file_size_mb = os.path.getsize(video_file_path) / (1024 * 1024)
        compressed_path = None
        
        if file_size_mb > 100:
            compressed_path = output_dir / f"compressed_{Path(video_file_path).name}"
            compress_video(video_file_path, str(compressed_path), crf=28)
        
        return {
            'info': info,
            'thumbnail': str(thumbnail_path),
            'compressed_video': str(compressed_path) if compressed_path else None,
            'original_size_mb': file_size_mb
        }
        
    except Exception as e:
        print(f"Error procesando video: {str(e)}")
        return None


# ==============================================================================
# EJEMPLO DE USO
# ==============================================================================
if __name__ == '__main__':
    # Ejemplo básico de uso
    input_video = "ejemplo.mp4"
    
    if os.path.exists(input_video):
        # Obtener información
        info = get_video_info(input_video)
        print(f"Información del video: {info}")
        
        # Generar thumbnail
        generate_thumbnail(input_video, "thumbnail.jpg")
        
        # Comprimir video
        compress_video(input_video, "comprimido.mp4", crf=28)
    else:
        print("Coloca un video de ejemplo llamado 'ejemplo.mp4' para probar")

