"""
Class-Based Views refactorizadas para mejor mantenibilidad
"""

from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, View
)
from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.core.paginator import Paginator

from .models import Project, Video, Image, Script, Scene
from .forms import VideoBaseForm, HeyGenAvatarV2Form, HeyGenAvatarIVForm, GeminiVeoVideoForm, SoraVideoForm, GeminiImageForm, ScriptForm
from .services import ProjectService, VideoService, ImageService, APIService, N8nService, SceneService, VideoCompositionService, ValidationException, ServiceException, ImageGenerationException
from django.template.loader import render_to_string
import logging

logger = logging.getLogger(__name__)


# ====================
# MIXINS PERSONALIZADOS
# ====================

class BreadcrumbMixin:
    """Mixin para agregar breadcrumbs al contexto"""
    
    def get_breadcrumbs(self):
        """Override en subclases para definir breadcrumbs"""
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = self.get_breadcrumbs()
        return context


class SuccessMessageMixin:
    """Mixin para mostrar mensaje de éxito"""
    success_message = ''
    
    def form_valid(self, form):
        response = super().form_valid(form)
        if self.success_message:
            messages.success(self.request, self.success_message)
        return response


class ServiceMixin:
    """Mixin para acceso fácil a servicios"""
    
    def get_project_service(self):
        return ProjectService()
    
    def get_video_service(self):
        return VideoService()
    
    def get_image_service(self):
        return ImageService()
    
    def get_api_service(self):
        return APIService()


# ====================
# DASHBOARD
# ====================

class DashboardView(ServiceMixin, ListView):
    """Vista principal del dashboard"""
    model = Project
    template_name = 'dashboard/index.html'
    context_object_name = 'projects'
    paginate_by = 20
    
    def get_queryset(self):
        """Obtener proyectos optimizado"""
        return ProjectService.get_user_projects()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Agregar estadísticas
        context.update({
            'total_videos': Video.objects.count(),
            'total_images': Image.objects.count(),
            'total_scripts': Script.objects.count(),
            'completed_videos': Video.objects.filter(status='completed').count(),
            'processing_videos': Video.objects.filter(status='processing').count(),
            'completed_scripts': Script.objects.filter(status='completed').count(),
        })
        
        # Obtener todos los videos recientes
        videos = Video.objects.select_related('project').order_by('-created_at')[:20]
        video_service = self.get_video_service()
        videos_with_urls = []
        
        for video in videos:
            if video.status == 'completed' and video.gcs_path:
                try:
                    video_data = video_service.get_video_with_signed_urls(video)
                    videos_with_urls.append(video_data)
                except Exception as e:
                    videos_with_urls.append({
                        'video': video,
                        'signed_url': None
                    })
            else:
                videos_with_urls.append({
                    'video': video,
                    'signed_url': None
                })
        
        # Obtener todas las imágenes recientes
        images = Image.objects.select_related('project').order_by('-created_at')[:20]
        image_service = self.get_image_service()
        images_with_urls = []
        
        for image in images:
            if image.status == 'completed' and image.gcs_path:
                try:
                    image_data = image_service.get_image_with_signed_url(image)
                    images_with_urls.append(image_data)
                except Exception as e:
                    images_with_urls.append({
                        'image': image,
                        'signed_url': None
                    })
            else:
                images_with_urls.append({
                    'image': image,
                    'signed_url': None
                })
        
        context['videos'] = videos
        context['videos_with_urls'] = videos_with_urls
        context['images'] = images
        context['images_with_urls'] = images_with_urls
        
        return context


# ====================
# PROJECT VIEWS
# ====================

