"""
Comando para verificar credenciales de Google Cloud y revisar logs de videos
Uso: python manage.py check_video_credentials [--video-id VIDEO_ID]
"""
import os
import json
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Video
from core.ai_services.gemini_veo import GeminiVeoClient

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Verifica credenciales de Google Cloud y revisa logs de videos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--video-id',
            type=int,
            help='ID del video a revisar',
        )
        parser.add_argument(
            '--test-connection',
            action='store_true',
            help='Probar conexión con Google Cloud',
        )

    def handle(self, *args, **options):
        video_id = options.get('video_id')
        test_connection = options.get('test_connection', False)

        self.stdout.write(self.style.WARNING('=== Verificación de Credenciales ===\n'))

        # Verificar archivo de credenciales
        self.check_credentials_file()

        # Verificar variable de entorno
        self.check_environment_variable()

        # Si se especificó un video, revisar su información
        if video_id:
            self.check_video(video_id)

        # Si se solicita, probar conexión
        if test_connection:
            self.test_google_cloud_connection()

    def check_credentials_file(self):
        """Verifica si el archivo de credenciales existe y es válido"""
        self.stdout.write(self.style.WARNING('1. Verificando archivo de credenciales...'))
        
        creds_path = getattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS', None)
        
        if not creds_path:
            self.stdout.write(self.style.ERROR('   ✗ GOOGLE_APPLICATION_CREDENTIALS no está configurado en settings'))
            return
        
        self.stdout.write(f'   Ruta configurada: {creds_path}')
        
        # Verificar si existe
        if not os.path.exists(creds_path):
            self.stdout.write(self.style.ERROR(f'   ✗ Archivo NO existe: {creds_path}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ Archivo existe: {creds_path}'))
        
        # Verificar permisos
        if not os.access(creds_path, os.R_OK):
            self.stdout.write(self.style.ERROR(f'   ✗ Sin permisos de lectura: {creds_path}'))
            return
        
        self.stdout.write(self.style.SUCCESS('   ✓ Archivo es legible'))
        
        # Verificar que sea JSON válido
        try:
            with open(creds_path, 'r') as f:
                creds_data = json.load(f)
            
            self.stdout.write(self.style.SUCCESS('   ✓ Archivo JSON válido'))
            
            # Mostrar información básica (sin exponer la clave privada)
            project_id = creds_data.get('project_id', 'NO ENCONTRADO')
            client_email = creds_data.get('client_email', 'NO ENCONTRADO')
            
            self.stdout.write(f'   Project ID: {project_id}')
            self.stdout.write(f'   Client Email: {client_email}')
            
            # Verificar campos requeridos
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
            missing_fields = [field for field in required_fields if field not in creds_data]
            
            if missing_fields:
                self.stdout.write(self.style.ERROR(f'   ✗ Campos faltantes: {", ".join(missing_fields)}'))
            else:
                self.stdout.write(self.style.SUCCESS('   ✓ Todos los campos requeridos están presentes'))
                
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'   ✗ JSON inválido: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ✗ Error al leer archivo: {e}'))

    def check_environment_variable(self):
        """Verifica la variable de entorno GOOGLE_APPLICATION_CREDENTIALS"""
        self.stdout.write(self.style.WARNING('\n2. Verificando variable de entorno...'))
        
        env_var = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        
        if not env_var:
            self.stdout.write(self.style.ERROR('   ✗ Variable de entorno GOOGLE_APPLICATION_CREDENTIALS NO está configurada'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ Variable configurada: {env_var}'))
        
        # Verificar que apunte al mismo archivo que settings
        settings_path = getattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS', None)
        if settings_path and os.path.abspath(env_var) != os.path.abspath(settings_path):
            self.stdout.write(self.style.WARNING(
                f'   ⚠ Variable de entorno ({env_var}) y settings ({settings_path}) apuntan a archivos diferentes'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('   ✓ Variable de entorno coincide con settings'))

    def check_video(self, video_id):
        """Revisa información de un video específico"""
        self.stdout.write(self.style.WARNING(f'\n3. Revisando video ID: {video_id}'))
        
        try:
            video = Video.objects.get(id=video_id)
        except Video.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'   ✗ Video {video_id} no encontrado'))
            return
        
        self.stdout.write(f'   Título: {video.title}')
        self.stdout.write(f'   Tipo: {video.type}')
        self.stdout.write(f'   Estado: {video.status}')
        self.stdout.write(f'   Creado: {video.created_at}')
        self.stdout.write(f'   External ID: {video.external_id or "N/A"}')
        
        # Si es un video Veo, mostrar información adicional
        if video.type == 'gemini_veo':
            self.stdout.write(self.style.WARNING('\n   Información específica de Veo:'))
            config = video.config or {}
            model = config.get('veo_model') or config.get('model_id', 'N/A')
            self.stdout.write(f'   Modelo: {model}')
            self.stdout.write(f'   Duración: {config.get("duration", "N/A")}s')
            self.stdout.write(f'   Aspect Ratio: {config.get("aspect_ratio", "N/A")}')
            
            # Verificar si hay error_message
            if hasattr(video, 'error_message') and video.error_message:
                self.stdout.write(self.style.ERROR(f'\n   ✗ Mensaje de error: {video.error_message}'))
            
            # Intentar obtener el cliente y verificar credenciales
            try:
                client = GeminiVeoClient(model_name=model)
                self.stdout.write(self.style.SUCCESS('   ✓ Cliente Veo inicializado correctamente'))
                
                # Intentar obtener un token (esto validará las credenciales)
                try:
                    token = client._get_access_token()
                    if token:
                        self.stdout.write(self.style.SUCCESS('   ✓ Credenciales válidas (token obtenido)'))
                    else:
                        self.stdout.write(self.style.ERROR('   ✗ No se pudo obtener token'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'   ✗ Error al obtener token: {e}'))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ✗ Error al inicializar cliente Veo: {e}'))

    def test_google_cloud_connection(self):
        """Prueba la conexión con Google Cloud"""
        self.stdout.write(self.style.WARNING('\n4. Probando conexión con Google Cloud...'))
        
        try:
            # Intentar inicializar el cliente con un modelo simple
            client = GeminiVeoClient(model_name='veo-2.0-generate-001')
            self.stdout.write(self.style.SUCCESS('   ✓ Cliente inicializado'))
            
            # Intentar obtener un token
            token = client._get_access_token()
            if token:
                self.stdout.write(self.style.SUCCESS('   ✓ Token obtenido exitosamente'))
                self.stdout.write(f'   Token (primeros 20 chars): {token[:20]}...')
            else:
                self.stdout.write(self.style.ERROR('   ✗ No se pudo obtener token'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ✗ Error al probar conexión: {e}'))
            import traceback
            self.stdout.write(self.style.ERROR(f'   Traceback:\n{traceback.format_exc()}'))






