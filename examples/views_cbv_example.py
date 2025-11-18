"""
EJEMPLO: Class-Based Views - Mejores Prácticas
================================================

Reemplaza Function-Based Views con CBVs para mejor reutilización
"""

from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, View
)
from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator

from core.models import Project, Video
from core.forms import ProjectForm, get_video_form_class
from core.services import ProjectService, VideoService


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


# ====================
# DASHBOARD
# ====================

class DashboardView(LoginRequiredMixin, ListView):
    """Vista principal del dashboard"""
    model = Project
    template_name = 'dashboard/index.html'
    context_object_name = 'projects'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Agregar estadísticas
        context.update({
            'total_videos': Video.objects.count(),
            'completed_videos': Video.objects.filter(status='completed').count(),
            'processing_videos': Video.objects.filter(status='processing').count(),
        })
        
        return context


# ====================
# PROJECT VIEWS
# ====================

class ProjectListView(LoginRequiredMixin, ListView):
    """Lista de proyectos del usuario"""
    model = Project
    template_name = 'projects/list.html'
    context_object_name = 'projects'
    paginate_by = 20
    
    def get_queryset(self):
        """Filtrar proyectos del usuario"""
        # TODO: Filtrar por request.user cuando se implemente
        return Project.objects.all().order_by('-created_at')