class ProjectDetailView(BreadcrumbMixin, ServiceMixin, DetailView):
    """Detalle de un proyecto con sus videos"""
    model = Project
    template_name = 'projects/detail.html'
    context_object_name = 'project'
    pk_url_kwarg = 'project_id'
    
    def get_object(self, queryset=None):
        """Obtener proyecto con videos optimizado"""
        project_id = self.kwargs.get('project_id')
        return ProjectService.get_project_with_videos(project_id)
    
    def get_breadcrumbs(self):
        return [
            {'label': self.object.name, 'url': None}
        ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener videos del proyecto
        videos = self.object.videos.select_related('project').order_by('-created_at')
        
        # Generar URLs firmadas para videos completados
        video_service = self.get_video_service()
        videos_with_urls = []
        
        for video in videos:
            if video.status == 'completed' and video.gcs_path:
                try:
                    video_data = video_service.get_video_with_signed_urls(video)
                    videos_with_urls.append(video_data)
                except Exception as e:
                    # Si falla, agregar sin URL firmada
                    videos_with_urls.append({
                        'video': video,
                        'signed_url': None
                    })
            else:
                videos_with_urls.append({
                    'video': video,
                    'signed_url': None
                })
        
        # Obtener imágenes del proyecto
        images = self.object.images.select_related('project').order_by('-created_at')
        
        # Generar URLs firmadas para imágenes completadas
        image_service = self.get_image_service()
        images_with_urls = []
        
        for image in images:
            if image.status == 'completed' and image.gcs_path:
                try:
                    image_data = image_service.get_image_with_signed_url(image)
                    images_with_urls.append(image_data)
                except Exception as e:
                    # Si falla, agregar sin URL firmada
                    images_with_urls.append({
                        'image': image,
                        'signed_url': None
                    })
            else:
                images_with_urls.append({
                    'image': image,
                    'signed_url': None
                })
        
        # Obtener guiones del proyecto
        scripts = self.object.scripts.select_related('project').order_by('-created_at')
        
        context['videos'] = videos
        context['videos_with_urls'] = videos_with_urls
        context['images'] = images
        context['images_with_urls'] = images_with_urls
        context['scripts'] = scripts
        
        return context


class ProjectCreateView(SuccessMessageMixin, BreadcrumbMixin, ServiceMixin, CreateView):
    """Crear nuevo proyecto"""
    model = Project
    fields = ['name']
    template_name = 'projects/create.html'
    success_message = 'Proyecto creado exitosamente'
    
    def get_success_url(self):
        return reverse('core:project_detail', kwargs={'project_id': self.object.pk})
    
    def get_breadcrumbs(self):
        return [
            {'label': 'Nuevo Proyecto', 'url': None}
        ]
    
    def form_valid(self, form):
        """Usar servicio para crear proyecto"""
        try:
            name = form.cleaned_data['name']
            # TODO: Pasar request.user cuando se implemente autenticación
            self.object = ProjectService.create_project(name)
            messages.success(self.request, self.success_message)
            return redirect(self.get_success_url())
        except ValidationException as e:
            form.add_error('name', str(e))
            return self.form_invalid(form)


class ProjectDeleteView(BreadcrumbMixin, ServiceMixin, DeleteView):
    """Eliminar proyecto"""
    model = Project
    template_name = 'projects/delete.html'
    context_object_name = 'project'
    pk_url_kwarg = 'project_id'
    success_url = reverse_lazy('core:dashboard')
    
    def get_breadcrumbs(self):
        return [
            {'label': self.object.name, 'url': reverse('core:project_detail', args=[self.object.pk])},
            {'label': 'Eliminar', 'url': None}
        ]
    
    def delete(self, request, *args, **kwargs):
        """Override para usar ProjectService"""
        self.object = self.get_object()
        success_url = self.get_success_url()
        
        try:
            # Usar servicio para lógica de eliminación
            ProjectService.delete_project(self.object)
            messages.success(request, f'Proyecto "{self.object.name}" eliminado')
            return redirect(success_url)
        except Exception as e:
            messages.error(request, f'Error al eliminar proyecto: {str(e)}')
            return redirect('core:project_detail', project_id=self.object.pk)


# ====================
# VIDEO VIEWS
# ====================

class VideoDetailView(BreadcrumbMixin, ServiceMixin, DetailView):
    """Detalle de un video"""
    model = Video
    template_name = 'videos/detail.html'
    context_object_name = 'video'
    pk_url_kwarg = 'video_id'
    
    def get_breadcrumbs(self):
        return [
            {
                'label': self.object.project.name, 
                'url': reverse('core:project_detail', args=[self.object.project.pk])
            },
            {'label': self.object.title, 'url': None}
        ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Usar servicio para obtener URLs firmadas
        video_service = self.get_video_service()
        video_data = video_service.get_video_with_signed_urls(self.object)
        
        context.update(video_data)
        return context


class VideoCreateView(BreadcrumbMixin, ServiceMixin, FormView):
    """Crear nuevo video"""
    template_name = 'videos/create.html'
    
    def get_form_class(self):
        """Determinar formulario según el tipo de video"""
        # Si es GET request, mostrar formulario base
        if self.request.method == 'GET':
            return VideoBaseForm
        
        # Para POST, determinar tipo desde los datos del formulario
        video_type = self.request.POST.get('type')
        if video_type == 'heygen_avatar_v2':
            return HeyGenAvatarV2Form
        elif video_type == 'heygen_avatar_iv':
            return HeyGenAvatarIVForm
        elif video_type == 'gemini_veo':
            return GeminiVeoVideoForm
        elif video_type == 'sora':
            return SoraVideoForm
        else:
            # Fallback al formulario base si el tipo no es reconocido
            return VideoBaseForm
    
    def get_project(self):
        """Obtener proyecto del contexto"""
        project_id = self.kwargs['project_id']
        return get_object_or_404(Project, pk=project_id)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_project()
        context['project'] = project
        return context
    
    def get_breadcrumbs(self):
        project = self.get_project()
        return [
            {
                'label': project.name, 
                'url': reverse('core:project_detail', args=[project.pk])
            },
            {'label': 'Nuevo Video', 'url': None}
        ]
    
    def post(self, request, *args, **kwargs):
        """Manejar creación de video según tipo"""
        project = self.get_project()
        video_service = self.get_video_service()
        
        # Obtener datos básicos
        title = request.POST.get('title')
        video_type = request.POST.get('type')
        script = request.POST.get('script')
        
        # Validaciones básicas
        if not all([title, video_type, script]):
            messages.error(request, 'Todos los campos son requeridos')
            return self.get(request, *args, **kwargs)
        
        try:
            # Configuración según el tipo de video
            config = self._build_video_config(request, video_type, project, video_service)
            
            # Crear video usando servicio
            video = video_service.create_video(
                project=project,
                title=title,
                video_type=video_type,
                script=script,
                config=config
            )
            
            messages.success(request, f'Video "{title}" creado. Ahora puedes generarlo.')
            return redirect('core:video_detail', video_id=video.pk)
            
        except (ValidationException, ServiceException) as e:
            messages.error(request, str(e))
            return self.get(request, *args, **kwargs)
        except Exception as e:
            messages.error(request, f'Error inesperado: {str(e)}')
            return self.get(request, *args, **kwargs)
    
    def _build_video_config(self, request, video_type, project, video_service):
        """Construir configuración según el tipo de video"""
        config = {}
        
        if video_type == 'heygen_avatar_v2':
            config = self._build_heygen_v2_config(request)
        elif video_type == 'heygen_avatar_iv':
            config = self._build_heygen_iv_config(request, project, video_service)
        elif video_type == 'gemini_veo':
            config = self._build_veo_config(request, project, video_service)
        elif video_type == 'sora':
            config = self._build_sora_config(request, project, video_service)
        
        return config
    
    def _build_heygen_v2_config(self, request):
        """Configuración para HeyGen Avatar V2"""
        avatar_id = request.POST.get('avatar_id')
        voice_id = request.POST.get('voice_id')
        
        if not avatar_id or not voice_id:
            raise ValidationException('Avatar y Voice son campos requeridos para HeyGen Avatar V2')
        
        return {
            'avatar_id': avatar_id,
            'voice_id': voice_id,
            'has_background': request.POST.get('has_background') == 'on',
            'background_url': request.POST.get('background_url', ''),
            'voice_speed': float(request.POST.get('voice_speed', 1.0)),
            'voice_pitch': int(request.POST.get('voice_pitch', 50)),
            'voice_emotion': request.POST.get('voice_emotion', 'Excited'),
        }
    
    def _build_heygen_iv_config(self, request, project, video_service):
        """Configuración para HeyGen Avatar IV"""
        voice_id = request.POST.get('voice_id')
        image_source = request.POST.get('image_source', 'upload')
        
        if not voice_id:
            raise ValidationException('Voice es requerido para HeyGen Avatar IV')
        
        config = {
            'voice_id': voice_id,
            'video_orientation': request.POST.get('video_orientation', 'portrait'),
            'fit': request.POST.get('fit', 'cover'),
        }
        
        if image_source == 'upload':
            avatar_image = request.FILES.get('avatar_image')
            if not avatar_image:
                raise ValidationException('Debes subir una imagen')
            
            # Subir imagen usando servicio
            upload_result = video_service.upload_avatar_image(avatar_image, project)
            config.update({
                'gcs_avatar_path': upload_result['gcs_path'],
                'image_filename': upload_result['filename'],
                'image_source': 'upload'
            })
        else:
            existing_image_key = request.POST.get('existing_image_key')
            if not existing_image_key:
                raise ValidationException('Debes seleccionar una imagen existente')
            
            config.update({
                'existing_image_id': existing_image_key,
                'image_source': 'existing'
            })
        
        return config
    
    def _build_veo_config(self, request, project, video_service):
        """Configuración para Gemini Veo"""
        config = {
            'veo_model': request.POST.get('veo_model', 'veo-2.0-generate-001'),
            'duration': int(request.POST.get('duration', 8)),
            'aspect_ratio': request.POST.get('aspect_ratio', '16:9'),
            'sample_count': int(request.POST.get('sample_count', 1)),
            'negative_prompt': request.POST.get('negative_prompt', ''),
            'enhance_prompt': request.POST.get('enhance_prompt', 'true').lower() == 'true',
            'person_generation': request.POST.get('person_generation', 'allow_adult'),
            'compression_quality': request.POST.get('compression_quality', 'optimized'),
        }
        
        # Seed opcional
        seed_value = request.POST.get('seed', '')
        if seed_value and seed_value.isdigit():
            config['seed'] = int(seed_value)
        
        # Limpiar negative_prompt vacío
        if not config['negative_prompt']:
            config.pop('negative_prompt')
        
        # Imagen inicial (imagen-a-video)
        input_image = request.FILES.get('input_image')
        if input_image:
            upload_result = video_service.upload_veo_input_image(input_image, project)
            config['input_image_gcs_uri'] = upload_result['gcs_path']
            config['input_image_mime_type'] = upload_result['mime_type']
        
        # Imágenes de referencia (máximo 3)
        reference_images = []
        reference_types = []
        for i in range(1, 4):
            ref_image = request.FILES.get(f'reference_image_{i}')
            ref_type = request.POST.get(f'reference_type_{i}', 'asset')
            if ref_image:
                reference_images.append(ref_image)
                reference_types.append(ref_type)
        
        if reference_images:
            uploaded_refs = video_service.upload_veo_reference_images(
                reference_images, reference_types, project
            )
            config['reference_images'] = uploaded_refs
        
        return config
    
    def _build_sora_config(self, request, project, video_service):
        """Configuración para OpenAI Sora"""
        config = {
            'sora_model': request.POST.get('sora_model', 'sora-2'),
            'duration': int(request.POST.get('duration', 8)),
            'size': request.POST.get('size', '1280x720'),
            'use_input_reference': request.POST.get('use_input_reference') == 'on',
        }
        
        # Imagen de referencia (opcional)
        if config['use_input_reference']:
            input_reference = request.FILES.get('input_reference')
            if not input_reference:
                raise ValidationException('Debes subir una imagen de referencia')
            
            # Subir imagen usando servicio
            upload_result = video_service.upload_sora_input_reference(input_reference, project)
            config['input_reference_gcs_path'] = upload_result['gcs_path']
            config['input_reference_mime_type'] = upload_result['mime_type']
        
        return config

class VideoDeleteView(BreadcrumbMixin, DeleteView):
    """Eliminar video"""
    model = Video
    template_name = 'videos/delete.html'
    context_object_name = 'video'
    pk_url_kwarg = 'video_id'
    
    def get_success_url(self):
        return reverse('core:project_detail', kwargs={'project_id': self.object.project.pk})
    
    def get_breadcrumbs(self):
        return [
            {
                'label': self.object.project.name, 
                'url': reverse('core:project_detail', args=[self.object.project.pk])
            },
            {
                'label': self.object.title, 
                'url': reverse('core:video_detail', args=[self.object.pk])
            },
            {'label': 'Eliminar', 'url': None}
        ]
    
    def delete(self, request, *args, **kwargs):
        """Override para eliminar archivo de GCS"""
        self.object = self.get_object()
        success_url = self.get_success_url()
        
        # Eliminar de GCS si existe
        if self.object.gcs_path:
            try:
                from .storage.gcs import gcs_storage
                gcs_storage.delete_file(self.object.gcs_path)
            except Exception as e:
                logger.error(f"Error al eliminar archivo: {e}")
        
        video_title = self.object.title
        self.object.delete()
        
        messages.success(request, f'Video "{video_title}" eliminado')
        return redirect(success_url)


# ====================
# VIDEO ACTIONS
# ====================

class VideoGenerateView(ServiceMixin, View):
    """Generar video usando API externa"""
    
    def post(self, request, video_id):
        video = get_object_or_404(Video, pk=video_id)
        video_service = self.get_video_service()
        
        try:
            external_id = video_service.generate_video(video)
            messages.success(
                request, 
                'Video enviado para generación. El proceso puede tardar varios minutos.'
            )
        except (ValidationException, ServiceException) as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error inesperado: {str(e)}')
        
        return redirect('core:video_detail', video_id=video.pk)


class VideoStatusView(ServiceMixin, View):
    """API endpoint para consultar estado del video"""
    
    def get(self, request, video_id):
        video = get_object_or_404(Video, pk=video_id)
        
        # Si ya está en estado final
        if video.status in ['completed', 'error']:
            return JsonResponse({
                'status': video.status,
                'message': 'Video ya procesado',
                'updated_at': video.updated_at.isoformat()
            })
        
        if not video.external_id:
            return JsonResponse({
                'error': 'Video no tiene external_id',
                'status': video.status
            }, status=400)
        
        # Consultar estado usando servicio
        video_service = self.get_video_service()
        try:
            status_data = video_service.check_video_status(video)
            return JsonResponse({
                'status': video.status,
                'external_status': status_data,
                'updated_at': video.updated_at.isoformat()
            })
        except ServiceException as e:
            return JsonResponse({
                'error': str(e),
                'status': video.status
            }, status=500)


# ====================
# API ENDPOINTS
# ====================

class ListAvatarsView(ServiceMixin, View):
    """Lista avatares de HeyGen"""
    
    def get(self, request):
        try:
            api_service = self.get_api_service()
            avatars = api_service.list_avatars()
            return JsonResponse({'avatars': avatars})
        except ServiceException as e:
            return JsonResponse({
                'error': str(e),
                'avatars': []
            }, status=500)


class ListVoicesView(ServiceMixin, View):
    """Lista voces de HeyGen"""
    
    def get(self, request):
        try:
            api_service = self.get_api_service()
            voices = api_service.list_voices()
            return JsonResponse({'voices': voices})
        except ServiceException as e:
            return JsonResponse({
                'error': str(e),
                'voices': []
            }, status=500)


class ListImageAssetsView(ServiceMixin, View):
    """Lista imágenes disponibles en HeyGen"""
    
    def get(self, request):
        try:
            api_service = self.get_api_service()
            assets = api_service.list_image_assets()
            return JsonResponse({'assets': assets})
        except ServiceException as e:
            return JsonResponse({
                'error': str(e),
                'assets': []
            }, status=500)


# ====================
# IMAGE VIEWS
# ====================

class ImageDetailView(BreadcrumbMixin, ServiceMixin, DetailView):
    """Detalle de una imagen"""
    model = Image
    template_name = 'images/detail.html'
    context_object_name = 'image'
    pk_url_kwarg = 'image_id'
    
    def get_breadcrumbs(self):
        return [
            {
                'label': self.object.project.name, 
                'url': reverse('core:project_detail', args=[self.object.project.pk])
            },
            {'label': self.object.title, 'url': None}
        ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Usar servicio para obtener URLs firmadas
        image_service = self.get_image_service()
        image_data = image_service.get_image_with_signed_url(self.object)
        
        context.update(image_data)
        return context


class ImageCreateView(BreadcrumbMixin, ServiceMixin, FormView):
    """Crear nueva imagen"""
    template_name = 'images/create.html'
    form_class = GeminiImageForm
    
    def get_project(self):
        """Obtener proyecto del contexto"""
        project_id = self.kwargs['project_id']
        return get_object_or_404(Project, pk=project_id)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_project()
        context['project'] = project
        return context
    
    def get_breadcrumbs(self):
        project = self.get_project()
        return [
            {
                'label': project.name, 
                'url': reverse('core:project_detail', args=[project.pk])
            },
            {'label': 'Nueva Imagen', 'url': None}
        ]
    
    def post(self, request, *args, **kwargs):
        """Manejar creación de imagen"""
        project = self.get_project()
        image_service = self.get_image_service()
        
        # Obtener datos básicos
        title = request.POST.get('title')
        image_type = request.POST.get('type')
        prompt = request.POST.get('prompt')
        
        # Validaciones básicas
        if not all([title, image_type, prompt]):
            messages.error(request, 'Todos los campos son requeridos')
            return self.get(request, *args, **kwargs)
        
        try:
            # Configuración según el tipo de imagen
            config = self._build_image_config(request, image_type, project, image_service)
            
            # Crear imagen usando servicio
            image = image_service.create_image(
                project=project,
                title=title,
                image_type=image_type,
                prompt=prompt,
                config=config
            )
            
            messages.success(request, f'Imagen "{title}" creada. Ahora puedes generarla.')
            return redirect('core:image_detail', image_id=image.pk)
            
        except (ValidationException, ServiceException) as e:
            messages.error(request, str(e))
            return self.get(request, *args, **kwargs)
        except Exception as e:
            messages.error(request, f'Error inesperado: {str(e)}')
            return self.get(request, *args, **kwargs)
    
    def _build_image_config(self, request, image_type, project, image_service):
        """Construir configuración según el tipo de imagen"""
        # Configuración común
        config = {
            'aspect_ratio': request.POST.get('aspect_ratio', '1:1'),
        }
        
        # Response modalities
        response_modalities_choice = request.POST.get('response_modalities', 'image_only')
        if response_modalities_choice == 'image_only':
            config['response_modalities'] = ['Image']
        else:
            config['response_modalities'] = ['Text', 'Image']
        
        # Configuración según tipo
        if image_type == 'text_to_image':
            # No se necesita configuración adicional
            pass
        
        elif image_type == 'image_to_image':
            # Subir imagen de entrada
            input_image = request.FILES.get('input_image')
            if not input_image:
                raise ValidationException('Imagen de entrada es requerida para image-to-image')
            
            upload_result = image_service.upload_input_image(input_image, project)
            config['input_image_gcs_path'] = upload_result['gcs_path']
            config['input_image_mime_type'] = upload_result['mime_type']
        
        elif image_type == 'multi_image':
            # Subir múltiples imágenes de entrada
            input_images = []
            for i in range(1, 4):
                img_file = request.FILES.get(f'input_image_{i}')
                if img_file:
                    input_images.append(img_file)
            
            if len(input_images) < 2:
                raise ValidationException('Se requieren al menos 2 imágenes para composición')
            
            uploaded_images = image_service.upload_multiple_input_images(input_images, project)
            config['input_images'] = uploaded_images
        
        return config


class ImageDeleteView(BreadcrumbMixin, DeleteView):
    """Eliminar imagen"""
    model = Image
    template_name = 'images/delete.html'
    context_object_name = 'image'
    pk_url_kwarg = 'image_id'
    
    def get_success_url(self):
        return reverse('core:project_detail', kwargs={'project_id': self.object.project.pk})
    
    def get_breadcrumbs(self):
        return [
            {
                'label': self.object.project.name, 
                'url': reverse('core:project_detail', args=[self.object.project.pk])
            },
            {
                'label': self.object.title, 
                'url': reverse('core:image_detail', args=[self.object.pk])
            },
            {'label': 'Eliminar', 'url': None}
        ]
    
    def delete(self, request, *args, **kwargs):
        """Override para eliminar archivo de GCS"""
        self.object = self.get_object()
        success_url = self.get_success_url()
        
        # Eliminar de GCS si existe
        if self.object.gcs_path:
            try:
                from .storage.gcs import gcs_storage
                gcs_storage.delete_file(self.object.gcs_path)
            except Exception as e:
                logger.error(f"Error al eliminar archivo: {e}")
        
        image_title = self.object.title
        self.object.delete()
        
        messages.success(request, f'Imagen "{image_title}" eliminada')
        return redirect(success_url)


# ====================
# IMAGE ACTIONS
# ====================

class ImageGenerateView(ServiceMixin, View):
    """Generar imagen usando Gemini API"""
    
    def post(self, request, image_id):
        image = get_object_or_404(Image, pk=image_id)
        image_service = self.get_image_service()
        
        try:
            gcs_path = image_service.generate_image(image)
            messages.success(
                request, 
                'Imagen generada exitosamente.'
            )
        except (ValidationException, ImageGenerationException) as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error inesperado: {str(e)}')
        
        return redirect('core:image_detail', image_id=image.pk)


# ====================
# VISTAS PARCIALES HTMX
# ====================

class VideoStatusPartialView(View):
    """Vista parcial para actualizar estado de video con HTMX"""
    
    def get(self, request, video_id):
        from django.template.loader import render_to_string
        from django.http import HttpResponse
        from .services import VideoService
        
        video = get_object_or_404(Video, pk=video_id)
        
        # Si el video está procesando y tiene external_id, consultar estado externo
        if video.status == 'processing' and video.external_id:
            try:
                video_service = VideoService()
                status_data = video_service.check_video_status(video)
                
                # Log del polling
                logger.info(f"=== POLLING VIDEO {video_id} ===")
                logger.info(f"Estado actual: {video.status}")
                logger.info(f"External ID: {video.external_id}")
                logger.info(f"Estado externo: {status_data.get('status', 'unknown')}")
                logger.info(f"Timestamp: {timezone.now()}")
                
                # Refrescar el objeto desde la BD para obtener el estado actualizado
                video.refresh_from_db()
                
            except Exception as e:
                logger.error(f"Error al consultar estado del video {video_id}: {e}")
        
        html = render_to_string('partials/video_status.html', {'video': video})
        return HttpResponse(html)


class ImageStatusPartialView(View):
    """Vista parcial para actualizar estado de imagen con HTMX"""
    
    def get(self, request, image_id):
        from django.template.loader import render_to_string
        from django.http import HttpResponse
        image = get_object_or_404(Image, pk=image_id)
        html = render_to_string('partials/image_status.html', {'image': image})
        return HttpResponse(html)


class ScriptStatusPartialView(View):
    """Vista parcial para actualizar estado de guión con HTMX"""
    
    def get(self, request, script_id):
        from django.template.loader import render_to_string
        from django.http import HttpResponse
        from .services import RedisService, N8nService
        script = get_object_or_404(Script, pk=script_id)
        
        # Log del polling
        logger.info(f"=== POLLING SCRIPT {script_id} ===")
        logger.info(f"Estado actual: {script.status}")
        logger.info(f"Datos procesados: {bool(script.processed_data)}")
        if script.processed_data:
            logger.info(f"Escenas: {len(script.scenes)}")
        logger.info(f"Timestamp: {timezone.now()}")
        
        # Si está procesando, verificar Redis
        if script.status == 'processing':
            try:
                redis_service = RedisService()
                result = redis_service.get_script_result(str(script_id))
                
                if result:
                    logger.info(f"✓ Resultado encontrado en Redis para guión {script_id}")
                    # Procesar resultado como si fuera webhook
                    n8n_service = N8nService()
                    script = n8n_service.process_webhook_response(result)
                    logger.info(f"✓ Guión {script_id} actualizado desde Redis")
                else:
                    logger.info(f"⏳ No hay resultado aún en Redis para guión {script_id}")
                    
            except Exception as e:
                logger.error(f"✗ Error al consultar Redis: {e}")
        
        html = render_to_string('partials/script_status.html', {'script': script})
        return HttpResponse(html)


# ====================
# SCRIPT VIEWS
# ====================

class ScriptDetailView(BreadcrumbMixin, ServiceMixin, DetailView):
    """Detalle de un guión"""
    model = Script
    template_name = 'scripts/detail.html'
    context_object_name = 'script'
    pk_url_kwarg = 'script_id'
    
    def get_breadcrumbs(self):
        return [
            {
                'label': self.object.project.name, 
                'url': reverse('core:project_detail', args=[self.object.project.pk])
            },
            {'label': self.object.title, 'url': None}
        ]


class ScriptCreateView(BreadcrumbMixin, ServiceMixin, FormView):
    """Crear nuevo guión"""
    template_name = 'scripts/create.html'
    form_class = ScriptForm
    
    def get_template_names(self):
        """Usar template modal si es petición HTMX"""
        if self.request.headers.get('HX-Request'):
            return ['scripts/create_modal.html']
        return ['scripts/create.html']
    
    def get_project(self):
        """Obtener proyecto del contexto"""
        project_id = self.kwargs['project_id']
        return get_object_or_404(Project, pk=project_id)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_project()
        context['project'] = project
        return context
    
    def get_breadcrumbs(self):
        project = self.get_project()
        return [
            {
                'label': project.name, 
                'url': reverse('core:project_detail', args=[project.pk])
            },
            {'label': 'Nuevo Guión', 'url': None}
        ]
    
    def post(self, request, *args, **kwargs):
        """Manejar creación de guión"""
        project = self.get_project()
        
        # Obtener datos básicos
        title = request.POST.get('title')
        original_script = request.POST.get('original_script')
        desired_duration_min = request.POST.get('desired_duration_min', 5)
        
        # Validaciones básicas
        if not all([title, original_script]):
            messages.error(request, 'Todos los campos son requeridos')
            return self.get(request, *args, **kwargs)
        
        try:
            # Crear guión
            script = Script.objects.create(
                project=project,
                title=title,
                original_script=original_script,
                desired_duration_min=int(desired_duration_min),
                status='pending'
            )
            
            # Enviar a n8n para procesamiento (en background)
            n8n_service = N8nService()
            try:
                n8n_service.send_script_for_processing(script)
                messages.success(request, f'Guión "{title}" creado y enviado para procesamiento.')
            except Exception as e:
                messages.warning(request, f'Guión "{title}" creado pero hubo un problema al enviarlo para procesamiento: {str(e)}')
            
            # Redirigir inmediatamente al detalle del guión
            return redirect('core:script_detail', script_id=script.pk)
            
        except Exception as e:
            messages.error(request, f'Error inesperado: {str(e)}')
            return self.get(request, *args, **kwargs)


class ScriptDeleteView(BreadcrumbMixin, DeleteView):
    """Eliminar guión"""
    model = Script
    template_name = 'scripts/delete.html'
    context_object_name = 'script'
    pk_url_kwarg = 'script_id'
    
    def get_success_url(self):
        return reverse('core:project_detail', kwargs={'project_id': self.object.project.pk})
    
    def get_breadcrumbs(self):
        return [
            {
                'label': self.object.project.name, 
                'url': reverse('core:project_detail', args=[self.object.project.pk])
            },
            {
                'label': self.object.title, 
                'url': reverse('core:script_detail', args=[self.object.pk])
            },
            {'label': 'Eliminar', 'url': None}
        ]
    
    def delete(self, request, *args, **kwargs):
        """Manejar eliminación con soporte HTMX"""
        self.object = self.get_object()
        project_id = self.object.project.pk
        self.object.delete()
        
        # Si es petición HTMX, devolver respuesta vacía (el elemento se eliminará)
        if request.headers.get('HX-Request'):
            from django.http import HttpResponse
            return HttpResponse(status=200)
        
        # Si no es HTMX, redirigir normalmente
        return redirect('core:project_detail', project_id=project_id)


class ScriptRetryView(ServiceMixin, View):
    """Reintentar procesamiento de guión"""
    
    def post(self, request, script_id):
        script = get_object_or_404(Script, pk=script_id)
        
        try:
            # Resetear estado
            script.status = 'pending'
            script.error_message = None
            script.save()
            
            # Reenviar a n8n
            n8n_service = N8nService()
            if n8n_service.send_script_for_processing(script):
                messages.success(request, f'Guión "{script.title}" reenviado para procesamiento.')
            else:
                messages.error(request, f'Error al reenviar guión "{script.title}".')
            
            # Si es petición HTMX, devolver template parcial
            if request.headers.get('HX-Request'):
                from django.template.loader import render_to_string
                from django.http import HttpResponse
                html = render_to_string('partials/script_actions.html', {'script': script})
                return HttpResponse(html)
            
            return redirect('core:script_detail', script_id=script.pk)
            
        except Exception as e:
            messages.error(request, f'Error inesperado: {str(e)}')
            return redirect('core:script_detail', script_id=script.pk)


# ====================
# AGENT VIDEO FLOW
# ====================

class AgentCreateView(BreadcrumbMixin, View):
    """Paso 1: Crear contenido (script o PDF)"""
    template_name = 'agent/create.html'
    
    def get_project(self):
        project_id = self.kwargs['project_id']
        return get_object_or_404(Project, pk=project_id)
    
    def get_breadcrumbs(self):
        project = self.get_project()
        return [
            {'label': project.name, 'url': reverse('core:project_detail', args=[project.pk])},
            {'label': 'Agente de Video', 'url': None}
        ]
    
    def get(self, request, project_id):
        project = self.get_project()
        
        context = {
            'project': project,
            'breadcrumbs': self.get_breadcrumbs()
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, project_id):
        """
        Guarda el contenido en sessionStorage (lado cliente) y redirige
        El POST solo valida y redirige a configure
        """
        project = self.get_project()
        
        content_type = request.POST.get('content_type')
        script_content = request.POST.get('script_content')
        
        if not content_type or not script_content:
            messages.error(request, 'Debes proporcionar el contenido del script')
            return redirect('core:agent_create', project_id=project_id)
        
        # El script se guarda en sessionStorage en el cliente
        # Aquí solo redirigimos a configure
        return redirect('core:agent_configure', project_id=project_id)


class AgentConfigureView(BreadcrumbMixin, ServiceMixin, View):
    """Paso 2: Procesar con IA y configurar escenas"""
    template_name = 'agent/configure.html'
    
    def get_project(self):
        project_id = self.kwargs['project_id']
        return get_object_or_404(Project, pk=project_id)
    
    def get_breadcrumbs(self):
        project = self.get_project()
        return [
            {'label': project.name, 'url': reverse('core:project_detail', args=[project.pk])},
            {'label': 'Configurar Escenas', 'url': None}
        ]
    
    def get(self, request, project_id):
        """
        Muestra pantalla de "Processing..." 
        Si hay un script_id en la URL, muestra las escenas
        """
        project = self.get_project()
        
        script_id = request.GET.get('script_id')
        
        # Si hay script_id, cargar escenas
        if script_id:
            try:
                script = Script.objects.get(id=script_id, project=project, agent_flow=True)
                scenes = script.db_scenes.all().order_by('order')
                
                # Generar URLs firmadas para preview images
                scenes_with_urls = []
                for scene in scenes:
                    scene_data = SceneService().get_scene_with_signed_urls(scene)
                    scenes_with_urls.append(scene_data)
                
                context = {
                    'project': project,
                    'script': script,
                    'scenes': scenes,
                    'scenes_with_urls': scenes_with_urls,
                    'breadcrumbs': self.get_breadcrumbs()
                }
                
                return render(request, self.template_name, context)
                
            except Script.DoesNotExist:
                messages.error(request, 'Script no encontrado')
                return redirect('core:agent_create', project_id=project_id)
        
        # Si no hay script_id, mostrar pantalla inicial
        context = {
            'project': project,
            'breadcrumbs': self.get_breadcrumbs()
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, project_id):
        """
        Recibe el script desde el cliente y lo envía a n8n
        """
        project = self.get_project()
        
        # Obtener datos del POST
        script_title = request.POST.get('title', 'Video con Agente')
        script_content = request.POST.get('script_content')
        desired_duration_min = request.POST.get('desired_duration_min', 5)
        
        if not script_content:
            messages.error(request, 'El contenido del script es requerido')
            return redirect('core:agent_create', project_id=project_id)
        
        try:
            # Crear Script con agent_flow=True
            script = Script.objects.create(
                project=project,
                title=script_title,
                original_script=script_content,
                desired_duration_min=int(desired_duration_min),
                agent_flow=True,  # Marcar como flujo del agente
                status='pending'
            )
            
            # Enviar a n8n
            from .services import N8nService
            n8n_service = N8nService()
            
            try:
                n8n_service.send_script_for_processing(script)
                
                # Redirigir a la misma página con script_id para polling
                return JsonResponse({
                    'status': 'success',
                    'script_id': script.id,
                    'message': 'Script enviado para procesamiento'
                })
                
            except Exception as e:
                script.mark_as_error(str(e))
                return JsonResponse({
                    'status': 'error',
                    'message': f'Error al enviar script: {str(e)}'
                }, status=500)
                
        except Exception as e:
            logger.error(f"Error al crear script: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Error al crear script: {str(e)}'
            }, status=500)


class AgentScenesView(BreadcrumbMixin, ServiceMixin, View):
    """Paso 3: Generar videos de las escenas"""
    template_name = 'agent/scenes.html'
    
    def get_project(self):
        project_id = self.kwargs['project_id']
        return get_object_or_404(Project, pk=project_id)
    
    def get_breadcrumbs(self):
        project = self.get_project()
        return [
            {'label': project.name, 'url': reverse('core:project_detail', args=[project.pk])},
            {'label': 'Generar Escenas', 'url': None}
        ]
    
    def get(self, request, project_id):
        project = self.get_project()
        
        script_id = request.GET.get('script_id')
        
        if not script_id:
            messages.error(request, 'Script ID requerido')
            return redirect('core:agent_create', project_id=project_id)
        
        try:
            script = Script.objects.get(id=script_id, project=project, agent_flow=True)
            scenes = script.db_scenes.filter(is_included=True).order_by('order')
            
            # Generar URLs firmadas para cada escena
            scenes_with_urls = []
            for scene in scenes:
                scene_data = SceneService().get_scene_with_signed_urls(scene)
                scenes_with_urls.append(scene_data)
            
            context = {
                'project': project,
                'script': script,
                'scenes': scenes,
                'scenes_with_urls': scenes_with_urls,
                'breadcrumbs': self.get_breadcrumbs()
            }
            
            return render(request, self.template_name, context)
            
        except Script.DoesNotExist:
            messages.error(request, 'Script no encontrado')
            return redirect('core:agent_create', project_id=project_id)


class AgentFinalView(BreadcrumbMixin, ServiceMixin, View):
    """Paso 4: Combinar videos y crear video final"""
    template_name = 'agent/final.html'
    
    def get_project(self):
        project_id = self.kwargs['project_id']
        return get_object_or_404(Project, pk=project_id)
    
    def get_breadcrumbs(self):
        project = self.get_project()
        return [
            {'label': project.name, 'url': reverse('core:project_detail', args=[project.pk])},
            {'label': 'Video Final', 'url': None}
        ]
    
    def get(self, request, project_id):
        project = self.get_project()
        
        script_id = request.GET.get('script_id')
        
        if not script_id:
            messages.error(request, 'Script ID requerido')
            return redirect('core:agent_create', project_id=project_id)
        
        try:
            script = Script.objects.get(id=script_id, project=project, agent_flow=True)
            scenes = script.db_scenes.filter(
                is_included=True,
                video_status='completed'
            ).order_by('order')
            
            # Generar URLs firmadas
            scenes_with_urls = []
            for scene in scenes:
                scene_data = SceneService().get_scene_with_signed_urls(scene)
                scenes_with_urls.append(scene_data)
            
            context = {
                'project': project,
                'script': script,
                'scenes': scenes,
                'scenes_with_urls': scenes_with_urls,
                'breadcrumbs': self.get_breadcrumbs()
            }
            
            return render(request, self.template_name, context)
            
        except Script.DoesNotExist:
            messages.error(request, 'Script no encontrado')
            return redirect('core:agent_create', project_id=project_id)
    
    def post(self, request, project_id):
        """Combinar videos de escenas con FFmpeg"""
        from .services import VideoCompositionService
        from datetime import datetime
        
        project = self.get_project()
        
        script_id = request.POST.get('script_id')
        video_title = request.POST.get('video_title')
        
        if not script_id or not video_title:
            return JsonResponse({
                'status': 'error',
                'message': 'Script ID y título son requeridos'
            }, status=400)
        
        try:
            script = Script.objects.get(id=script_id, project=project, agent_flow=True)
            scenes = script.db_scenes.filter(
                is_included=True,
                video_status='completed'
            ).order_by('order')
            
            if scenes.count() == 0:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No hay escenas completadas para combinar'
                }, status=400)
            
            # Combinar videos con FFmpeg
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"{timestamp}_{video_title.replace(' ', '_')}.mp4"
            
            composition_service = VideoCompositionService()
            gcs_path = composition_service.combine_scene_videos(scenes, output_filename)
            
            # Calcular duración total
            total_duration = sum(scene.duration_sec for scene in scenes)
            
            # Crear objeto Video final
            video = Video.objects.create(
                project=project,
                title=video_title,
                type='gemini_veo',  # Tipo genérico, podría ser mixto
                status='completed',
                script=f"Video generado por agente con {scenes.count()} escenas",
                config={
                    'agent_generated': True,
                    'script_id': script.id,
                    'num_scenes': scenes.count(),
                    'scene_ids': [scene.id for scene in scenes]
                },
                gcs_path=gcs_path,
                duration=total_duration,
                metadata={
                    'scenes': [
                        {
                            'scene_id': scene.scene_id,
                            'ai_service': scene.ai_service,
                            'duration_sec': scene.duration_sec
                        }
                        for scene in scenes
                    ]
                },
                completed_at=timezone.now()
            )
            
            # Asociar video final con el script
            script.final_video = video
            script.save(update_fields=['final_video'])
            
            logger.info(f"✓ Video final creado: {video.id} para script {script.id}")
            
            return JsonResponse({
                'status': 'success',
                'message': 'Video combinado exitosamente',
                'video_id': video.id
            })
            
        except Script.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Script no encontrado'
            }, status=404)
        except (ValidationException, ServiceException) as e:
            logger.error(f"Error de servicio al combinar videos: {e}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
        except Exception as e:
            logger.error(f"Error inesperado al combinar videos: {e}")
            logger.exception("Traceback completo:")
            return JsonResponse({
                'status': 'error',
                'message': f'Error inesperado: {str(e)}'
            }, status=500)


# ====================
# SCENE ACTIONS
# ====================

class SceneGenerateView(ServiceMixin, View):
    """Generar video para una escena"""
    
    def post(self, request, scene_id):
        from .models import Scene
        
        try:
            scene = get_object_or_404(Scene, pk=scene_id)
            
            # Validar configuración de HeyGen antes de generar
            if scene.ai_service == 'heygen':
                logger.info(f"Validando configuración de HeyGen para escena {scene_id}")
                logger.info(f"  ai_config: {scene.ai_config}")
                
                if not scene.ai_config.get('avatar_id') or not scene.ai_config.get('voice_id'):
                    error_msg = 'Debes configurar el avatar y la voz. Regresa al Paso 2 (Configurar) y selecciona un avatar y una voz para esta escena HeyGen.'
                    logger.error(f"Escena {scene_id}: {error_msg}")
                    return JsonResponse({
                        'status': 'error',
                        'message': error_msg
                    }, status=400)
                    
                logger.info(f"  ✓ Avatar ID: {scene.ai_config.get('avatar_id')}")
                logger.info(f"  ✓ Voice ID: {scene.ai_config.get('voice_id')}")
            
            # Generar video usando SceneService
            scene_service = SceneService()
            external_id = scene_service.generate_scene_video(scene)
            
            return JsonResponse({
                'status': 'success',
                'message': 'Video de escena enviado para generación',
                'external_id': external_id,
                'scene_id': scene.id
            })
            
        except ValidationException as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
        except Exception as e:
            logger.error(f"Error al generar video de escena: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Error: {str(e)}'
            }, status=500)


