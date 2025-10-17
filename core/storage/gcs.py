"""Google Cloud Storage Manager"""
from google.cloud import storage
from django.conf import settings
import logging
import requests
import os

logger = logging.getLogger(__name__)


class GCSStorageManager:
    """Gestor para Google Cloud Storage"""
    
    def __init__(self):
        self._client = None
        self._bucket = None
    
    @property
    def client(self):
        """Lazy initialization del cliente de GCS"""
        if self._client is None:
            self._client = storage.Client(project=settings.GCS_PROJECT_ID)
        return self._client
    
    @property
    def bucket(self):
        """Lazy initialization del bucket de GCS"""
        if self._bucket is None:
            self._bucket = self.client.bucket(settings.GCS_BUCKET_NAME)
        return self._bucket
    
    def copy_from_gcs(self, source_gcs_uri: str, destination_path: str) -> str:
        """
        Copia un archivo desde otro bucket de GCS a nuestro bucket
        
        Args:
            source_gcs_uri: URI de GCS completa (gs://bucket/path)
            destination_path: Path destino en nuestro bucket
        
        Returns:
            URI completa del archivo copiado
        """
        try:
            # Parsear la URI de origen: gs://bucket_name/path/to/file
            source_parts = source_gcs_uri.replace('gs://', '').split('/', 1)
            source_bucket_name = source_parts[0]
            source_blob_name = source_parts[1] if len(source_parts) > 1 else ''
            
            logger.info(f"[GCS] Copiando desde: {source_gcs_uri}")
            logger.info(f"[GCS] Bucket origen: {source_bucket_name}, Path: {source_blob_name}")
            
            # Obtener el blob de origen
            source_bucket = self.client.bucket(source_bucket_name)
            source_blob = source_bucket.blob(source_blob_name)
            
            # Copiar al bucket destino
            destination_bucket = self.bucket
            destination_blob = destination_bucket.blob(destination_path)
            
            logger.info(f"[GCS] Copiando a: {destination_path}")
            
            # Realizar la copia
            rewrite_token = None
            while True:
                rewrite_token, bytes_rewritten, bytes_to_rewrite = destination_blob.rewrite(
                    source_blob, token=rewrite_token
                )
                if rewrite_token is None:
                    break
            
            gcs_path = f"gs://{settings.GCS_BUCKET_NAME}/{destination_path}"
            logger.info(f"[GCS] ✅ Archivo copiado exitosamente: {gcs_path}")
            return gcs_path
            
        except Exception as e:
            logger.error(f"[GCS] ❌ Error al copiar archivo: {str(e)}")
            raise
    
    def upload_from_url(self, url: str, destination_path: str) -> str:
        """Descarga un archivo desde URL y lo sube a GCS"""
        try:
            logger.info(f"[GCS] Descargando archivo desde: {url}")
            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()
            
            content_length = len(response.content)
            logger.info(f"[GCS] Archivo descargado: {content_length / (1024*1024):.2f} MB")
            
            blob = self.bucket.blob(destination_path)
            logger.info(f"[GCS] Subiendo a: {destination_path}")
            
            blob.upload_from_string(
                response.content,
                content_type=response.headers.get('content-type', 'video/mp4')
            )
            
            gcs_path = f"gs://{settings.GCS_BUCKET_NAME}/{destination_path}"
            logger.info(f"[GCS] ✅ Archivo subido exitosamente: {gcs_path}")
            return gcs_path
            
        except Exception as e:
            logger.error(f"[GCS] ❌ Error al subir archivo: {str(e)}")
            raise
    
    def upload_file(self, local_path: str, destination_path: str) -> str:
        """Sube un archivo local a GCS"""
        try:
            blob = self.bucket.blob(destination_path)
            blob.upload_from_filename(local_path)
            
            gcs_path = f"gs://{settings.GCS_BUCKET_NAME}/{destination_path}"
            logger.info(f"[GCS] Subido a {gcs_path}")
            return gcs_path
            
        except Exception as e:
            logger.error(f"[GCS] Error: {str(e)}")
            raise
    
    def upload_from_bytes(self, file_content: bytes, destination_path: str, content_type: str = 'image/jpeg') -> str:
        """Sube contenido desde bytes a GCS"""
        try:
            logger.info(f"[GCS] Subiendo {len(file_content)} bytes a: {destination_path}")
            
            blob = self.bucket.blob(destination_path)
            blob.upload_from_string(file_content, content_type=content_type)
            
            gcs_path = f"gs://{settings.GCS_BUCKET_NAME}/{destination_path}"
            logger.info(f"[GCS] ✅ Subido exitosamente: {gcs_path}")
            return gcs_path
            
        except Exception as e:
            logger.error(f"[GCS] ❌ Error: {str(e)}")
            raise
    
    def upload_base64(self, base64_string: str, destination_path: str, content_type: str = 'video/mp4') -> str:
        """Sube contenido desde string base64 a GCS"""
        try:
            import base64
            
            logger.info(f"[GCS] Decodificando base64 y subiendo a: {destination_path}")
            
            # Decodificar base64
            file_content = base64.b64decode(base64_string)
            
            return self.upload_from_bytes(file_content, destination_path, content_type)
            
        except Exception as e:
            logger.error(f"[GCS] ❌ Error al subir base64: {str(e)}")
            raise
    
    def upload_django_file(self, django_file, destination_path: str) -> str:
        """Sube un archivo de Django (UploadedFile) a GCS"""
        try:
            logger.info(f"[GCS] Subiendo archivo Django: {django_file.name} ({django_file.size} bytes)")
            
            # Leer contenido del archivo
            file_content = django_file.read()
            content_type = django_file.content_type or 'application/octet-stream'
            
            return self.upload_from_bytes(file_content, destination_path, content_type)
            
        except Exception as e:
            logger.error(f"[GCS] ❌ Error al subir archivo Django: {str(e)}")
            raise
    
    def get_signed_url(self, gcs_path: str, expiration: int = 3600) -> str:
        """Genera URL firmada para acceder a un archivo"""
        try:
            blob_name = gcs_path.replace(f"gs://{settings.GCS_BUCKET_NAME}/", "")
            blob = self.bucket.blob(blob_name)
            
            url = blob.generate_signed_url(
                version="v4",
                expiration=expiration,
                method="GET"
            )
            return url
            
        except Exception as e:
            logger.error(f"Error al generar URL: {str(e)}")
            raise
    
    def delete_file(self, gcs_path: str) -> bool:
        """Elimina un archivo de GCS"""
        try:
            blob_name = gcs_path.replace(f"gs://{settings.GCS_BUCKET_NAME}/", "")
            blob = self.bucket.blob(blob_name)
            blob.delete()
            
            logger.info(f"Eliminado: {gcs_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error al eliminar: {str(e)}")
            return False
    
    def file_exists(self, gcs_path: str) -> bool:
        """Verifica si existe un archivo"""
        try:
            blob_name = gcs_path.replace(f"gs://{settings.GCS_BUCKET_NAME}/", "")
            blob = self.bucket.blob(blob_name)
            return blob.exists()
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return False


# Instancia global
gcs_storage = GCSStorageManager()

