"""
Comando de Django para probar el encolado de imágenes
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Image, Project
from core.services import ImageService


class Command(BaseCommand):
    help = 'Prueba el encolado de una imagen'

    def add_arguments(self, parser):
        parser.add_argument(
            '--prompt',
            type=str,
            default='Un gato astronauta',
            help='Prompt para la imagen'
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='ID del usuario (por defecto usa el primer usuario)'
        )

    def handle(self, *args, **options):
        prompt = options['prompt']
        user_id = options.get('user_id')
        
        # Obtener usuario
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Usuario con ID {user_id} no encontrado'))
                return
        else:
            user = User.objects.first()
            if not user:
                self.stdout.write(self.style.ERROR('No hay usuarios en la base de datos'))
                return
        
        self.stdout.write(f'Usuario: {user.username} (ID: {user.id})')
        
        # Obtener o crear proyecto
        project = Project.objects.filter(created_by=user).first()
        if not project:
            project = Project.objects.create(
                title='Proyecto de Prueba',
                created_by=user
            )
            self.stdout.write(f'Proyecto creado: {project.title} (ID: {project.id})')
        else:
            self.stdout.write(f'Usando proyecto: {project.title} (ID: {project.id})')
        
        # Crear imagen
        image_service = ImageService()
        image = image_service.create_image(
            project=project,
            user=user,
            prompt=prompt,
            config={'model_id': 'gemini-2.5-flash-image'}  # Modelo por defecto
        )
        
        self.stdout.write(f'Imagen creada: {image.title} (ID: {image.id}, UUID: {image.uuid})')
        
        # Encolar generación
        try:
            task = image_service.generate_image_async(image)
            self.stdout.write(self.style.SUCCESS(
                f'✓ Imagen encolada exitosamente\n'
                f'  Task UUID: {task.uuid}\n'
                f'  Task ID: {task.task_id}\n'
                f'  Estado: {task.status}\n'
                f'  Cola: {task.queue_name}\n'
                f'  Prioridad: {task.priority}'
            ))
            self.stdout.write(f'\nEstado de la imagen: {image.status}')
            self.stdout.write(f'\nRevisa los logs del worker de Celery para ver el procesamiento.')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error al encolar: {e}'))
            import traceback
            self.stdout.write(traceback.format_exc())





