"""
Class-Based Views refactorizadas para mejor mantenibilidad
"""

from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, View
)
from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import permission_required
from django.utils import timezone
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Max
from django.contrib.auth import authenticate, login, logout
import os
from django.contrib.auth.models import User, Group
from .forms import CustomUserCreationForm, PendingUserCreationForm, ActivationSetPasswordForm
from django.db import IntegrityError

from .models import Project, Video, Image, Script, Scene
from .forms import VideoBaseForm, HeyGenAvatarV2Form, HeyGenAvatarIVForm, GeminiVeoVideoForm, SoraVideoForm, GeminiImageForm, ScriptForm
from .services import ProjectService, VideoService, ImageService, APIService, N8nService, SceneService, VideoCompositionService, ValidationException, ServiceException, ImageGenerationException
from django.template.loader import render_to_string
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.forms import SetPasswordForm
from django.utils.crypto import get_random_string
from django.conf import settings
import logging
import re

logger = logging.getLogger(__name__)


from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def no_permissions(request):
    """
    View para mostrar mensaje de 'sin permisos' y botones de redirección
    según roles (usar, ver, crear, editar, borrar).
    Detecta roles en grupos, atributos o permisos relacionados.
    """
    user = request.user
    expected_roles = {"usar", "ver", "crear", "editar", "borrar"}

    roles_found = set()

    # 1) Grupos
    try:
        groups = {g.strip().lower() for g in user.groups.values_list("name", flat=True)}
        roles_found |= (groups & expected_roles)
    except Exception:
        pass

    # 2) Atributo ManyToMany 'roles'
    if hasattr(user, "roles"):
        try:
            role_names = {r.strip().lower() for r in user.roles.values_list("name", flat=True)}
            roles_found |= (role_names & expected_roles)
        except Exception:
            try:
                roles_found |= {r.name.strip().lower() for r in user.roles.all()} & expected_roles
            except Exception:
                pass

    # 3) Campo string 'role'
    if hasattr(user, "role"):
        val = getattr(user, "role")
        if isinstance(val, str):
            for token in val.split(","):
                t = token.strip().lower()
                if t in expected_roles:
                    roles_found.add(t)

    # 4) Permisos (busca subcadenas)
    try:
        perms = user.get_all_permissions()
        for perm in perms:
            for role in expected_roles:
                if role in perm:
                    roles_found.add(role)
    except Exception:
        pass

    # 5) Permisos de gestión de usuarios (original)
    management_perms = {
        "auth.add_user", "auth.change_user", "auth.view_user", "auth.delete_user"
    }
    try:
        user_perms_full = set(user.get_all_permissions())
    except Exception:
        user_perms_full = set()

    # Si tiene solo permisos de gestión de usuarios O alguno de los roles clave
    has_management_perms = bool(user_perms_full) and user_perms_full.issubset(management_perms)
    # Definir roles que también cuentan como "solo gestión"
    management_roles = {"crear", "ver", "borrar", "editar", "admin"}
    has_management_roles = bool(roles_found & management_roles)
    only_management = has_management_perms or has_management_roles

    no_perms = not (user_perms_full or roles_found)

    # Contexto
    context = {
        "only_management": only_management,
        "no_perms": no_perms,
        "roles_found": sorted(list(roles_found)),
        "can_usar": "usar" in roles_found,
        "can_ver": "ver" in roles_found,
        "can_crear": "crear" in roles_found,
        "can_editar": "editar" in roles_found,
        "can_borrar": "borrar" in roles_found,
    }

    return render(request, "no_permissions.html", context)



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
# LOGIN
# ====================

class LoginView(View):
    """Inicio de sesión"""
    template_name = 'login/login.html'

    def get_context(self, username=''):
        """Contexto extra para el template"""
        return {
            'hide_header': True,
        }

    def get(self, request):
        return render(request, self.template_name, self.get_context())

    def post(self, request):
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Bienvenido, {user.username} 👋")

            # After login, if the user has no permissions at all, redirect to a friendly page
            # that explains the account is active but no permissions have been assigned.
            # Also if the user's permissions are only user-management related, show a variant
            # that includes a button to go to the user management panel.
            user_perms = user.get_all_permissions()
            management_perms = set([
                'auth.add_user', 'auth.change_user', 'auth.view_user', 'auth.delete_user'
            ])

            if not user_perms:
                return redirect('core:no_permissions')

            # if all permissions are subset of management_perms, redirect to same page
            if user_perms and set(user_perms).issubset(management_perms):
                return redirect('core:no_permissions')

            return redirect('core:dashboard')
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")
            return render(request, self.template_name, self.get_context(username=username))


# ====================
# LOGOUT
# ====================

class LogoutView(View):
    """Cerrar sesión"""
    def get(self, request):
        logout(request)
        messages.info(request, "Has cerrado sesión correctamente 👋")
        return redirect('core:login')


