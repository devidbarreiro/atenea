"""
Comando para limpiar el bucket de GCS de archivos de pruebas
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from google.cloud import storage
import os


class Command(BaseCommand):
    help = 'Limpiar bucket de GCS (imágenes, videos, audios de pruebas)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar qué se borraría sin borrar realmente',
        )
        parser.add_argument(
            '--folders',
            nargs='+',
            default=['images', 'videos', 'audios', 'projects'],
            help='Carpetas a limpiar (default: images, videos, audios, projects)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        folders = options['folders']
        
        if not settings.GCS_BUCKET_NAME:
            self.stdout.write(self.style.ERROR('GCS_BUCKET_NAME no configurado'))
            return
        
        self.stdout.write(f'🧹 Limpiando bucket: {settings.GCS_BUCKET_NAME}')
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  DRY RUN - No se borrará nada'))
        
        try:
            # Inicializar cliente de GCS usando credenciales de aplicación por defecto
            # Esto usa las credenciales de gcloud auth application-default login
            import os
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.expanduser('~/.config/gcloud/application_default_credentials.json')
            
            project_id = getattr(settings, 'GCS_PROJECT_ID', None)
            client = storage.Client(project=project_id)
            bucket = client.bucket(settings.GCS_BUCKET_NAME)
            
            total_deleted = 0
            
            for folder in folders:
                self.stdout.write(f'\n📁 Procesando carpeta: {folder}/')
                
                # Listar todos los blobs en la carpeta
                blobs = bucket.list_blobs(prefix=f'{folder}/')
                blob_list = list(blobs)
                
                if not blob_list:
                    self.stdout.write(f'  ✓ Carpeta vacía o no existe')
                    continue
                
                self.stdout.write(f'  Encontrados {len(blob_list)} archivos')
                
                if not dry_run:
                    # Borrar todos los blobs
                    for blob in blob_list:
                        blob.delete()
                        total_deleted += 1
                        if total_deleted % 10 == 0:
                            self.stdout.write(f'  ... {total_deleted} archivos borrados')
                    
                    self.stdout.write(self.style.SUCCESS(f'  ✓ {len(blob_list)} archivos borrados'))
                else:
                    # Solo mostrar
                    for blob in blob_list[:10]:  # Mostrar solo los primeros 10
                        self.stdout.write(f'    - {blob.name}')
                    if len(blob_list) > 10:
                        self.stdout.write(f'    ... y {len(blob_list) - 10} más')
                    total_deleted += len(blob_list)
            
            self.stdout.write(f'\n✅ Total: {total_deleted} archivos {"serían borrados" if dry_run else "borrados"}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))
            import traceback
            traceback.print_exc()