class SceneStatusView(View):
    """Consultar estado de una escena (para polling)"""
    
    def get(self, request, scene_id):
        from .models import Scene
        
        try:
            scene = get_object_or_404(Scene, pk=scene_id)
            
            # Si está procesando y tiene external_id, consultar estado
            if scene.video_status == 'processing' and scene.external_id:
                try:
                    scene_service = SceneService()
                    status_data = scene_service.check_scene_video_status(scene)
                    
                    # Refrescar desde BD
                    scene.refresh_from_db()
                    
                except Exception as e:
                    logger.error(f"Error al consultar estado de escena {scene_id}: {e}")
            
            # Generar URLs firmadas
            scene_data = SceneService().get_scene_with_signed_urls(scene)
            
            return JsonResponse({
                'status': 'success',
                'scene_id': scene.id,
                'video_status': scene.video_status,
                'preview_status': scene.preview_image_status,
                'video_url': scene_data.get('video_url'),
                'preview_url': scene_data.get('preview_image_url'),
                'error_message': scene.error_message
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)


class SceneUpdateConfigView(View):
    """Actualizar configuración de una escena"""
    
    def post(self, request, scene_id):
        try:
            scene = get_object_or_404(Scene, id=scene_id)
            
            import json
            data = json.loads(request.body)
            
            logger.info(f"Actualizando configuración de escena {scene_id}: {data}")
            
            # Actualizar ai_service si viene
            if 'ai_service' in data:
                scene.ai_service = data['ai_service']
                logger.info(f"  ai_service actualizado a: {data['ai_service']}")
            
            # Actualizar ai_config
            if 'ai_config' in data:
                scene.ai_config.update(data['ai_config'])
                logger.info(f"  ai_config actualizado: {scene.ai_config}")
            
            # Actualizar script_text si viene
            if 'script_text' in data:
                scene.script_text = data['script_text']
                logger.info(f"  script_text actualizado")
            
            scene.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Configuración actualizada',
                'ai_config': scene.ai_config  # Retornar para confirmación
            })
            
        except Exception as e:
            logger.error(f"Error al actualizar configuración de escena {scene_id}: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Error: {str(e)}'
            }, status=500)


