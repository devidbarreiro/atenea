"""Google Cloud Storage Manager"""
from google.cloud import storage
from django.conf import settings
import logging
import requests

logger = logging.getLogger(__name__)


class GCSStorageManager:
    """Gestor para Google Cloud Storage"""
    
    def __init__(self):
        self.client = storage.Client(project=settings.GCS_PROJECT_ID)
        self.bucket = self.client.bucket(settings.GCS_BUCKET_NAME)
    
    def upload_from_url(self, url: str, destination_path: str) -> str:
        """Descarga un archivo desde URL y lo sube a GCS"""
        try:
            logger.info(f"Descargando desde {url}")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            blob = self.bucket.blob(destination_path)
            blob.upload_from_string(
                response.content,
                content_type=response.headers.get('content-type', 'video/mp4')
            )
            
            gcs_path = f"gs://{settings.GCS_BUCKET_NAME}/{destination_path}"
            logger.info(f"Subido a {gcs_path}")
            return gcs_path
            
        except Exception as e:
            logger.error(f"Error al subir: {str(e)}")
            raise
    
    def upload_file(self, local_path: str, destination_path: str) -> str:
        """Sube un archivo local a GCS"""
        try:
            blob = self.bucket.blob(destination_path)
            blob.upload_from_filename(local_path)
            
            gcs_path = f"gs://{settings.GCS_BUCKET_NAME}/{destination_path}"
            logger.info(f"Subido a {gcs_path}")
            return gcs_path
            
        except Exception as e:
            logger.error(f"Error: {str(e)}")
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

