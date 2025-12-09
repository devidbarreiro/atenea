from rembg import remove, new_session
from io import BytesIO

# Configuración ULTRA CALIDAD (BiRefNet):
# Inicializamos la sesión fuera de la función para que el modelo 
# se cargue solo una vez en memoria al iniciar la aplicación,
# mejorando drásticamente el rendimiento en peticiones sucesivas.
try:
    # Nota: Asegúrate de tener instalado rembg[gpu] si tienes tarjeta gráfica
    # para acelerar el proceso.
    bg_session = new_session("birefnet-general")
except Exception as e:
    print(f"Error cargando modelo BiRefNet, asegúrate de tener rembg actualizado: {e}")
    bg_session = None

def process_remove_background(input_bytes: bytes) -> bytes:
    """
    Toma los bytes de una imagen, elimina el fondo con configuración de alta fidelidad
    y retorna los bytes de la nueva imagen en formato PNG.
    """
    if bg_session is None:
        raise RuntimeError("El modelo de eliminación de fondo no se pudo cargar.")

    # Configuración "RAW / LOSSLESS" (Máxima fidelidad):
    output_bytes = remove(
        input_bytes,
        session=bg_session,
        alpha_matting=True,
        
        # Umbrales EXTREMOS para BiRefNet
        alpha_matting_foreground_threshold=250,
        alpha_matting_background_threshold=5,
        
        # Erode size 0: Conserva el 100% de los píxeles originales del borde (pelos, humo).
        alpha_matting_erode_size=0,
        
        # Resolución masiva para el refinado de bordes
        alpha_matting_base_size=4096,
        
        # Sin post-proceso para evitar borrar detalles finos por error
        post_process_mask=False
    )
    
    return output_bytes