class SceneRegenerateView(View):
    """Regenerar video de una escena (crea nueva versión)"""
    
    def post(self, request, scene_id):
        try:
            original_scene = get_object_or_404(Scene, id=scene_id)
            
            logger.info(f"Regenerando escena {scene_id} (versión actual: {original_scene.version})")
            
            # Crear nueva versión de la escena
            new_version = original_scene.version + 1
            
            new_scene = Scene.objects.create(
                script=original_scene.script,
                project=original_scene.project,
                scene_id=original_scene.scene_id,
                summary=original_scene.summary,
                script_text=original_scene.script_text,
                duration_sec=original_scene.duration_sec,
                avatar=original_scene.avatar,
                platform=original_scene.platform,
                broll=original_scene.broll,
                transition=original_scene.transition,
                text_on_screen=original_scene.text_on_screen,
                audio_notes=original_scene.audio_notes,
                order=original_scene.order,
                is_included=original_scene.is_included,
                ai_service=original_scene.ai_service,
                ai_config=original_scene.ai_config.copy(),
                preview_image_gcs_path=original_scene.preview_image_gcs_path,
                preview_image_status=original_scene.preview_image_status,
                video_status='pending',
                version=new_version,
                parent_scene_id=original_scene.id
            )
            
            # Marcar la versión anterior como no incluida
            original_scene.is_included = False
            original_scene.save(update_fields=['is_included', 'updated_at'])
            
            # Generar nuevo video
            scene_service = SceneService()
            external_id = scene_service.generate_scene_video(new_scene)
            
            return JsonResponse({
                'status': 'success',
                'message': 'Nueva versión de escena creada',
                'new_scene_id': new_scene.id,
                'version': new_version,
                'external_id': external_id
            })
            
        except Exception as e:
            logger.error(f"Error al regenerar escena {scene_id}: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Error al regenerar escena: {str(e)}'
            }, status=500)