class SignupView(View):
    """Registro de nuevos usuarios"""
    template_name = 'login/signup.html'

    def get_context(self):
        """Contexto extra para el template"""
        return {
            'hide_header': True,
        }

    def get(self, request):
        return render(request, self.template_name, self.get_context())

    def post(self, request):
        from django.contrib.auth.models import User
        
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        password_confirm = request.POST.get('password_confirm', '').strip()

        # Validaciones básicas
        if not all([username, email, password, password_confirm]):
            messages.error(request, 'Todos los campos son requeridos')
            return render(request, self.template_name, self.get_context())

        if password != password_confirm:
            messages.error(request, 'Las contraseñas no coinciden')
            return render(request, self.template_name, self.get_context())

        if len(password) < 8:
            messages.error(request, 'La contraseña debe tener al menos 8 caracteres')
            return render(request, self.template_name, self.get_context())

        # Verificar si el usuario ya existe
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Este nombre de usuario ya está en uso')
            return render(request, self.template_name, self.get_context())

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Este correo electrónico ya está registrado')
            return render(request, self.template_name, self.get_context())

        try:
            # Crear usuario
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            messages.success(request, f'Cuenta creada exitosamente. Bienvenido, {username}! 👋')
            # Autenticar y hacer login automáticamente
            login(request, user)
            return redirect('core:dashboard')
        except Exception as e:
            messages.error(request, f'Error al crear la cuenta: {str(e)}')
            return render(request, self.template_name, self.get_context())

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
        context['show_header'] = True
        
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
                    'video_type': script.video_type or 'general',
                    'video_orientation': script.video_orientation or '16:9',
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
        video_type = request.POST.get('video_type', 'general')
        video_orientation = request.POST.get('video_orientation', '16:9')
        generate_previews = request.POST.get('generate_previews', 'true').lower() == 'true'
        
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
                video_type=video_type,
                video_orientation=video_orientation,
                generate_previews=generate_previews,
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


class AgentAIAssistantView(BreadcrumbMixin, View):
    """Vista para el asistente de escritura con IA"""
    template_name = 'agent/ai_assistant.html'
    
    def get_project(self):
        project_id = self.kwargs['project_id']
        return get_object_or_404(Project, pk=project_id)
    
    def get_breadcrumbs(self):
        project = self.get_project()
        return [
            {'label': project.name, 'url': reverse('core:project_detail', args=[project.pk])},
            {'label': 'Asistente IA', 'url': None}
        ]
    
    def get(self, request, project_id):
        project = self.get_project()
        
        context = {
            'project': project,
            'breadcrumbs': self.get_breadcrumbs()
        }
        
        return render(request, self.template_name, context)


class AgentAIAssistantInitView(View):
    """API para inicializar sesión de chat con el asistente"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, project_id):
        """Inicializa una nueva sesión de chat"""
        try:
            from .services import OpenAIScriptAssistantService
            
            service = OpenAIScriptAssistantService()
            session_data = service.create_chat_session()
            
            return JsonResponse({
                'status': 'success',
                **session_data
            })
            
        except Exception as e:
            logger.error(f"Error al inicializar sesión IA: {e}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)


class AgentAIAssistantChatView(View):
    """API para enviar mensajes al asistente"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, project_id):
        """Envía un mensaje y obtiene respuesta del asistente"""
        try:
            import json
            from .services import OpenAIScriptAssistantService
            
            data = json.loads(request.body)
            session_data = data.get('session_data')
            user_message = data.get('user_message')
            current_script = data.get('current_script', '')
            
            if not session_data or not user_message:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Datos incompletos'
                }, status=400)
            
            service = OpenAIScriptAssistantService()
            result = service.send_message(session_data, user_message, current_script)
            
            return JsonResponse({
                'status': 'success',
                **result
            })
            
        except Exception as e:
            logger.error(f"Error en chat IA: {e}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
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


class SceneCreateManualView(View):
    """Crear una escena manualmente (Paso 2 o 3)"""
    
    def post(self, request, script_id):
        try:
            script = get_object_or_404(Script, id=script_id)
            project = script.project
            
            import json
            data = json.loads(request.body)
            
            logger.info(f"Creando escena manual para script {script_id}: {data}")
            
            # Obtener datos básicos
            scene_type = data.get('scene_type', 'ai_generated')  # 'ai_generated', 'video_upload', 'freepik_video'
            script_text = data.get('script_text', '')
            summary = data.get('summary', script_text[:100] if script_text else 'Escena manual')
            
            # Calcular el siguiente order
            max_order = script.db_scenes.aggregate(Max('order'))['order__max'] or -1
            new_order = max_order + 1
            
            # Calcular scene_id
            scene_count = script.db_scenes.count()
            scene_id = f"Escena {scene_count + 1}"
            
            # Obtener y convertir ai_service si es necesario
            ai_service = data.get('ai_service', 'gemini_veo')
            # Convertir valores antiguos de heygen a heygen_v2 (backward compatibility)
            if ai_service == 'heygen':
                logger.info(f"  Convirtiendo ai_service 'heygen' a 'heygen_v2'")
                ai_service = 'heygen_v2'
            
            # Crear escena base
            new_scene = Scene.objects.create(
                script=script,
                project=project,
                scene_id=scene_id,
                summary=summary,
                script_text=script_text,
                duration_sec=data.get('duration_sec', 8),
                avatar='no',
                platform='manual',
                broll=[],
                order=new_order,
                is_included=True,
                ai_service=ai_service,
                ai_config=data.get('ai_config', {}),
                video_status='pending' if scene_type == 'ai_generated' else 'completed',
                version=1
            )
            
            # Manejar según el tipo
            if scene_type == 'video_upload':
                # El video se subirá en otra petición con el video file
                # Por ahora solo creamos la escena
                pass
            elif scene_type == 'freepik_video':
                # Descargar video de Freepik
                freepik_resource_id = data.get('freepik_resource_id')
                if freepik_resource_id:
                    from .services import SceneService
                    scene_service = SceneService()
                    scene_service._download_freepik_video(new_scene, freepik_resource_id)
            # Si es 'ai_generated', la escena queda pendiente para generar
            
            logger.info(f"✓ Escena manual creada: {new_scene.id} ({scene_id})")
            
            return JsonResponse({
                'status': 'success',
                'message': 'Escena creada exitosamente',
                'scene_id': new_scene.id,
                'scene_data': {
                    'id': new_scene.id,
                    'scene_id': new_scene.scene_id,
                    'summary': new_scene.summary,
                    'script_text': new_scene.script_text,
                    'ai_service': new_scene.ai_service,
                    'ai_config': new_scene.ai_config,
                    'order': new_scene.order,
                    'video_status': new_scene.video_status
                }
            })
            
        except Exception as e:
            logger.error(f"Error al crear escena manual: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'status': 'error',
                'message': f'Error: {str(e)}'
            }, status=500)


