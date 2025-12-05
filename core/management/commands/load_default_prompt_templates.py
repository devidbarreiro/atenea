"""
Comando para cargar templates de prompts por defecto desde archivos Markdown
Uso: python manage.py load_default_prompt_templates [--update]
"""
import os
import re
import yaml
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import PromptTemplate
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Carga templates de prompts por defecto desde archivos Markdown'

    def add_arguments(self, parser):
        parser.add_argument(
            '--update',
            action='store_true',
            help='Actualiza templates existentes en lugar de solo crear nuevos'
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Usuario que será el creador de los templates (default: None)'
        )

    def handle(self, *args, **options):
        update = options.get('update', False)
        username = options.get('user')
        
        # Obtener usuario creador (opcional)
        created_by = None
        if username:
            try:
                created_by = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'Usuario "{username}" no encontrado. Usando None como creador.')
                )
        
        # Ruta base de los templates
        base_path = os.path.join(settings.BASE_DIR, 'core', 'prompt_templates', 'default')
        
        if not os.path.exists(base_path):
            self.stdout.write(
                self.style.ERROR(f'Directorio no encontrado: {base_path}')
            )
            return
        
        total_loaded = 0
        total_updated = 0
        total_errors = 0
        
        # Recorrer subdirectorios (video, image, agent)
        for template_type in ['video', 'image', 'agent']:
            type_path = os.path.join(base_path, template_type)
            
            if not os.path.exists(type_path):
                self.stdout.write(
                    self.style.WARNING(f'Directorio no encontrado: {type_path}')
                )
                continue
            
            # Leer todos los archivos Markdown en el directorio
            for filename in os.listdir(type_path):
                if not filename.endswith('.md'):
                    continue
                
                file_path = os.path.join(type_path, filename)
                
                try:
                    template_data = self._parse_markdown_file(file_path)
                    
                    if not template_data:
                        self.stdout.write(
                            self.style.WARNING(f'{file_path}: No se pudo parsear - saltando')
                        )
                        total_errors += 1
                        continue
                    
                    # Procesar el template
                    result = self._load_template(
                        template_data,
                        template_type,
                        created_by,
                        update,
                        file_path
                    )
                    
                    if result == 'created':
                        total_loaded += 1
                    elif result == 'updated':
                        total_updated += 1
                    elif result == 'error':
                        total_errors += 1
                
                except yaml.YAMLError as e:
                    self.stdout.write(
                        self.style.ERROR(f'{file_path}: Error parseando frontmatter YAML - {e}')
                    )
                    total_errors += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'{file_path}: Error inesperado - {e}')
                    )
                    total_errors += 1
        
        # Resumen
        self.stdout.write(self.style.SUCCESS('\n=== Resumen ==='))
        self.stdout.write(f'Templates creados: {total_loaded}')
        self.stdout.write(f'Templates actualizados: {total_updated}')
        self.stdout.write(f'Errores: {total_errors}')
        self.stdout.write(self.style.SUCCESS('✓ Proceso completado'))

    def _parse_markdown_file(self, file_path):
        """
        Parsea un archivo Markdown con frontmatter YAML
        
        Formato esperado:
        ---
        name: Template Name
        description: Description
        recommended_service: sora
        is_public: true
        ---
        
        Prompt text here...
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Buscar frontmatter (entre --- y ---)
            frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
            match = re.match(frontmatter_pattern, content, re.DOTALL)
            
            if not match:
                self.stdout.write(
                    self.style.WARNING(f'{file_path}: No se encontró frontmatter válido')
                )
                return None
            
            frontmatter_text = match.group(1)
            prompt_text = match.group(2).strip()
            
            # Parsear YAML frontmatter
            try:
                frontmatter = yaml.safe_load(frontmatter_text)
            except yaml.YAMLError as e:
                self.stdout.write(
                    self.style.ERROR(f'{file_path}: Error parseando YAML - {e}')
                )
                return None
            
            if not isinstance(frontmatter, dict):
                self.stdout.write(
                    self.style.WARNING(f'{file_path}: Frontmatter debe ser un objeto YAML')
                )
                return None
            
            # Combinar frontmatter con prompt_text
            template_data = frontmatter.copy()
            template_data['prompt_text'] = prompt_text
            
            return template_data
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'{file_path}: Error leyendo archivo - {e}')
            )
            return None

    def _load_template(self, template_data, template_type, created_by, update, file_path):
        """Carga o actualiza un template individual"""
        try:
            # Validar campos requeridos
            name = template_data.get('name')
            prompt_text = template_data.get('prompt_text')
            recommended_service = template_data.get('recommended_service')
            
            if not name or not prompt_text:
                self.stdout.write(
                    self.style.WARNING(
                        f'{file_path}: Template sin nombre o prompt_text - saltando'
                    )
                )
                return 'error'
            
            # Validar longitud del prompt
            if len(prompt_text) > 2000:
                self.stdout.write(
                    self.style.WARNING(
                        f'{file_path}: Template "{name}" excede 2000 caracteres - truncando'
                    )
                )
                prompt_text = prompt_text[:2000]
            
            # Buscar template existente
            # Para templates del sistema (created_by=None), buscar por nombre y tipo
            # Para templates de usuario, buscar por nombre y creador
            if created_by is None:
                template = PromptTemplate.objects.filter(
                    name=name,
                    template_type=template_type,
                    recommended_service=recommended_service,
                    created_by__isnull=True
                ).first()
            else:
                template = PromptTemplate.objects.filter(
                    name=name,
                    template_type=template_type,
                    recommended_service=recommended_service,
                    created_by=created_by
                ).first()
            
            if template:
                if update:
                    # Actualizar template existente
                    template.description = template_data.get('description', template.description)
                    template.prompt_text = prompt_text
                    template.is_public = template_data.get('is_public', True)
                    template.is_active = True
                    if 'preview_url' in template_data:
                        template.preview_url = template_data['preview_url']
                    template.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Actualizado: {name} ({template_type})')
                    )
                    return 'updated'
                else:
                    self.stdout.write(
                        self.style.WARNING(f'  - Ya existe: {name} ({template_type}) - saltando')
                    )
                    return 'skipped'
            else:
                # Crear nuevo template
                template = PromptTemplate.objects.create(
                    name=name,
                    description=template_data.get('description', ''),
                    template_type=template_type,
                    prompt_text=prompt_text,
                    recommended_service=recommended_service,
                    preview_url=template_data.get('preview_url'),
                    created_by=created_by,
                    is_public=template_data.get('is_public', True),
                    is_active=True
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Creado: {name} ({template_type})')
                )
                return 'created'
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  ✗ Error cargando template: {e}')
            )
            return 'error'

