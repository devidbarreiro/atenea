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