class SceneGenerateAIImageView(View):
    """Generar imagen preview con IA usando un prompt personalizado"""
    
    def post(self, request, scene_id):
        try:
            scene = get_object_or_404(Scene, id=scene_id)
            
            import json
            data = json.loads(request.body)
            prompt = data.get('prompt', '').strip()
            
            if not prompt:
                return JsonResponse({
                    'status': 'error',
                    'message': 'El prompt es requerido'
                }, status=400)
            
            logger.info(f"Generando imagen con IA para escena {scene_id} con prompt: {prompt[:100]}...")
            
            # Usar SceneService para generar la imagen
            from .services import SceneService
            scene_service = SceneService()
            
            # Modificar temporalmente el script_text para usar el prompt personalizado
            # Guardamos el original
            original_script_text = scene.script_text
            original_summary = scene.summary
            
            # Construir prompt mejorado
            enhanced_prompt = f"""
Create a cinematic preview image for a video scene.

Custom prompt: {prompt}

Scene summary: {scene.summary}
Scene content: {scene.script_text[:200]}...

Visual elements to include: {', '.join(scene.broll[:3]) if scene.broll else 'general scene'}

Style: Photorealistic, professional video production, cinematic lighting, high quality, 16:9 aspect ratio.
This is a preview thumbnail for a video, make it visually engaging and representative of the content.
"""
            
            # Generar imagen
            gcs_path = scene_service.generate_preview_image_with_prompt(scene, enhanced_prompt)
            
            logger.info(f"✓ Imagen generada con IA para escena {scene_id}: {gcs_path}")
            
            return JsonResponse({
                'status': 'success',
                'message': 'Imagen generada exitosamente',
                'gcs_path': gcs_path
            })
            
        except Exception as e:
            logger.error(f"Error al generar imagen con IA para escena {scene_id}: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'status': 'error',
                'message': f'Error: {str(e)}'
            }, status=500)


class SceneUploadVideoView(View):
    """Subir video manual a una escena"""
    
    def post(self, request, scene_id):
        try:
            scene = get_object_or_404(Scene, id=scene_id)
            
            if 'video_file' not in request.FILES:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No se proporcionó archivo de video'
                }, status=400)
            
            video_file = request.FILES['video_file']
            
            # Validar tipo de archivo
            allowed_extensions = ['.mp4', '.mov', '.avi', '.webm']
            file_ext = os.path.splitext(video_file.name)[1].lower()
            if file_ext not in allowed_extensions:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Formato no soportado. Use: {", ".join(allowed_extensions)}'
                }, status=400)
            
            # Subir a GCS
            from .storage.gcs import gcs_storage
            from datetime import datetime
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_filename = os.path.basename(video_file.name)
            gcs_destination = f"projects/{scene.project.id}/scenes/{scene.id}/manual_upload_{timestamp}_{safe_filename}"
            
            logger.info(f"Subiendo video manual a GCS: {safe_filename}")
            gcs_path = gcs_storage.upload_django_file(video_file, gcs_destination)
            
            # Marcar escena como completada
            scene.video_gcs_path = gcs_path
            scene.video_status = 'completed'
            scene.save()
            
            logger.info(f"✓ Video manual subido para escena {scene.id}: {gcs_path}")
            
            return JsonResponse({
                'status': 'success',
                'message': 'Video subido exitosamente',
                'gcs_path': gcs_path
            })
            
        except Exception as e:
            logger.error(f"Error al subir video manual: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Error: {str(e)}'
            }, status=500)