class ProjectDetailView(LoginRequiredMixin, BreadcrumbMixin, DetailView):
    """Detalle de un proyecto con sus videos"""
    model = Project
    template_name = 'projects/detail.html'
    context_object_name = 'project'
    pk_url_kwarg = 'project_id'
    
    def get_breadcrumbs(self):
        return [
            {'label': self.object.name, 'url': None}
        ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener videos del proyecto
        videos = self.object.videos.select_related('project').order_by('-created_at')
        
        # Generar URLs firmadas para videos completados
        from core.storage.gcs import gcs_storage
        import logging
        logger = logging.getLogger(__name__)
        
        videos_with_urls = []
        for video in videos:
            video_data = {
                'video': video,
                'signed_url': None
            }
            if video.status == 'completed' and video.gcs_path:
                try:
                    video_data['signed_url'] = gcs_storage.get_signed_url(
                        video.gcs_path, 
                        expiration=3600
                    )
                except Exception as e:
                    logger.error(f"Error al generar URL firmada: {e}")
            
            videos_with_urls.append(video_data)
        
        context['videos'] = videos
        context['videos_with_urls'] = videos_with_urls
        
        return context


class ProjectCreateView(LoginRequiredMixin, SuccessMessageMixin, BreadcrumbMixin, CreateView):
    """Crear nuevo proyecto"""
    model = Project
    form_class = ProjectForm
    template_name = 'projects/create.html'
    success_message = 'Proyecto creado exitosamente'
    
    def get_success_url(self):
        return reverse('core:project_detail', kwargs={'project_id': self.object.pk})
    
    def get_breadcrumbs(self):
        return [
            {'label': 'Nuevo Proyecto', 'url': None}
        ]
    
    def form_valid(self, form):
        """Asignar usuario propietario"""
        # TODO: Asignar request.user cuando se implemente
        return super().form_valid(form)


class ProjectUpdateView(LoginRequiredMixin, SuccessMessageMixin, BreadcrumbMixin, UpdateView):
    """Editar proyecto"""
    model = Project
    form_class = ProjectForm
    template_name = 'projects/edit.html'
    pk_url_kwarg = 'project_id'
    success_message = 'Proyecto actualizado exitosamente'
    
    def get_success_url(self):
        return reverse('core:project_detail', kwargs={'project_id': self.object.pk})
    
    def get_breadcrumbs(self):
        return [
            {'label': self.object.name, 'url': reverse('core:project_detail', args=[self.object.pk])},
            {'label': 'Editar', 'url': None}
        ]


class ProjectDeleteView(LoginRequiredMixin, BreadcrumbMixin, DeleteView):
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
        
        # Usar servicio para lógica de eliminación
        ProjectService.delete_project(self.object)
        
        messages.success(request, f'Proyecto "{self.object.name}" eliminado')
        return redirect(success_url)


# ====================
# VIDEO VIEWS
# ====================

class VideoDetailView(LoginRequiredMixin, BreadcrumbMixin, DetailView):
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
        
        from core.storage.gcs import gcs_storage
        import logging
        logger = logging.getLogger(__name__)
        
        # URL firmada del video principal
        signed_url = None
        if self.object.status == 'completed' and self.object.gcs_path:
            try:
                signed_url = gcs_storage.get_signed_url(self.object.gcs_path)
            except Exception as e:
                logger.error(f"Error al generar URL: {e}")
        
        # URLs de todos los videos (si hay múltiples)
        all_videos_with_urls = []
        if self.object.status == 'completed' and self.object.metadata.get('all_videos'):
            for video_data in self.object.metadata['all_videos']:
                if video_data.get('gcs_path'):
                    try:
                        signed = gcs_storage.get_signed_url(
                            video_data['gcs_path'], 
                            expiration=3600
                        )
                        all_videos_with_urls.append({
                            'index': video_data['index'],
                            'signed_url': signed,
                            'gcs_path': video_data['gcs_path']
                        })
                    except Exception as e:
                        logger.error(f"Error: {e}")
        
        context.update({
            'signed_url': signed_url,
            'all_videos': all_videos_with_urls,
        })
        
        return context


class VideoCreateView(LoginRequiredMixin, BreadcrumbMixin, FormView):
    """Crear nuevo video (multi-step form)"""
    template_name = 'videos/create.html'
    
    def get_form_class(self):
        """Obtener form según el tipo de video"""
        video_type = self.request.POST.get('type') or self.request.GET.get('type', 'heygen_avatar_v2')
        return get_video_form_class(video_type)
    
    def get_project(self):
        """Obtener proyecto del contexto"""
        return get_object_or_404(Project, pk=self.kwargs['project_id'])
    
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
    
    def form_valid(self, form):
        """Crear video usando VideoService"""
        project = self.get_project()
        service = VideoService()
        
        try:
            # Preparar configuración
            config = {}
            
            # Manejar upload de imagen si existe
            if form.cleaned_data.get('avatar_image'):
                upload_result = service.upload_avatar_image(
                    form.cleaned_data['avatar_image'],
                    project
                )
                config['gcs_avatar_path'] = upload_result['gcs_path']
                config['image_filename'] = upload_result['filename']
                config['image_source'] = 'upload'
            
            # Crear video
            video = form.save(commit=False)
            video.project = project
            video.save()
            
            messages.success(
                self.request, 
                f'Video "{video.title}" creado. Ahora puedes generarlo.'
            )
            return redirect('core:video_detail', video_id=video.pk)
            
        except Exception as e:
            messages.error(self.request, f'Error al crear video: {str(e)}')
            return self.form_invalid(form)


class VideoDeleteView(LoginRequiredMixin, BreadcrumbMixin, DeleteView):
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
            from core.storage.gcs import gcs_storage
            import logging
            logger = logging.getLogger(__name__)
            
            try:
                gcs_storage.delete_file(self.object.gcs_path)
            except Exception as e:
                logger.error(f"Error al eliminar archivo: {e}")
        
        video_title = self.object.title
        self.object.delete()
        
        messages.success(request, f'Video "{video_title}" eliminado')
        return redirect(success_url)


# ====================
# VIDEO ACTIONS (API-like)
# ====================

class VideoGenerateView(LoginRequiredMixin, View):
    """Generar video usando API externa"""
    
    def post(self, request, video_id):
        video = get_object_or_404(Video, pk=video_id)
        service = VideoService()
        
        try:
            service.generate_video(video)
            messages.success(
                request, 
                'Video enviado para generación. El proceso puede tardar varios minutos.'
            )
        except Exception as e:
            messages.error(request, f'Error al generar video: {str(e)}')
        
        return redirect('core:video_detail', video_id=video.pk)


class VideoStatusView(LoginRequiredMixin, View):
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
        
        # Consultar estado
        service = VideoService()
        try:
            status_data = service.check_video_status(video)
            return JsonResponse({
                'status': video.status,
                'external_status': status_data,
                'updated_at': video.updated_at.isoformat()
            })
        except Exception as e:
            return JsonResponse({
                'error': str(e),
                'status': video.status
            }, status=500)


# ====================
# API ENDPOINTS
# ====================

class ListAvatarsView(LoginRequiredMixin, View):
    """Lista avatares de HeyGen"""
    
    def get(self, request):
        from django.conf import settings
        from core.ai_services.heygen import HeyGenClient
        import logging
        logger = logging.getLogger(__name__)
        
        if not settings.HEYGEN_API_KEY:
            return JsonResponse({
                'error': 'HEYGEN_API_KEY no configurada',
                'avatars': []
            }, status=400)
        
        try:
            client = HeyGenClient(api_key=settings.HEYGEN_API_KEY)
            avatars = client.list_avatars()
            return JsonResponse({'avatars': avatars})
        except Exception as e:
            logger.error(f"Error: {e}")
            return JsonResponse({
                'error': str(e),
                'avatars': []
            }, status=500)


class ListVoicesView(LoginRequiredMixin, View):
    """Lista voces de HeyGen"""
    
    def get(self, request):
        from django.conf import settings
        from core.ai_services.heygen import HeyGenClient
        import logging
        logger = logging.getLogger(__name__)
        
        if not settings.HEYGEN_API_KEY:
            return JsonResponse({
                'error': 'HEYGEN_API_KEY no configurada',
                'voices': []
            }, status=400)
        
        try:
            client = HeyGenClient(api_key=settings.HEYGEN_API_KEY)
            voices = client.list_voices()
            return JsonResponse({'voices': voices})
        except Exception as e:
            logger.error(f"Error: {e}")
            return JsonResponse({
                'error': str(e),
                'voices': []
            }, status=500)


# ====================
# URLS.PY EXAMPLE
# ====================

"""
# core/urls.py

from django.urls import path
from . import views_cbv as views

app_name = 'core'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Projects
    path('projects/', views.ProjectListView.as_view(), name='project_list'),
    path('projects/create/', views.ProjectCreateView.as_view(), name='project_create'),
    path('projects/<int:project_id>/', views.ProjectDetailView.as_view(), name='project_detail'),
    path('projects/<int:project_id>/edit/', views.ProjectUpdateView.as_view(), name='project_edit'),
    path('projects/<int:project_id>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),
    
    # Videos
    path('projects/<int:project_id>/videos/create/', views.VideoCreateView.as_view(), name='video_create'),
    path('videos/<int:video_id>/', views.VideoDetailView.as_view(), name='video_detail'),
    path('videos/<int:video_id>/delete/', views.VideoDeleteView.as_view(), name='video_delete'),
    path('videos/<int:video_id>/generate/', views.VideoGenerateView.as_view(), name='video_generate'),
    path('videos/<int:video_id>/status/', views.VideoStatusView.as_view(), name='video_status'),
    
    # API endpoints
    path('api/avatars/', views.ListAvatarsView.as_view(), name='api_list_avatars'),
    path('api/voices/', views.ListVoicesView.as_view(), name='api_list_voices'),
]
"""