class SceneVersionsView(View):
    """Obtener todas las versiones de una escena"""
    
    def get(self, request, scene_id):
        try:
            scene = get_object_or_404(Scene, id=scene_id)
            
            # Obtener todas las versiones (la actual y sus ancestros)
            versions = []
            
            # Primero agregar la escena actual
            scene_service = SceneService()
            current_data = scene_service.get_scene_with_signed_urls(scene)
            versions.append({
                'id': scene.id,
                'version': scene.version,
                'created_at': scene.created_at.isoformat(),
                'video_status': scene.video_status,
                'is_included': scene.is_included,
                'video_url': current_data.get('video_url'),
                'preview_url': current_data.get('preview_url')
            })
            
            # Luego agregar todas las versiones anteriores
            parent = scene.parent_scene
            while parent:
                parent_data = scene_service.get_scene_with_signed_urls(parent)
                versions.append({
                    'id': parent.id,
                    'version': parent.version,
                    'created_at': parent.created_at.isoformat(),
                    'video_status': parent.video_status,
                    'is_included': parent.is_included,
                    'video_url': parent_data.get('video_url'),
                    'preview_url': parent_data.get('preview_url')
                })
                parent = parent.parent_scene
            
            return JsonResponse({
                'status': 'success',
                'versions': versions
            })
            
        except Exception as e:
            logger.error(f"Error al obtener versiones de escena {scene_id}: {e}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)


# ====================
# WEBHOOK INTEGRATION
# ====================

class N8nWebhookView(View):
    """Webhook para recibir respuestas de n8n"""
    
    from django.views.decorators.csrf import csrf_exempt
    from django.utils.decorators import method_decorator
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request):
        """Procesar respuesta del webhook de n8n"""
        try:
            import json
            
            # Log de inicio
            logger.info("=" * 80)
            logger.info("=== WEBHOOK N8N RECIBIDO ===")
            logger.info(f"Timestamp: {timezone.now()}")
            logger.info(f"Request headers: {dict(request.headers)}")
            logger.info(f"Request body (raw): {request.body.decode('utf-8')}")
            
            # Obtener datos del webhook
            data = json.loads(request.body)
            
            # Log de los datos parseados
            logger.info(f"Datos parseados:")
            logger.info(f"  - status: {data.get('status')}")
            logger.info(f"  - script_id: {data.get('script_id')}")
            logger.info(f"  - message: {data.get('message')}")
            logger.info(f"  - project: {data.get('project', {})}")
            logger.info(f"  - scenes count: {len(data.get('scenes', []))}")
            
            # Procesar respuesta usando el servicio
            n8n_service = N8nService()
            script = n8n_service.process_webhook_response(data)
            
            logger.info(f"✓ Webhook n8n procesado exitosamente para guión {script.id}")
            logger.info(f"  - Nuevo estado: {script.status}")
            logger.info(f"  - Escenas guardadas: {len(script.scenes)}")
            logger.info("=" * 80)
            
            return JsonResponse({
                'status': 'success', 
                'message': 'Datos procesados',
                'script_id': script.id
            })
            
        except json.JSONDecodeError as e:
            logger.error(f"✗ JSON inválido en webhook: {e}")
            return JsonResponse({'error': 'JSON inválido'}, status=400)
        except (ValidationException, ServiceException) as e:
            logger.error(f"✗ Error de validación en webhook n8n: {e}")
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            logger.error(f"✗ Error inesperado en webhook n8n: {e}")
            logger.exception("Traceback completo:")
            return JsonResponse({'error': 'Error interno'}, status=500)