class SceneUploadCustomImageView(View):
    """Subir imagen personalizada como preview de una escena"""
    
    def post(self, request, scene_id):
        try:
            scene = get_object_or_404(Scene, id=scene_id)
            
            if 'image_file' not in request.FILES:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No se proporcionó archivo de imagen'
                }, status=400)
            
            image_file = request.FILES['image_file']
            
            # Validar tipo de archivo
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
            file_ext = os.path.splitext(image_file.name)[1].lower()
            if file_ext not in allowed_extensions:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Formato no soportado. Use: {", ".join(allowed_extensions)}'
                }, status=400)
            
            # Validar tamaño (max 10MB)
            max_size = 10 * 1024 * 1024  # 10MB
            if image_file.size > max_size:
                return JsonResponse({
                    'status': 'error',
                    'message': 'La imagen es demasiado grande. Tamaño máximo: 10MB'
                }, status=400)
            
            # Subir a GCS
            from .storage.gcs import gcs_storage
            from datetime import datetime
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_filename = os.path.basename(image_file.name)
            gcs_destination = f"projects/{scene.project.id}/scenes/{scene.id}/custom_preview_{timestamp}_{safe_filename}"
            
            logger.info(f"Subiendo imagen personalizada a GCS: {safe_filename}")
            gcs_path = gcs_storage.upload_django_file(image_file, gcs_destination)
            
            # Establecer como preview de la escena
            scene.preview_image_path = gcs_path
            scene.save()
            
            logger.info(f"✓ Imagen personalizada subida para escena {scene.id}: {gcs_path}")
            
            return JsonResponse({
                'status': 'success',
                'message': 'Imagen subida exitosamente',
                'gcs_path': gcs_path
            })
            
        except Exception as e:
            logger.error(f"Error al subir imagen personalizada: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Error: {str(e)}'
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
                ai_service = data['ai_service']
                # Convertir valores antiguos de heygen a heygen_v2 (backward compatibility)
                if ai_service == 'heygen':
                    logger.info(f"  Convirtiendo ai_service 'heygen' a 'heygen_v2'")
                    ai_service = 'heygen_v2'
                scene.ai_service = ai_service
                logger.info(f"  ai_service actualizado a: {ai_service}")
            
            # Actualizar ai_config
            if 'ai_config' in data:
                scene.ai_config.update(data['ai_config'])
                logger.info(f"  ai_config actualizado: {scene.ai_config}")
            
            # Actualizar script_text si viene
            if 'script_text' in data:
                scene.script_text = data['script_text']
                logger.info(f"  script_text actualizado")
            
            # Actualizar order si viene (para drag & drop)
            if 'order' in data:
                scene.order = int(data['order'])
                logger.info(f"  order actualizado a: {data['order']}")
            
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
            
            # Extraer el scene_id base sin el sufijo de versión anterior si existe
            base_scene_id = original_scene.scene_id
            if ' v' in base_scene_id:
                base_scene_id = base_scene_id.split(' v')[0]
            
            # Buscar la versión más alta existente para esta escena base
            # Esto evita conflictos si ya existe una versión posterior
            max_version = Scene.objects.filter(
                script=original_scene.script,
                scene_id__startswith=base_scene_id
            ).aggregate(models.Max('version'))['version__max'] or 0
            
            new_version = max_version + 1
            
            # Generar nuevo scene_id único
            new_scene_id = f"{base_scene_id} v{new_version}" if new_version > 1 else base_scene_id
            
            # Verificar que no exista (por seguridad adicional)
            counter = 0
            temp_scene_id = new_scene_id
            while Scene.objects.filter(script=original_scene.script, scene_id=temp_scene_id).exists():
                counter += 1
                temp_scene_id = f"{base_scene_id} v{new_version + counter}"
                logger.warning(f"scene_id {new_scene_id} ya existe, probando con {temp_scene_id}")
            
            new_scene_id = temp_scene_id
            
            logger.info(f"  scene_id original: {original_scene.scene_id}")
            logger.info(f"  scene_id nuevo: {new_scene_id}")
            logger.info(f"  versión nueva: {new_version}")
            
            new_scene = Scene.objects.create(
                script=original_scene.script,
                project=original_scene.project,
                scene_id=new_scene_id,
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


# ====================
# FREEPIK API VIEWS
# ====================

class FreepikSearchImagesView(View):
    """Buscar imágenes en Freepik Stock"""
    
    def get(self, request):
        """
        Busca imágenes en Freepik
        
        Query params:
            - query: Término de búsqueda (requerido)
            - orientation: horizontal, vertical, square (opcional)
            - page: Número de página (default: 1)
            - limit: Límite de resultados (default: 20, max: 200)
        """
        from .ai_services.freepik import FreepikClient, FreepikOrientation
        from django.conf import settings
        
        query = request.GET.get('query')
        if not query:
            return JsonResponse({
                'status': 'error',
                'message': 'El parámetro "query" es requerido'
            }, status=400)
        
        if not settings.FREEPIK_API_KEY:
            return JsonResponse({
                'status': 'error',
                'message': 'FREEPIK_API_KEY no configurada'
            }, status=500)
        
        try:
            client = FreepikClient(api_key=settings.FREEPIK_API_KEY)
            
            # Parsear orientación
            orientation = None
            orientation_str = request.GET.get('orientation', '').lower()
            if orientation_str == 'horizontal':
                orientation = FreepikOrientation.HORIZONTAL
            elif orientation_str == 'vertical':
                orientation = FreepikOrientation.VERTICAL
            elif orientation_str == 'square':
                orientation = FreepikOrientation.SQUARE
            
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 20))
            license_filter = request.GET.get('license', 'all')  # all, free, premium
            
            # Buscar
            results = client.search_images(
                query=query,
                orientation=orientation,
                page=page,
                limit=limit,
                license_filter=license_filter
            )
            
            logger.info(f"Freepik search for '{query}': Found {len(results.get('data', []))} raw results")
            
            # Log de los primeros IDs para debugging
            if results.get('data'):
                first_ids = [item.get('id') for item in results.get('data', [])[:3]]
                logger.info(f"First 3 resource IDs from Freepik: {first_ids}")
            
            # Parsear resultados para simplificar
            parsed_results = client.parse_search_results(results, license_filter=license_filter)
            
            logger.info(f"Freepik search for '{query}': Parsed {len(parsed_results)} results with images")
            
            # Log de un resultado de ejemplo para debugging
            if parsed_results:
                sample = parsed_results[0]
                logger.info(f"Sample result: ID={sample['id']}, title='{sample['title'][:50]}', has_thumbnail={bool(sample['thumbnail'])}, has_preview={bool(sample['preview'])}, is_premium={sample.get('is_premium', 'NOT SET')}")
                
                # Log de las primeras 3 para ver distribución de premium
                for i, result in enumerate(parsed_results[:3]):
                    logger.info(f"  Result {i+1}: ID={result['id']}, is_premium={result.get('is_premium')}")
            
            return JsonResponse({
                'status': 'success',
                'results': parsed_results,
                'meta': results.get('meta', {}),
                'query': query
            })
            
        except Exception as e:
            logger.error(f"Error en búsqueda de Freepik: {e}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)


class FreepikSetSceneImageView(View):
    """Establecer imagen de Freepik como preview/referencia de una escena"""
    
    def post(self, request, scene_id):
        """
        Descarga imagen de Freepik y la establece como preview de la escena
        
        Body (JSON):
            - resource_id: ID del recurso en Freepik (requerido)
            - download_url: URL de descarga de la imagen (requerido)
        """
        from .ai_services.freepik import FreepikClient
        from django.conf import settings
        from .storage.gcs import gcs_storage
        import json
        import requests
        import tempfile
        import os
        
        try:
            scene = get_object_or_404(Scene, id=scene_id)
            data = json.loads(request.body)
            
            resource_id = data.get('resource_id')
            
            if not resource_id:
                return JsonResponse({
                    'status': 'error',
                    'message': 'resource_id es requerido'
                }, status=400)
            
            # Obtener URL de descarga real usando la API de Freepik
            logger.info(f"Obteniendo detalles de imagen de Freepik: {resource_id}")
            
            if not settings.FREEPIK_API_KEY:
                return JsonResponse({
                    'status': 'error',
                    'message': 'FREEPIK_API_KEY no configurada'
                }, status=500)
            
            client = FreepikClient(api_key=settings.FREEPIK_API_KEY)
            
            # Intentar usar el endpoint oficial de download
            image_url = None
            try:
                download_response = client.get_download_url(resource_id, image_size='large')
                
                # Extraer URL de descarga
                if 'data' in download_response:
                    data = download_response['data']
                    # La API puede devolver 'signed_url', 'url' o ambas
                    image_url = data.get('signed_url') or data.get('url')
                    logger.info(f"✓ URL de descarga obtenida del endpoint oficial")
            
            except Exception as e:
                error_str = str(e)
                logger.warning(f"No se pudo usar endpoint de descarga: {error_str}")
                
                # Si es un recurso Premium, usar fallback al preview
                if '403' in error_str or 'Premium' in error_str or 'Forbidden' in error_str:
                    logger.info(f"Recurso Premium detectado, usando preview/thumbnail como fallback")
                    
                    # Obtener detalles del recurso para extraer preview
                    try:
                        details = client.get_resource_details(resource_id)
                        logger.info(f"Details response keys: {details.keys() if isinstance(details, dict) else 'Not a dict'}")
                        
                        if 'data' in details:
                            item = details['data']
                            logger.info(f"Item keys: {item.keys() if isinstance(item, dict) else 'Not a dict'}")
                            
                            # Intentar obtener preview de diferentes lugares
                            # 1. Desde preview.url
                            if 'preview' in item and isinstance(item['preview'], dict):
                                preview_url = item['preview'].get('url')
                                if preview_url and isinstance(preview_url, str):
                                    image_url = preview_url
                                    logger.info(f"✓ Usando preview.url: {image_url[:80]}")
                            
                            # 2. Desde image.source.url (backup)
                            if not image_url and 'image' in item and isinstance(item['image'], dict):
                                if 'source' in item['image'] and isinstance(item['image']['source'], dict):
                                    source_url = item['image']['source'].get('url')
                                    if source_url and isinstance(source_url, str):
                                        image_url = source_url
                                        logger.info(f"✓ Usando image.source.url: {image_url[:80]}")
                            
                            if image_url:
                                logger.info(f"✓ Preview/thumbnail encontrado para recurso Premium")
                            else:
                                logger.error(f"No se encontró URL de preview en detalles del recurso")
                    except Exception as detail_error:
                        logger.error(f"Error obteniendo detalles del recurso: {detail_error}")
                else:
                    raise
            
            if not image_url:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No se pudo obtener URL de imagen de Freepik. Es posible que sea un recurso Premium.'
                }, status=400)
            
            logger.info(f"Descargando imagen desde: {image_url[:80]}...")
            
            # Descargar imagen
            response = requests.get(image_url, timeout=60, stream=True)
            response.raise_for_status()
            
            # Guardar temporalmente
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    tmp_file.write(chunk)
                tmp_path = tmp_file.name
            
            try:
                # Subir a GCS
                gcs_path = f"projects/{scene.project.id}/scenes/{scene.id}/preview_freepik.jpg"
                
                with open(tmp_path, 'rb') as image_file:
                    gcs_full_path = gcs_storage.upload_from_bytes(
                        file_content=image_file.read(),
                        destination_path=gcs_path,
                        content_type='image/jpeg'
                    )
                
                # Actualizar escena
                scene.preview_image_gcs_path = gcs_full_path
                scene.preview_image_status = 'completed'
                scene.image_source = 'freepik_stock'
                scene.freepik_resource_id = resource_id
                scene.save(update_fields=[
                    'preview_image_gcs_path',
                    'preview_image_status',
                    'image_source',
                    'freepik_resource_id',
                    'updated_at'
                ])
                
                logger.info(f"✓ Imagen de Freepik establecida para escena {scene.scene_id}")
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Imagen de Freepik establecida correctamente',
                    'gcs_path': gcs_full_path
                })
                
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            
        except Exception as e:
            logger.error(f"Error al establecer imagen de Freepik: {e}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)


class FreepikSearchVideosView(View):
    """Buscar videos en Freepik Stock"""
    
    def get(self, request):
        """
        Busca videos en Freepik
        
        Query params:
            - query: Término de búsqueda (requerido)
            - orientation: horizontal, vertical (opcional)
            - page: Número de página (default: 1)
            - limit: Límite de resultados (default: 20, max: 200)
        """
        from .ai_services.freepik import FreepikClient, FreepikOrientation
        from django.conf import settings
        
        query = request.GET.get('query')
        if not query:
            return JsonResponse({
                'status': 'error',
                'message': 'El parámetro "query" es requerido'
            }, status=400)
        
        if not settings.FREEPIK_API_KEY:
            return JsonResponse({
                'status': 'error',
                'message': 'FREEPIK_API_KEY no configurada'
            }, status=500)
        
        try:
            client = FreepikClient(api_key=settings.FREEPIK_API_KEY)
            
            # Parsear orientación
            orientation = None
            orientation_str = request.GET.get('orientation', '').lower()
            if orientation_str == 'horizontal':
                orientation = FreepikOrientation.HORIZONTAL
            elif orientation_str == 'vertical':
                orientation = FreepikOrientation.VERTICAL
            
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 20))
            
            # Buscar
            results = client.search_videos(
                query=query,
                orientation=orientation,
                page=page,
                limit=limit
            )
            
            # Parsear resultados
            parsed_results = client.parse_search_results(results)
            
            return JsonResponse({
                'status': 'success',
                'results': parsed_results,
                'meta': results.get('meta', {}),
                'query': query
            })
            
        except Exception as e:
            logger.error(f"Error en búsqueda de videos en Freepik: {e}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)


# ====================
# VUELA.AI API VIEWS
# ====================

class VuelaAIValidateTokenView(View):
    """Validar token de Vuela.ai"""
    
    def post(self, request):
        """Valida el token API de Vuela.ai"""
        from .ai_services.vuela_ai import VuelaAIClient
        from django.conf import settings
        
        if not settings.VUELA_AI_API_KEY:
            return JsonResponse({
                'status': 'error',
                'message': 'VUELA_AI_API_KEY no configurada'
            }, status=500)
        
        try:
            client = VuelaAIClient(api_key=settings.VUELA_AI_API_KEY)
            result = client.validate_token()
            
            return JsonResponse({
                'status': 'success',
                'validation': result
            })
            
        except Exception as e:
            logger.error(f"Error al validar token de Vuela.ai: {e}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)


class VuelaAIListVideosView(View):
    """Listar videos generados en Vuela.ai"""
    
    def get(self, request):
        """
        Lista videos de Vuela.ai
        
        Query params:
            - page: Número de página (default: 1)
            - limit: Límite de resultados (default: 10)
            - search: Término de búsqueda (opcional)
        """
        from .ai_services.vuela_ai import VuelaAIClient
        from django.conf import settings
        
        if not settings.VUELA_AI_API_KEY:
            return JsonResponse({
                'status': 'error',
                'message': 'VUELA_AI_API_KEY no configurada'
            }, status=500)
        
        try:
            client = VuelaAIClient(api_key=settings.VUELA_AI_API_KEY)
            
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 10))
            search = request.GET.get('search')
            
            result = client.list_videos(page=page, limit=limit, search=search)
            
            return JsonResponse({
                'status': 'success',
                'videos': result
            })
            
        except Exception as e:
            logger.error(f"Error al listar videos de Vuela.ai: {e}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)


class VuelaAIVideoDetailsView(View):
    """Obtener detalles de un video de Vuela.ai"""
    
    def get(self, request, video_id):
        """Obtiene detalles de un video específico"""
        from .ai_services.vuela_ai import VuelaAIClient
        from django.conf import settings
        
        if not settings.VUELA_AI_API_KEY:
            return JsonResponse({
                'status': 'error',
                'message': 'VUELA_AI_API_KEY no configurada'
            }, status=500)
        
        try:
            client = VuelaAIClient(api_key=settings.VUELA_AI_API_KEY)
            result = client.get_video_details(video_id)
            
            return JsonResponse({
                'status': 'success',
                'video': result
            })
            
        except Exception as e:
            logger.error(f"Error al obtener detalles de video Vuela.ai: {e}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
        
# ====================
# MANAGEMENT USERS
# ====================

class UserMenuView(View):
    """
    User management view with permission-based access control.
    
    Access logic:
    - Users with view_user, change_user, or delete_user can access the admin panel
    - Users with add_user can access ONLY the create panel (not the admin list)
    - Superusers can access everything
    """
    login_url = 'core:dashboard'
    template_name = 'users/menu.html'

    def dispatch(self, request, *args, **kwargs):
        # Check if user has at least one permission to manage users
        # Compute granular admin/create access. We intentionally treat a user
        # that only has add_user (crear) as NOT having admin access even if they
        # accidentally also received view_user. Admin access requires change/delete
        # or view when the user isn't a create-only account.
        has_change = request.user.has_perm('auth.change_user')
        has_delete = request.user.has_perm('auth.delete_user')
        has_view = request.user.has_perm('auth.view_user')
        has_add = request.user.has_perm('auth.add_user')

        # Superuser shortcut
        if request.user.is_superuser:
            has_admin_access = True
            has_create_access = True
        else:
            # Admin access if change or delete
            if has_change or has_delete:
                has_admin_access = True
            else:
                # If only view is present, allow admin access only if user is NOT a create-only account
                is_create_only = has_add and not (has_change or has_delete)
                has_admin_access = has_view and not is_create_only

            has_create_access = has_add
        
        # If user has neither admin nor create permissions, deny access
        if not (has_admin_access or has_create_access):
            messages.error(request, 'No tienes permiso para acceder a esta página.')
            return redirect(self.login_url)
        
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        # Determine access flags for template and data loading (same logic as dispatch)
        has_change = request.user.has_perm('auth.change_user')
        has_delete = request.user.has_perm('auth.delete_user')
        has_view = request.user.has_perm('auth.view_user')
        has_add = request.user.has_perm('auth.add_user')

        if request.user.is_superuser:
            has_admin_access = True
            has_create_access = True
        else:
            if has_change or has_delete:
                has_admin_access = True
            else:
                is_create_only = has_add and not (has_change or has_delete)
                has_admin_access = has_view and not is_create_only

            has_create_access = has_add

        form = CustomUserCreationForm()

        # Load groups always (needed for the create form). Only load the
        # full users list when the user has admin access.
        groups = Group.objects.all()
        if has_admin_access:
            # Prefetch groups para evitar N+1 queries
            users = User.objects.prefetch_related('groups').all()
        else:
            # For create-only users, don't load the admin list
            users = []

        # Determine whether the current user belongs to an "editar" role or has change_user
        can_reset_password = (
            request.user.is_superuser or
            request.user.has_perm('auth.change_user') or
            request.user.groups.filter(name__icontains='editar').exists()
        )

        return render(request, self.template_name, {
            'users': users,
            'form': form,
            'groups': groups,
            'can_reset_password': can_reset_password,
            'has_admin_access': has_admin_access,
            'has_create_access': has_create_access,
        })

    # ------------------------------
    #  VALIDACIÓN DE CONTRASEÑA
    # ------------------------------
    @staticmethod
    def validar_password(password):
        if len(password) < 6:
            return "La contraseña debe tener al menos 6 caracteres."
        if not re.search(r'[a-z]', password):
            return "La contraseña debe contener al menos una letra minúscula."
        if not re.search(r'[A-Z]', password):
            return "La contraseña debe contener al menos una letra mayúscula."
        if not re.search(r'\d', password):
            return "La contraseña debe contener al menos un número."
        if not re.search(r'[^A-Za-z0-9]', password):
            return "La contraseña debe contener al menos un carácter especial."
        return None

    def post(self, request):
        # --- Acciones AJAX individuales ---
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            accion = request.POST.get('accion')

            # Cambiar contraseña
            if accion == 'cambiar_password':
                user_id = request.POST.get('usuario_id')
                nueva = request.POST.get('nueva_password')
                # Validar que la nueva contraseña no esté vacía
                if not nueva or nueva.strip() == '':
                    return JsonResponse({'success': False, 'error': 'La nueva contraseña no puede estar vacía.'})

                # Validar complejidad de la contraseña
                error_pwd = self.validar_password(nueva)
                if error_pwd:
                    return JsonResponse({'success': False, 'error': error_pwd})

                # Permission: only allow if user is changing own password or has the 'editar' role / change permission
                has_edit_role = (
                    request.user.is_superuser or
                    request.user.has_perm('auth.change_user') or
                    request.user.groups.filter(name__icontains='editar').exists()
                )

                if not (has_edit_role or str(request.user.id) == str(user_id)):
                    return JsonResponse({'success': False, 'error': 'No tienes permiso para cambiar la contraseña.'})
                try:
                    user = User.objects.get(id=user_id)
                    user.set_password(nueva)
                    user.save()
                    return JsonResponse({'success': True})
                except User.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'Usuario no encontrado'})
                except Exception as e:
                    return JsonResponse({'success': False, 'error': str(e)})

            # Eliminar usuario individual
            elif accion == 'eliminar_usuario':
                user_id = request.POST.get('usuario_id')
                # Permission: require delete_user
                if not request.user.has_perm('auth.delete_user'):
                    return JsonResponse({'success': False, 'error': 'No tienes permiso para eliminar usuarios.'})
                try:
                    if str(request.user.id) == str(user_id):
                        return JsonResponse({'success': False, 'error': 'No puedes eliminar tu propio usuario.'})
                    user = User.objects.get(id=user_id)
                    user.delete()
                    return JsonResponse({'success': True})
                except User.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'Usuario no encontrado'})
                except Exception as e:
                    return JsonResponse({'success': False, 'error': str(e)})

            # --- Eliminación masiva o edición existente ---
            # Server-side permission checks for bulk operations
            # If the request tries to update users (usuarios[...] keys) require change permission
            if any(k.startswith('usuarios[') for k in request.POST):
                if not request.user.has_perm('auth.change_user'):
                    return JsonResponse({'success': False, 'error': 'No tienes permiso para modificar usuarios.'})

            try:
                # Si se está eliminando en masa
                if any(k.startswith('usuarios_a_eliminar') for k in request.POST):
                    # Permission: require delete_user for bulk deletes
                    if not request.user.has_perm('auth.delete_user'):
                        return JsonResponse({'success': False, 'error': 'No tienes permiso para eliminar usuarios.'})
                    ids_a_eliminar = [
                        request.POST[k] for k in request.POST if k.startswith('usuarios_a_eliminar')
                    ]

                    if str(request.user.id) in ids_a_eliminar:
                        return JsonResponse({
                            'success': False,
                            'error': 'No puedes eliminar tu propio usuario.'
                        })

                    eliminados = User.objects.filter(id__in=ids_a_eliminar)
                    count = eliminados.count()
                    eliminados.delete()
                    return JsonResponse({'success': True, 'deleted_count': count})

                # Si se están actualizando usuarios
                usuarios = []

                for key in request.POST:
                    if key.startswith('usuarios['):
                        idx = key.split('[')[1].split(']')[0]
                        campo = key.split('[')[2].split(']')[0]
                        valor = request.POST[key]

                        while len(usuarios) <= int(idx):
                            usuarios.append({})
                        usuarios[int(idx)][campo] = valor

                for u in usuarios:
                    if 'id' not in u:
                        continue

                    user = User.objects.get(id=u['id'])
                    nuevo_username = u.get('username', user.username).strip()
                    nuevo_email = u.get('email', user.email).strip()

                    if User.objects.exclude(id=user.id).filter(username=nuevo_username).exists():
                        return JsonResponse({
                            'success': False,
                            'error': f'El nombre de usuario "{nuevo_username}" ya está en uso.'
                        })

                    user.username = nuevo_username
                    user.email = nuevo_email
                    user.is_staff = u.get('is_staff', 'False').lower() == 'true'
                    user.is_active = u.get('is_active', 'False').lower() == 'true'
                    user.save()
                    # Update groups if provided (comma separated ids)
                    if 'groups' in u:
                        try:
                            group_ids = [int(x) for x in u['groups'].split(',') if x]
                            groups_qs = Group.objects.filter(id__in=group_ids)
                            user.groups.set(groups_qs)
                        except Exception:
                            # ignore malformed group input
                            pass

                return JsonResponse({'success': True})

            except IntegrityError:
                return JsonResponse({'success': False, 'error': 'Usuario duplicado.'})
            except Exception as e:
                print("❌ Error al guardar/eliminar:", e)
                return JsonResponse({'success': False, 'error': str(e)})

        # --- Creación normal (formulario clásico) ---
        # Ensure the requesting user has permission to create users
        if not request.user.has_perm('auth.add_user'):
            messages.error(request, 'No tienes permiso para crear usuarios.')
            return redirect('core:user_menu')

        # Use PendingUserCreationForm: create a user with a strong random password and set is_active=False
        form = PendingUserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                # generate a secure random hidden password
                random_pw = get_random_string(50)
                user.set_password(random_pw)
                user.is_active = False  # pending
                user.is_staff = 'staff' in request.POST
                user.save()

                # Assign groups
                group_ids = request.POST.getlist('groups') or request.POST.getlist('group')
                if group_ids:
                    groups_qs = Group.objects.filter(id__in=group_ids)
                    user.groups.set(groups_qs)

                # Build activation link
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                activation_url = request.build_absolute_uri(reverse('core:activate_account', args=[uid, token]))

                # Send activation email
                try:
                    context = {'user': user, 'activation_url': activation_url}
                    subject = 'Activa tu cuenta en Atenea'
                    message = render_to_string('users/activation_email.txt', context)
                    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
                    from django.core.mail import send_mail
                    send_mail(subject, message, from_email, [user.email], fail_silently=False)
                except Exception as e:
                    logger.error(f"Error enviando email de activación a {user.email}: {e}")

                messages.success(request, '✅ Usuario creado en estado pendiente. Se ha enviado un correo de activación.')
            except Exception as e:
                logger.exception('Error creando usuario pendiente')
                messages.error(request, f'Error creando usuario: {e}')
        else:
            friendly_names = {
                'username': 'Usuario',
                'email': 'Correo electrónico',
                'groups': 'Roles',
                '__all__': 'Error general'
            }
            for field, errors in form.errors.items():
                field_name = friendly_names.get(field, field.capitalize())
                for error in errors:
                    messages.error(request, f"{field_name}: {error}")

        return redirect('core:user_menu')


def activate_account(request, uidb64, token):
    """Activate account view: user follows email link, sets password, and is activated."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        # Validar token ANTES de usar el usuario
        if not default_token_generator.check_token(user, token):
            user = None #invalidar si token no coincide
    except Exception:
        user = None

    # If token is invalid or user not found, render an informative page instead of redirecting
    if user is None:
        return render(request, 'users/activation_invalid.html', {
            'user_obj': None,
            'message': 'El enlace de activación no es válido o ha expirado.'
        })

    # If someone else is currently authenticated on this browser, log them out
    # so the activation can proceed for the target account. This avoids errors
    # when trying to activate while another session is active.

    # verifica si la cuenta esta activa y redirije al login 
    if user.is_active:
        messages.info(request, 'Tu cuenta ya está activa. Puedes iniciar sesión.')
        return redirect('core:login')

    # If someone else is currently authenticated on this browser, log them out
    if request.user.is_authenticated and request.user.pk != user.pk:
        # logout the current session and inform the user
        logout(request)
        messages.info(request, 'La sesión anterior se ha cerrado para continuar con la activación de la cuenta.')
        
    # Procesar contraseña y activar (con logging y manejo de errores)
    if request.method == 'POST':
        logger.info(f"Activation POST received for uid={uidb64} user_id={getattr(user, 'pk', None)}")
        form = ActivationSetPasswordForm(user=user, data=request.POST)
        if form.is_valid():
            try:
                # Guardar la contraseña (SetPasswordForm.save() llama a user.save())
                form.save()

                # Marcar activo antes de guardar la contraseña
                user.is_active = True
                user.save(update_fields=["is_active"])
                # Refrescar desde la base de datos para verificar
                user.refresh_from_db()

                if user.is_active:
                    messages.success(request, "Tu cuenta ha sido activada. Ahora puedes iniciar sesión.")
                else:
                    messages.warning(request, "Tu contraseña se guardó pero no se pudo activar la cuenta automáticamente. Contacta con el administrador.")

                return redirect("core:login")

            except Exception as e:
                # Capturar cualquier excepción durante el guardado para depuración
                logger.exception(f"Exception during account activation for user {getattr(user, 'pk', None)}: {e}")
                messages.error(request, "Ocurrió un error al activar la cuenta. Por favor intenta de nuevo o contacta con el administrador.")
        else:
            # Form invalid: log details for debugging
            for field, errors in form.errors.items():
                messages.error(request, errors)
                break
    else:
        logger.info(f"Activation GET for uid={uidb64} user_id={getattr(user, 'pk', None)}")
        form = ActivationSetPasswordForm(user=user)

    return render(request, 'users/activate_account.html', {'form': form, 'user': user})
