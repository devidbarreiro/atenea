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
from django.http import Http404
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import permission_required
from django.utils import timezone
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Max, Q, Sum, Count
from django.contrib.auth import authenticate, login, logout
import os
from django.contrib.auth.models import User, Group
from .forms import CustomUserCreationForm, PendingUserCreationForm, ActivationSetPasswordForm
from django.db import IntegrityError
import json

from .models import Project, Video, Image, Audio, Script, Scene, Music, UserCredits, CreditTransaction, ServiceUsage
from .forms import VideoBaseForm, HeyGenAvatarV2Form, HeyGenAvatarIVForm, GeminiVeoVideoForm, SoraVideoForm, GeminiImageForm, AudioForm, ScriptForm
from .services import ProjectService, VideoService, ImageService, AudioService, APIService, SceneService, VideoCompositionService, ValidationException, ServiceException, ImageGenerationException, InvitationService
from .services.credits import CreditService, InsufficientCreditsException, RateLimitExceededException
# N8nService se importa dinámicamente en get_script_service() para compatibilidad
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


# ====================
# DOCUMENTACION USER
# ====================

# Vista principal de la documentación
def docs_home(request):
    return render(request, 'docs/docs_template.html')

# Vista para devolver la estructura de la documentación
def docs_structure(request):
    base_dir = os.path.join(settings.BASE_DIR, 'docs', 'api', 'services')

    def build_tree(path):
        tree = {}
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                tree[item] = build_tree(item_path)
            elif item.endswith('.md'):
                tree[item] = item_path  # Guardamos ruta completa temporalmente
        return tree

    structure = build_tree(base_dir)
    return JsonResponse(structure)

# Vista para devolver el contenido de un archivo markdown
def docs_md_view(request, path):
    md_file_path = os.path.join(settings.BASE_DIR, 'docs', 'api', 'services', path + '.md')
    
    if not os.path.exists(md_file_path):
        raise Http404("Documento no encontrado")
    
    with open(md_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return JsonResponse({'content': content})

# ====================
# HELPER FUNCTIONS
# ====================

def get_script_service():
    """
    Retorna el servicio de procesamiento de guiones según feature flag.
    Permite alternar entre n8n (legacy) y LangChain (nuevo) sin cambiar código.
    """
    from django.conf import settings
    if getattr(settings, 'USE_LANGCHAIN_AGENT', False):
        from core.services_agent import ScriptAgentService
        return ScriptAgentService()
    else:
        # Usar N8nService cuando USE_LANGCHAIN_AGENT=False (comportamiento legacy)
        from core.services import N8nService
        return N8nService()


def send_invitation_email(request, invitation):
    """
    Envía un email de invitación a un proyecto
    
    Args:
        request: HttpRequest para construir URLs absolutas
        invitation: ProjectInvitation a enviar
    """
    from .models import ProjectInvitation
    from django.core.mail import send_mail
    
    try:
        # Construir URL de aceptación
        accept_url = request.build_absolute_uri(
            reverse('core:accept_invitation', args=[invitation.token])
        )
        
        # Contexto para el template
        context = {
            'invitation': invitation,
            'project': invitation.project,
            'invited_by': invitation.invited_by,
            'accept_url': accept_url,
            'role_display': invitation.get_role_display(),
        }
        
        # Renderizar mensaje
        subject = f'Invitación para unirte al proyecto "{invitation.project.name}"'
        message = render_to_string('projects/invitation_email.txt', context)
        
        # Enviar email
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
        send_mail(
            subject,
            message,
            from_email,
            [invitation.email],
            fail_silently=False
        )
        
        logger.info(f"Email de invitación enviado a {invitation.email} para proyecto {invitation.project.id}")
        
    except Exception as e:
        logger.error(f"Error enviando email de invitación a {invitation.email}: {e}")
        # No lanzar excepción para no interrumpir el flujo


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
    
    def get_audio_service(self):
        return AudioService()
    
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
        return ProjectService.get_user_projects(self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['show_header'] = True
        
        # Obtener query de búsqueda
        search_query = self.request.GET.get('q', '').strip()
        context['search_query'] = search_query
        
        # Obtener proyectos del usuario para filtrar estadísticas
        user_projects = ProjectService.get_user_projects(self.request.user)
        user_project_ids = user_projects.values_list('id', flat=True)
        
        # Agregar estadísticas filtradas por items del usuario (con y sin proyecto)
        from django.db.models import Q
        from core.models import Audio, Music
        context.update({
            'total_videos': Video.objects.filter(
                Q(project_id__in=user_project_ids) | Q(project__isnull=True, created_by=self.request.user)
            ).count(),
            'total_images': Image.objects.filter(
                Q(project_id__in=user_project_ids) | Q(project__isnull=True, created_by=self.request.user)
            ).count(),
            'total_scripts': Script.objects.filter(
                Q(project_id__in=user_project_ids) | Q(project__isnull=True, created_by=self.request.user)
            ).count(),
            'completed_videos': Video.objects.filter(
                Q(project_id__in=user_project_ids) | Q(project__isnull=True, created_by=self.request.user),
                status='completed'
            ).count(),
            'processing_videos': Video.objects.filter(
                Q(project_id__in=user_project_ids) | Q(project__isnull=True, created_by=self.request.user),
                status='processing'
            ).count(),
            'completed_scripts': Script.objects.filter(
                Q(project_id__in=user_project_ids) | Q(project__isnull=True, created_by=self.request.user),
                status='completed'
            ).count(),
        })
        
        # Construir filtro base para items del usuario
        base_filter = Q(project_id__in=user_project_ids) | Q(project__isnull=True, created_by=self.request.user)
        
        # Si hay búsqueda, agregar filtro de texto
        if search_query:
            # Videos: buscar en título y script
            video_search = Q(title__icontains=search_query) | Q(script__icontains=search_query)
            video_filter = base_filter & video_search
            
            # Imágenes: buscar en título y prompt
            image_search = Q(title__icontains=search_query) | Q(prompt__icontains=search_query)
            image_filter = base_filter & image_search
            
            # Audios: buscar en título y texto
            audio_search = Q(title__icontains=search_query) | Q(text__icontains=search_query)
            audio_filter = base_filter & audio_search
            
            # Música: buscar en nombre y prompt
            music_search = Q(name__icontains=search_query) | Q(prompt__icontains=search_query)
            music_filter = base_filter & music_search
            
            # Scripts: buscar en título y contenido del script
            script_search = Q(title__icontains=search_query) | Q(original_script__icontains=search_query)
            script_filter = base_filter & script_search
        else:
            video_filter = base_filter
            image_filter = base_filter
            audio_filter = base_filter
            music_filter = base_filter
            script_filter = base_filter
        
        # Obtener todos los items recientes mezclados (videos, imágenes, audios, música, scripts)
        recent_items = []
        
        # Videos
        videos = Video.objects.filter(video_filter).select_related('project').order_by('-created_at')
        video_service = self.get_video_service()
        for video in videos:
            item_data = {
                'type': 'video',
                'object': video,
                'id': video.id,
                'created_at': video.created_at,
                'title': video.title,
                'status': video.status,
                'project': video.project,
                'signed_url': None,
                'detail_url': reverse('core:video_detail', args=[video.id]),
                'delete_url': reverse('core:video_delete', args=[video.id]),
            }
            if video.status == 'completed' and video.gcs_path:
                try:
                    video_data = video_service.get_video_with_signed_urls(video)
                    item_data['signed_url'] = video_data.get('signed_url')
                except Exception:
                    pass
            recent_items.append(item_data)
        
        # Imágenes
        images = Image.objects.filter(image_filter).select_related('project').order_by('-created_at')
        image_service = self.get_image_service()
        for image in images:
            item_data = {
                'type': 'image',
                'object': image,
                'id': image.id,
                'created_at': image.created_at,
                'title': image.title,
                'status': image.status,
                'project': image.project,
                'signed_url': None,
                'detail_url': reverse('core:image_detail', args=[image.id]),
                'delete_url': reverse('core:image_delete', args=[image.id]),
            }
            if image.status == 'completed' and image.gcs_path:
                try:
                    image_data = image_service.get_image_with_signed_url(image)
                    item_data['signed_url'] = image_data.get('signed_url')
                except Exception:
                    pass
            recent_items.append(item_data)
        
        # Audios
        audios = Audio.objects.filter(audio_filter).select_related('project').order_by('-created_at')
        audio_service = self.get_audio_service()
        for audio in audios:
            item_data = {
                'type': 'audio',
                'object': audio,
                'id': audio.id,
                'created_at': audio.created_at,
                'title': audio.title,
                'status': audio.status,
                'project': audio.project,
                'signed_url': None,
                'detail_url': reverse('core:audio_detail', args=[audio.id]),
                'delete_url': reverse('core:audio_delete', args=[audio.id]),
            }
            if audio.status == 'completed' and audio.gcs_path:
                try:
                    audio_data = audio_service.get_audio_with_signed_url(audio)
                    item_data['signed_url'] = audio_data.get('signed_url')
                except Exception:
                    pass
            recent_items.append(item_data)
        
        # Música
        music_tracks = Music.objects.filter(music_filter).select_related('project').order_by('-created_at')
        for music in music_tracks:
            item_data = {
                'type': 'music',
                'object': music,
                'id': music.id,
                'created_at': music.created_at,
                'title': music.name,
                'status': music.status,
                'project': music.project,
                'signed_url': None,
                'detail_url': reverse('core:music_detail', args=[music.id]),
                'delete_url': reverse('core:music_delete', args=[music.id]),
            }
            if music.status == 'completed' and music.gcs_path:
                try:
                    from .storage.gcs import gcs_storage
                    item_data['signed_url'] = gcs_storage.get_signed_url(music.gcs_path)
                except Exception:
                    pass
            recent_items.append(item_data)
        
        # Scripts
        scripts = Script.objects.filter(script_filter).select_related('project').order_by('-created_at')
        for script in scripts:
            item_data = {
                'type': 'script',
                'object': script,
                'id': script.id,
                'created_at': script.created_at,
                'title': script.title,
                'status': script.status,
                'project': script.project,
                'signed_url': None,
                'detail_url': reverse('core:script_detail', args=[script.id]),
                'delete_url': reverse('core:script_delete', args=[script.id]),
            }
            recent_items.append(item_data)
        
        # Ordenar todos los items por fecha de creación (más recientes primero)
        recent_items.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Paginación
        paginator = Paginator(recent_items, 20)  # 20 items por página
        page_number = self.request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        context['recent_items'] = page_obj
        context['page_obj'] = page_obj
        
        return context


# ====================
# PROJECT VIEWS
# ====================
class ProjectItemsManagementView:
    """Clase para gestionar operaciones de items dentro de proyectos"""
    
    ITEM_MODELS = (Video, Image, Audio, Music, Script)
    
    @classmethod
    def get_item(cls, item_id):
        """Buscar un item en todos los modelos"""
        for model in cls.ITEM_MODELS:
            try:
                return model.objects.get(id=item_id)
            except model.DoesNotExist:
                continue
        return None
    
    @classmethod
    def move_item(cls, request, item_id):
        if request.method != "POST":
            return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
        
        import json
        data = json.loads(request.body)
        project_id = data.get('project_id')
        
        item = cls.get_item(item_id)
        if not item:
            return JsonResponse({'success': False, 'error': 'Item no encontrado'}, status=404)
        
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Proyecto no encontrado'}, status=404)
        
        # Mover item
        item.project = project
        item.save()
        
        return JsonResponse({'success': True, 'new_project_name': project.name})

class ProjectDetailView(BreadcrumbMixin, ServiceMixin, DetailView):
    """Detalle de un proyecto con sus videos"""
    model = Project
    template_name = 'projects/detail.html'
    context_object_name = 'project'
    pk_url_kwarg = 'project_id'
    
    def get(self, request, *args, **kwargs):
        """Si no hay tab especificado, redirigir a /videos/"""
        if 'tab' not in kwargs:
            project_id = kwargs.get('project_id')
            return redirect('core:project_videos', project_id=project_id)
        return super().get(request, *args, **kwargs)
    
    def get_object(self, queryset=None):
        """Obtener proyecto con videos optimizado y verificar permisos"""
        project_id = self.kwargs.get('project_id')
        project = ProjectService.get_project_with_videos(project_id)
        
        # Verificar que el usuario tenga acceso
        if not ProjectService.user_has_access(project, self.request.user):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied('No tienes acceso a este proyecto')
        
        return project
    
    def get_breadcrumbs(self):
        return [
            {'label': self.object.name, 'url': None}
        ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener videos del proyecto y formatear para el partial unificado
        videos = self.object.videos.select_related('project').order_by('-created_at')
        video_service = self.get_video_service()
        videos_items = []
        for video in videos:
            item_data = {
                'type': 'video',
                'id': video.id,
                'title': video.title,
                'status': video.status,
                'created_at': video.created_at,
                'project': video.project,
                'signed_url': None,
                'detail_url': reverse('core:video_detail', args=[video.id]),
                'delete_url': reverse('core:video_delete', args=[video.id]),
            }
            if video.status == 'completed' and video.gcs_path:
                try:
                    video_data = video_service.get_video_with_signed_urls(video)
                    item_data['signed_url'] = video_data.get('signed_url')
                except Exception:
                    pass
            videos_items.append(item_data)
        
        # Obtener imágenes del proyecto y formatear para el partial unificado
        images = self.object.images.select_related('project').order_by('-created_at')
        image_service = self.get_image_service()
        images_items = []
        for image in images:
            item_data = {
                'type': 'image',
                'id': image.id,
                'title': image.title,
                'status': image.status,
                'created_at': image.created_at,
                'project': image.project,
                'signed_url': None,
                'detail_url': reverse('core:image_detail', args=[image.id]),
                'delete_url': reverse('core:image_delete', args=[image.id]),
            }
            if image.status == 'completed' and image.gcs_path:
                try:
                    image_data = image_service.get_image_with_signed_url(image)
                    item_data['signed_url'] = image_data.get('signed_url')
                except Exception:
                    pass
            images_items.append(item_data)
        
        # Obtener audios del proyecto y formatear para el partial unificado
        audios = self.object.audios.select_related('project').order_by('-created_at')
        audio_service = self.get_audio_service()
        audios_items = []
        for audio in audios:
            item_data = {
                'type': 'audio',
                'id': audio.id,
                'title': audio.title,
                'status': audio.status,
                'created_at': audio.created_at,
                'project': audio.project,
                'signed_url': None,
                'detail_url': reverse('core:audio_detail', args=[audio.id]),
                'delete_url': reverse('core:audio_delete', args=[audio.id]),
            }
            if audio.status == 'completed' and audio.gcs_path:
                try:
                    audio_data = audio_service.get_audio_with_signed_url(audio)
                    item_data['signed_url'] = audio_data.get('signed_url')
                except Exception:
                    pass
            audios_items.append(item_data)
        
        # Obtener música del proyecto y formatear para el partial unificado
        music_tracks = self.object.music_tracks.select_related('project').order_by('-created_at')
        music_items = []
        for music in music_tracks:
            item_data = {
                'type': 'music',
                'id': music.id,
                'title': music.name,
                'status': music.status,
                'created_at': music.created_at,
                'project': music.project,
                'signed_url': None,
                'detail_url': reverse('core:music_detail', args=[music.id]),
                'delete_url': reverse('core:music_delete', args=[music.id]),
            }
            if music.status == 'completed' and music.gcs_path:
                try:
                    from .storage.gcs import gcs_storage
                    item_data['signed_url'] = gcs_storage.get_signed_url(music.gcs_path)
                except Exception:
                    pass
            music_items.append(item_data)
        
        # Obtener scripts del proyecto y formatear para el partial unificado
        scripts = self.object.scripts.select_related('project').order_by('-created_at')
        scripts_items = []
        for script in scripts:
            item_data = {
                'type': 'script',
                'id': script.id,
                'title': script.title,
                'status': script.status,
                'created_at': script.created_at,
                'project': script.project,
                'signed_url': None,
                'detail_url': reverse('core:script_detail', args=[script.id]),
                'delete_url': reverse('core:script_delete', args=[script.id]),
            }
            scripts_items.append(item_data)
        
        # Mantener compatibilidad con el código existente
        context['videos'] = videos
        context['videos_items'] = videos_items
        context['images'] = images
        context['images_items'] = images_items
        context['audios'] = audios
        context['audios_items'] = audios_items
        context['scripts'] = scripts
        context['scripts_items'] = scripts_items
        context['music_tracks'] = music_tracks
        context['music_items'] = music_items
        
        # Agregar información de permisos y miembros
        context['user_role'] = self.object.get_user_role(self.request.user)
        context['project_owner'] = self.object.owner
        context['project_members'] = self.object.members.select_related('user').all()
        
        # Agregar tab activo desde kwargs (por defecto 'videos')
        context['active_tab'] = self.kwargs.get('tab', 'videos')

        context['projects'] = ProjectService.get_user_projects(self.request.user)
        
        return context


class ProjectsListView(ServiceMixin, ListView):
    """Vista de lista de proyectos del usuario"""
    model = Project
    template_name = 'projects/list.html'
    context_object_name = 'projects'
    paginate_by = 20
    
    def get_queryset(self):
        """Obtener proyectos del usuario con optimizaciones"""
        queryset = ProjectService.get_user_projects(self.request.user)
        # Optimizar consultas para evitar N+1 al acceder a owner, members y conteos
        return queryset.select_related('owner').prefetch_related(
            'members__user',
            'videos',
            'images',
            'audios',
            'music_tracks',
            'scripts'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['show_header'] = True
        
        # Agregar estadísticas de proyectos
        user_projects = ProjectService.get_user_projects(self.request.user)
        context['total_projects'] = user_projects.count()
        
        return context


class LibraryView(ServiceMixin, ListView):
    """Vista de biblioteca que muestra todos los items (videos, imágenes, audios, música, scripts)"""
    template_name = 'library/list.html'
    context_object_name = 'items'
    paginate_by = 24
    
    def get_queryset(self):
        """Obtener todos los items del usuario con búsqueda y filtros"""
        user = self.request.user
        search_query = self.request.GET.get('q', '').strip()
        item_type = self.request.GET.get('type', '').strip()
        
        # Lista para almacenar todos los items con su tipo
        all_items = []
        
        # Filtrar por tipo si se especifica
        if item_type == 'video':
            querysets = [('video', Video.objects.filter(created_by=user))]
        elif item_type == 'image':
            querysets = [('image', Image.objects.filter(created_by=user))]
        elif item_type == 'audio':
            querysets = [('audio', Audio.objects.filter(created_by=user))]
        elif item_type == 'music':
            querysets = [('music', Music.objects.filter(created_by=user))]
        elif item_type == 'script':
            querysets = [('script', Script.objects.filter(created_by=user))]
        else:
            # Todos los tipos mezclados
            querysets = [
                ('video', Video.objects.filter(created_by=user)),
                ('image', Image.objects.filter(created_by=user)),
                ('audio', Audio.objects.filter(created_by=user)),
                ('music', Music.objects.filter(created_by=user)),
                ('script', Script.objects.filter(created_by=user)),
            ]
        
        # Aplicar búsqueda y agregar items a la lista
        for item_type_name, queryset in querysets:
            if search_query:
                if item_type_name == 'video':
                    queryset = queryset.filter(Q(title__icontains=search_query) | Q(script__icontains=search_query))
                elif item_type_name == 'image':
                    queryset = queryset.filter(Q(title__icontains=search_query) | Q(prompt__icontains=search_query))
                elif item_type_name == 'audio':
                    queryset = queryset.filter(Q(title__icontains=search_query) | Q(text__icontains=search_query))
                elif item_type_name == 'music':
                    queryset = queryset.filter(Q(name__icontains=search_query) | Q(prompt__icontains=search_query))
                elif item_type_name == 'script':
                    queryset = queryset.filter(Q(title__icontains=search_query) | Q(original_script__icontains=search_query))
            
            # Convertir a lista y agregar tipo
            for item in queryset:
                # Crear un objeto wrapper con el tipo
                item_wrapper = type('ItemWrapper', (), {
                    'item': item,
                    'type': item_type_name,
                    'created_at': item.created_at,
                    'title': item.title if hasattr(item, 'title') else (item.name if hasattr(item, 'name') else 'Sin título'),
                    'status': item.status if hasattr(item, 'status') else None,
                })()
                all_items.append(item_wrapper)
        
        # Ordenar por fecha de creación descendente
        all_items.sort(key=lambda x: x.created_at, reverse=True)
        
        return all_items
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['show_header'] = True
        context['search_query'] = self.request.GET.get('q', '')
        context['selected_type'] = self.request.GET.get('type', '')
        
        # Estadísticas por tipo
        user = self.request.user
        context['stats'] = {
            'total': Video.objects.filter(created_by=user).count() + 
                    Image.objects.filter(created_by=user).count() + 
                    Audio.objects.filter(created_by=user).count() + 
                    Music.objects.filter(created_by=user).count() + 
                    Script.objects.filter(created_by=user).count(),
            'videos': Video.objects.filter(created_by=user).count(),
            'images': Image.objects.filter(created_by=user).count(),
            'audios': Audio.objects.filter(created_by=user).count(),
            'music': Music.objects.filter(created_by=user).count(),
            'scripts': Script.objects.filter(created_by=user).count(),
        }
        
        # Generar URLs firmadas y URLs de detalle para los items paginados
        from core.storage.gcs import gcs_storage
        items_with_urls = []
        for item_wrapper in context['items']:
            item = item_wrapper.item
            signed_url = None
            
            # Generar URL de detalle según el tipo
            if item_wrapper.type == 'video':
                detail_url = reverse('core:video_detail', args=[item.id])
                delete_url = reverse('core:video_delete', args=[item.id])
            elif item_wrapper.type == 'image':
                detail_url = reverse('core:image_detail', args=[item.id])
                delete_url = reverse('core:image_delete', args=[item.id])
            elif item_wrapper.type == 'audio':
                detail_url = reverse('core:audio_detail', args=[item.id])
                delete_url = reverse('core:audio_delete', args=[item.id])
            elif item_wrapper.type == 'music':
                detail_url = reverse('core:music_detail', args=[item.id])
                delete_url = reverse('core:music_delete', args=[item.id])
            elif item_wrapper.type == 'script':
                detail_url = reverse('core:script_detail', args=[item.id])
                delete_url = reverse('core:script_delete', args=[item.id])
            else:
                detail_url = '#'
                delete_url = '#'
            
            # Generar URL firmada si está completado
            if item_wrapper.status == 'completed' and hasattr(item, 'gcs_path') and item.gcs_path:
                try:
                    signed_url = gcs_storage.get_signed_url(item.gcs_path, expiration=3600)
                except Exception as e:
                    logger.error(f"Error al generar URL firmada para {item_wrapper.type} {item.id}: {e}")
            
            items_with_urls.append({
                'type': item_wrapper.type,
                'id': item.id,
                'title': item_wrapper.title,
                'status': item_wrapper.status,
                'created_at': item_wrapper.created_at,
                'project': item.project if hasattr(item, 'project') else None,
                'signed_url': signed_url,
                'detail_url': detail_url,
                'delete_url': delete_url,
            })
        
        context['items_with_urls'] = items_with_urls

        context['projects'] = ProjectService.get_user_projects(self.request.user)
        
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
            self.object = ProjectService.create_project(name, owner=self.request.user)
            messages.success(self.request, self.success_message)
            return redirect(self.get_success_url())
        except ValidationException as e:
            form.add_error('name', str(e))
            return self.form_invalid(form)


class ProjectUpdateNameView(ServiceMixin, View):
    """Actualizar nombre del proyecto via HTMX"""
    
    def post(self, request, project_id):
        """Actualizar nombre del proyecto"""
        project = get_object_or_404(Project, id=project_id)
        
        # Verificar permisos
        if not ProjectService.user_can_edit(project, request.user):
            return HttpResponse('No tienes permisos para editar este proyecto', status=403)
        
        new_name = request.POST.get('name', '').strip()
        
        if not new_name:
            return HttpResponse('El nombre no puede estar vacío', status=400)
        
        try:
            ProjectService.update_project_name(project, new_name, request.user)
            # Retornar el HTML actualizado del nombre
            return render(request, 'projects/partials/project_name.html', {
                'project': project,
                'user_role': project.get_user_role(request.user)
            })
        except ValidationException as e:
            return HttpResponse(str(e), status=400)


class ProjectDeleteView(BreadcrumbMixin, ServiceMixin, DeleteView):
    """Eliminar proyecto"""
    model = Project
    template_name = 'projects/delete.html'
    context_object_name = 'project'
    pk_url_kwarg = 'project_id'
    
    def get_success_url(self):
        # Intentar usar la página de referencia si está disponible
        referer = self.request.META.get('HTTP_REFERER')
        if referer:
            try:
                # Extraer la ruta de la URL de referencia
                from urllib.parse import urlparse
                parsed_referer = urlparse(referer)
                parsed_request = urlparse(self.request.build_absolute_uri())
                
                # Solo usar referer si es del mismo dominio
                if parsed_referer.netloc == parsed_request.netloc:
                    referer_path = parsed_referer.path
                    delete_url = self.request.path
                    
                    # Verificar que no sea la misma página de delete
                    if delete_url not in referer_path and '/delete/' not in referer_path:
                        # Si viene del dashboard, quedarse en el dashboard
                        if referer_path == '/' or referer_path.endswith('/'):
                            return reverse('core:dashboard')
                        return referer
            except Exception:
                pass  # Si hay error, usar fallback
        
        # Verificar si la URL actual es el dashboard
        current_path = self.request.path
        if current_path == '/' or (current_path.startswith('/') and current_path.count('/') == 1):
            return reverse('core:dashboard')
        
        # Fallback al dashboard
        return reverse('core:dashboard')
    
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
        """Obtener proyecto del contexto (opcional)"""
        project_id = self.kwargs.get('project_id')
        if project_id:
            return get_object_or_404(Project, pk=project_id)
        return None
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_project()
        if project:
            context['project'] = project
            context['user_role'] = project.get_user_role(self.request.user)
            context['project_owner'] = project.owner
            context['project_members'] = project.members.select_related('user').all()
        return context
    
    def get_breadcrumbs(self):
        project = self.get_project()
        if project:
            return [
                {
                    'label': project.name, 
                    'url': reverse('core:project_detail', args=[project.pk])
                },
                {'label': 'Nuevo Video', 'url': None}
            ]
        return [
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
                created_by=request.user,
                project=project,
                title=title,
                video_type=video_type,
                script=script,
                config=config
            )
            
            # Generar video automáticamente después de crear
            try:
                video_service.generate_video(video)
                messages.success(request, f'Video "{title}" creado y enviado para generación. El proceso puede tardar varios minutos.')
            except (ValidationException, ServiceException) as e:
                messages.warning(request, f'Video "{title}" creado, pero hubo un error al iniciar la generación: {str(e)}')
            except Exception as e:
                messages.warning(request, f'Video "{title}" creado, pero hubo un error inesperado al iniciar la generación: {str(e)}')
            
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


class VideoCreatePartialView(ServiceMixin, FormView):
    """Vista parcial para crear video (sin layout completo)"""
    template_name = 'videos/create_partial.html'
    
    def get_form_class(self):
        """Determinar formulario según el tipo de video"""
        if self.request.method == 'GET':
            return VideoBaseForm
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
            return VideoBaseForm
    
    def get_project(self):
        project_id = self.kwargs['project_id']
        return get_object_or_404(Project, pk=project_id)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_project()
        context['project'] = project
        return context
    
    def post(self, request, *args, **kwargs):
        """Manejar creación de video según tipo"""
        project = self.get_project()
        video_service = self.get_video_service()
        
        title = request.POST.get('title')
        video_type = request.POST.get('type')
        script = request.POST.get('script')
        
        if not all([title, video_type, script]):
            messages.error(request, 'Todos los campos son requeridos')
            return self.get(request, *args, **kwargs)
        
        try:
            config = self._build_video_config(request, video_type, project, video_service)
            video = video_service.create_video(
                project=project,
                title=title,
                video_type=video_type,
                script=script,
                config=config
            )
            
            # Generar video automáticamente después de crear
            try:
                video_service.generate_video(video)
                messages.success(request, f'Video "{title}" creado y enviado para generación. El proceso puede tardar varios minutos.')
            except (ValidationException, ServiceException) as e:
                messages.warning(request, f'Video "{title}" creado, pero hubo un error al iniciar la generación: {str(e)}')
            except Exception as e:
                messages.warning(request, f'Video "{title}" creado, pero hubo un error inesperado al iniciar la generación: {str(e)}')
            
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
        return {
            'avatar_id': request.POST.get('avatar_id'),
            'voice_id': request.POST.get('voice_id'),
            'voice_speed': float(request.POST.get('voice_speed', 1.0)),
            'voice_pitch': int(request.POST.get('voice_pitch', 0)),
            'test': request.POST.get('test') == 'true'
        }
    
    def _build_heygen_iv_config(self, request, project, video_service):
        """Configuración para HeyGen Avatar IV"""
        config = {
            'voice_id': request.POST.get('voice_id_iv'),
            'avatar_prompt': request.POST.get('avatar_prompt', ''),
            'test': request.POST.get('test_iv') == 'true'
        }
        
        avatar_image_id = request.POST.get('avatar_image_id')
        if avatar_image_id:
            config['avatar_image_id'] = avatar_image_id
        
        return config
    
    def _build_veo_config(self, request, project, video_service):
        """Configuración para Gemini Veo"""
        return {
            'veo_model': request.POST.get('veo_model', 'veo-2.0-generate-001'),
            'aspect_ratio': request.POST.get('aspect_ratio', '16:9'),
            'duration': int(request.POST.get('duration', 8))
        }
    
    def _build_sora_config(self, request, project, video_service):
        """Configuración para OpenAI Sora"""
        config = {
            'duration': int(request.POST.get('duration', 8)),
            'size': request.POST.get('size', '1280x720'),
            'sora_model': request.POST.get('sora_model', 'sora-2')
        }
        
        if request.POST.get('use_input_reference') == 'on':
            input_reference = request.FILES.get('input_reference')
            if input_reference:
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
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['delete_url'] = reverse('core:video_delete', args=[self.object.pk])
        context['detail_url'] = reverse('core:video_detail', args=[self.object.pk])
        return context
    
    def get_success_url(self):
        # Intentar usar la página de referencia si está disponible
        referer = self.request.META.get('HTTP_REFERER')
        if referer:
            try:
                # Extraer la ruta de la URL de referencia
                from urllib.parse import urlparse, parse_qs
                parsed_referer = urlparse(referer)
                parsed_request = urlparse(self.request.build_absolute_uri())
                
                # Solo usar referer si es del mismo dominio
                if parsed_referer.netloc == parsed_request.netloc:
                    referer_path = parsed_referer.path
                    delete_url = self.request.path
                    
                    # Verificar que no sea la misma página de delete
                    if delete_url not in referer_path and '/delete/' not in referer_path:
                        # Si viene del dashboard (ruta exacta "/" o con parámetros de query del dashboard)
                        if referer_path == '/' or referer_path == '':
                            # Preservar parámetros de query si existen (búsqueda, paginación)
                            query_params = parsed_referer.query
                            if query_params:
                                return reverse('core:dashboard') + '?' + query_params
                            return reverse('core:dashboard')
                        return referer
            except Exception:
                pass  # Si hay error, usar fallback
        
        # Verificar si la URL actual es el dashboard (cuando se elimina desde modal)
        current_path = self.request.path
        if current_path == '/' or current_path == '':
            return reverse('core:dashboard')
        
        # Fallback a la lógica original
        if self.object.project:
            return reverse('core:project_detail', kwargs={'project_id': self.object.project.pk})
        return reverse('core:dashboard')
    
    def get_breadcrumbs(self):
        breadcrumbs = []
        if self.object.project:
            breadcrumbs.append({
                'label': self.object.project.name, 
                'url': reverse('core:project_detail', args=[self.object.project.pk])
            })
        breadcrumbs.extend([
            {
                'label': self.object.title, 
                'url': reverse('core:video_detail', args=[self.object.pk])
            },
            {'label': 'Eliminar', 'url': None}
        ])
        return breadcrumbs
    
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
        except InsufficientCreditsException as e:
            messages.error(request, str(e))
            # Opcional: redirigir al dashboard de créditos
            # return redirect('core:credits_dashboard')
        except RateLimitExceededException as e:
            messages.error(request, str(e))
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
    """Lista avatares de HeyGen con manejo robusto de errores"""
    
    def get(self, request):
        try:
            api_service = self.get_api_service()
            avatars = api_service.list_avatars()
            return JsonResponse({
                'avatars': avatars,
                'cached': False
            })
        except ServiceException as e:
            logger.error(f"Error crítico al listar avatares: {e}")
            return JsonResponse({
                'error': 'No se pudieron cargar los avatares. Por favor, intenta de nuevo más tarde.',
                'error_detail': str(e),
                'avatars': []
            }, status=503)  # 503 Service Unavailable es más apropiado que 500


class ListVoicesView(ServiceMixin, View):
    """Lista voces de HeyGen con manejo robusto de errores"""
    
    def get(self, request):
        try:
            api_service = self.get_api_service()
            voices = api_service.list_voices()
            return JsonResponse({
                'voices': voices,
                'cached': False
            })
        except ServiceException as e:
            logger.error(f"Error crítico al listar voces: {e}")
            return JsonResponse({
                'error': 'No se pudieron cargar las voces. Por favor, intenta de nuevo más tarde.',
                'error_detail': str(e),
                'voices': []
            }, status=503)  # 503 Service Unavailable es más apropiado que 500


class ListImageAssetsView(ServiceMixin, View):
    """Lista imágenes disponibles en HeyGen con manejo robusto de errores"""
    
    def get(self, request):
        try:
            api_service = self.get_api_service()
            assets = api_service.list_image_assets()
            return JsonResponse({
                'image_assets': assets,
                'cached': False
            })
        except ServiceException as e:
            logger.error(f"Error crítico al listar image assets: {e}")
            return JsonResponse({
                'error': 'No se pudieron cargar los assets. Por favor, intenta de nuevo más tarde.',
                'error_detail': str(e),
                'image_assets': []
            }, status=503)  # 503 Service Unavailable es más apropiado que 500


class ListElevenLabsVoicesView(ServiceMixin, View):
    """Lista voces de ElevenLabs"""
    
    def get(self, request):
        try:
            audio_service = AudioService()
            voices = audio_service.list_voices()
            return JsonResponse({
                'status': 'success',
                'voices': voices
            })
        except ServiceException as e:
            return JsonResponse({
                'status': 'error',
                'error': str(e),
                'voices': []
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
        breadcrumbs = []
        if self.object.project:
            breadcrumbs.append({
                'label': self.object.project.name, 
                'url': reverse('core:project_detail', args=[self.object.project.pk])
            })
        breadcrumbs.append({'label': self.object.title, 'url': None})
        return breadcrumbs
    
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
        """Obtener proyecto del contexto (opcional)"""
        project_id = self.kwargs.get('project_id')
        if project_id:
            return get_object_or_404(Project, pk=project_id)
        return None
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_project()
        if project:
            context['project'] = project
            context['user_role'] = project.get_user_role(self.request.user)
            context['project_owner'] = project.owner
            context['project_members'] = project.members.select_related('user').all()
        return context
    
    def get_breadcrumbs(self):
        project = self.get_project()
        if project:
            return [
                {
                    'label': project.name, 
                    'url': reverse('core:project_detail', args=[project.pk])
                },
                {'label': 'Nueva Imagen', 'url': None}
            ]
        return [
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
                title=title,
                image_type=image_type,
                prompt=prompt,
                config=config,
                created_by=request.user,
                project=project
            )
            
            # Generar imagen automáticamente después de crear
            try:
                image_service.generate_image(image)
                messages.success(request, f'Imagen "{title}" creada y generada exitosamente.')
            except (ValidationException, ImageGenerationException) as e:
                messages.warning(request, f'Imagen "{title}" creada, pero hubo un error al generarla: {str(e)}')
            except Exception as e:
                messages.warning(request, f'Imagen "{title}" creada, pero hubo un error inesperado al generarla: {str(e)}')
            
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


class ImageCreatePartialView(ServiceMixin, FormView):
    """Vista parcial para crear imagen (sin layout completo)"""
    template_name = 'images/create_partial.html'
    form_class = GeminiImageForm
    
    def get_project(self):
        project_id = self.kwargs['project_id']
        return get_object_or_404(Project, pk=project_id)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_project()
        context['project'] = project
        return context
    
    def post(self, request, *args, **kwargs):
        """Manejar creación de imagen"""
        project = self.get_project()
        image_service = self.get_image_service()
        
        title = request.POST.get('title')
        image_type = request.POST.get('type')
        prompt = request.POST.get('prompt')
        
        if not all([title, image_type, prompt]):
            messages.error(request, 'Todos los campos son requeridos')
            return self.get(request, *args, **kwargs)
        
        try:
            config = self._build_image_config(request, image_type, project, image_service)
            image = image_service.create_image(
                project=project,
                title=title,
                image_type=image_type,
                prompt=prompt,
                config=config
            )
            
            # Generar imagen automáticamente después de crear
            try:
                image_service.generate_image(image)
                messages.success(request, f'Imagen "{title}" creada y generada exitosamente.')
            except (ValidationException, ImageGenerationException) as e:
                messages.warning(request, f'Imagen "{title}" creada, pero hubo un error al generarla: {str(e)}')
            except Exception as e:
                messages.warning(request, f'Imagen "{title}" creada, pero hubo un error inesperado al generarla: {str(e)}')
            
            return redirect('core:image_detail', image_id=image.pk)
        except (ValidationException, ServiceException) as e:
            messages.error(request, str(e))
            return self.get(request, *args, **kwargs)
        except Exception as e:
            messages.error(request, f'Error inesperado: {str(e)}')
            return self.get(request, *args, **kwargs)
    
    def _build_image_config(self, request, image_type, project, image_service):
        """Construir configuración según el tipo de imagen"""
        config = {
            'aspect_ratio': request.POST.get('aspect_ratio', '1:1'),
            'response_modalities': request.POST.get('response_modalities', 'image_only')
        }
        
        if image_type == 'image_to_image':
            input_image = request.FILES.get('input_image')
            if input_image:
                upload_result = image_service.upload_input_image(input_image, project)
                config['input_image_gcs_path'] = upload_result['gcs_path']
        elif image_type == 'multi_image':
            input_images = []
            for i in range(1, 4):
                img = request.FILES.get(f'input_image_{i}')
                if img:
                    upload_result = image_service.upload_input_image(img, project)
                    input_images.append(upload_result['gcs_path'])
            config['input_images'] = input_images
        
        return config


class ImageDeleteView(BreadcrumbMixin, DeleteView):
    """Eliminar imagen"""
    model = Image
    template_name = 'images/delete.html'
    context_object_name = 'image'
    pk_url_kwarg = 'image_id'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['delete_url'] = reverse('core:image_delete', args=[self.object.pk])
        context['detail_url'] = reverse('core:image_detail', args=[self.object.pk])
        return context
    
    def get_success_url(self):
        if self.object.project:
            return reverse('core:project_detail', kwargs={'project_id': self.object.project.pk})
        return reverse('core:dashboard')
    
    def get_breadcrumbs(self):
        breadcrumbs = []
        if self.object.project:
            breadcrumbs.append({
                'label': self.object.project.name, 
                'url': reverse('core:project_detail', args=[self.object.project.pk])
            })
        breadcrumbs.extend([
            {
                'label': self.object.title, 
                'url': reverse('core:image_detail', args=[self.object.pk])
            },
            {'label': 'Eliminar', 'url': None}
        ])
        return breadcrumbs
    
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
        except InsufficientCreditsException as e:
            messages.error(request, str(e))
        except RateLimitExceededException as e:
            messages.error(request, str(e))
        except (ValidationException, ImageGenerationException) as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error inesperado: {str(e)}')
        
        return redirect('core:image_detail', image_id=image.pk)


# ====================
# AUDIO VIEWS
# ====================

class AudioDetailView(BreadcrumbMixin, ServiceMixin, DetailView):
    """Detalle de un audio"""
    model = Audio
    template_name = 'audios/detail.html'
    context_object_name = 'audio'
    pk_url_kwarg = 'audio_id'
    
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
        
        # Usar servicio para obtener URL firmada
        audio_service = self.get_audio_service()
        audio_data = audio_service.get_audio_with_signed_url(self.object)
        
        context.update(audio_data)
        return context


class AudioCreateView(BreadcrumbMixin, ServiceMixin, FormView):
    """Crear nuevo audio"""
    template_name = 'audios/create.html'
    form_class = AudioForm
    
    def get_project(self):
        """Obtener proyecto del contexto (opcional)"""
        project_id = self.kwargs.get('project_id')
        if project_id:
            return get_object_or_404(Project, pk=project_id)
        return None
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_project()
        if project:
            context['project'] = project
            context['user_role'] = project.get_user_role(self.request.user)
            context['project_owner'] = project.owner
            context['project_members'] = project.members.select_related('user').all()
        
        # Listar voces disponibles
        try:
            audio_service = self.get_audio_service()
            voices = audio_service.list_voices()
            context['voices'] = voices
        except Exception as e:
            logger.error(f"Error al listar voces: {e}")
            context['voices'] = []
            messages.warning(self.request, 'No se pudieron cargar las voces disponibles')
        
        return context
    
    def get_breadcrumbs(self):
        project = self.get_project()
        if project:
            return [
                {
                    'label': project.name, 
                    'url': reverse('core:project_detail', args=[project.pk])
                },
                {'label': 'Nuevo Audio', 'url': None}
            ]
        return [
            {'label': 'Nuevo Audio', 'url': None}
        ]
    
    def post(self, request, *args, **kwargs):
        """Manejar creación de audio"""
        project = self.get_project()
        audio_service = self.get_audio_service()
        
        # Obtener datos básicos
        title = request.POST.get('title')
        text = request.POST.get('text')
        voice_id = request.POST.get('voice_id')
        voice_name = request.POST.get('voice_name')
        
        # Validaciones básicas
        if not all([title, text, voice_id]):
            messages.error(request, 'Todos los campos son requeridos')
            return self.get(request, *args, **kwargs)
        
        try:
            # Crear audio usando servicio
            audio = audio_service.create_audio(
                title=title,
                text=text,
                voice_id=voice_id,
                created_by=request.user,
                voice_name=voice_name,
                project=project
            )
            
            # Generar audio automáticamente después de crear
            try:
                audio_service.generate_audio(audio)
                messages.success(request, f'Audio "{title}" creado y generado exitosamente.')
            except (ValidationException, ServiceException) as e:
                messages.warning(request, f'Audio "{title}" creado, pero hubo un error al generarlo: {str(e)}')
            except Exception as e:
                messages.warning(request, f'Audio "{title}" creado, pero hubo un error inesperado al generarlo: {str(e)}')
            
            return redirect('core:audio_detail', audio_id=audio.pk)
            
        except (ValidationException, ServiceException) as e:
            messages.error(request, str(e))
            return self.get(request, *args, **kwargs)
        except Exception as e:
            messages.error(request, f'Error inesperado: {str(e)}')
            return self.get(request, *args, **kwargs)


class AudioCreatePartialView(ServiceMixin, FormView):
    """Vista parcial para crear audio (sin layout completo)"""
    template_name = 'audios/create_partial.html'
    form_class = AudioForm
    
    def get_project(self):
        project_id = self.kwargs['project_id']
        return get_object_or_404(Project, pk=project_id)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_project()
        context['project'] = project
        
        try:
            audio_service = self.get_audio_service()
            voices = audio_service.list_voices()
            context['voices'] = voices
        except Exception as e:
            logger.error(f"Error al listar voces: {e}")
            context['voices'] = []
            messages.warning(self.request, 'No se pudieron cargar las voces disponibles')
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Manejar creación de audio"""
        project = self.get_project()
        audio_service = self.get_audio_service()
        
        title = request.POST.get('title')
        text = request.POST.get('text')
        voice_id = request.POST.get('voice_id')
        voice_name = request.POST.get('voice_name')
        
        if not all([title, text, voice_id]):
            messages.error(request, 'Todos los campos son requeridos')
            return self.get(request, *args, **kwargs)
        
        try:
            audio = audio_service.create_audio(
                project=project,
                title=title,
                text=text,
                voice_id=voice_id,
                voice_name=voice_name
            )
            
            # Generar audio automáticamente después de crear
            try:
                audio_service.generate_audio(audio)
                messages.success(request, f'Audio "{title}" creado y generado exitosamente.')
            except (ValidationException, ServiceException) as e:
                messages.warning(request, f'Audio "{title}" creado, pero hubo un error al generarlo: {str(e)}')
            except Exception as e:
                messages.warning(request, f'Audio "{title}" creado, pero hubo un error inesperado al generarlo: {str(e)}')
            
            return redirect('core:audio_detail', audio_id=audio.pk)
        except (ValidationException, ServiceException) as e:
            messages.error(request, str(e))
            return self.get(request, *args, **kwargs)
        except Exception as e:
            messages.error(request, f'Error inesperado: {str(e)}')
            return self.get(request, *args, **kwargs)


class AudioDeleteView(BreadcrumbMixin, DeleteView):
    """Eliminar audio"""
    model = Audio
    template_name = 'audios/delete.html'
    context_object_name = 'audio'
    pk_url_kwarg = 'audio_id'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['delete_url'] = reverse('core:audio_delete', args=[self.object.pk])
        context['detail_url'] = reverse('core:audio_detail', args=[self.object.pk])
        return context
    
    def get_success_url(self):
        if self.object.project:
            return reverse('core:project_detail', kwargs={'project_id': self.object.project.pk})
        return reverse('core:dashboard')
    
    def get_breadcrumbs(self):
        breadcrumbs = []
        if self.object.project:
            breadcrumbs.append({
                'label': self.object.project.name, 
                'url': reverse('core:project_detail', args=[self.object.project.pk])
            })
        breadcrumbs.extend([
            {
                'label': self.object.title, 
                'url': reverse('core:audio_detail', args=[self.object.pk])
            },
            {'label': 'Eliminar', 'url': None}
        ])
        return breadcrumbs
    
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
        
        audio_title = self.object.title
        self.object.delete()
        
        messages.success(request, f'Audio "{audio_title}" eliminado')
        return redirect(success_url)


# ====================
# AUDIO ACTIONS
# ====================

class AudioGenerateView(ServiceMixin, View):
    """Generar audio usando ElevenLabs API"""
    
    def post(self, request, audio_id):
        audio = get_object_or_404(Audio, pk=audio_id)
        audio_service = self.get_audio_service()
        
        try:
            gcs_path = audio_service.generate_audio(audio)
            messages.success(
                request, 
                'Audio generado exitosamente.'
            )
        except InsufficientCreditsException as e:
            messages.error(request, str(e))
        except RateLimitExceededException as e:
            messages.error(request, str(e))
        except (ValidationException, ServiceException) as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error inesperado: {str(e)}')
        
        return redirect('core:audio_detail', audio_id=audio.pk)


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
        from .services import RedisService
        # DEPRECATED: N8nService está comentado
        # from .services import RedisService, N8nService
        script = get_object_or_404(Script, pk=script_id)
        
        # Log del polling
        logger.info(f"=== POLLING SCRIPT {script_id} ===")
        logger.info(f"Estado actual: {script.status}")
        logger.info(f"Datos procesados: {bool(script.processed_data)}")
        if script.processed_data:
            logger.info(f"Escenas: {len(script.scenes)}")
        logger.info(f"Timestamp: {timezone.now()}")
        
        # Si está procesando, verificar Redis
        # DEPRECATED: Este código de Redis+N8n ya no se usa con LangChain
        # El procesamiento ahora es síncrono, no necesita polling
        if script.status == 'processing':
            try:
                redis_service = RedisService()
                result = redis_service.get_script_result(str(script_id))
                
                if result:
                    logger.info(f"✓ Resultado encontrado en Redis para guión {script_id}")
                    # DEPRECATED: N8nService está comentado
                    # n8n_service = N8nService()
                    # script = n8n_service.process_webhook_response(result)
                    logger.warning(f"Redis polling detectado pero N8nService está deprecado. Usar ScriptAgentService.")
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
        """Obtener proyecto del contexto (opcional)"""
        project_id = self.kwargs.get('project_id')
        if project_id:
            return get_object_or_404(Project, pk=project_id)
        return None
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_project()
        if project:
            context['project'] = project
            context['user_role'] = project.get_user_role(self.request.user)
            context['project_owner'] = project.owner
            context['project_members'] = project.members.select_related('user').all()
        return context
    
    def get_breadcrumbs(self):
        project = self.get_project()
        if project:
            return [
                {
                    'label': project.name, 
                    'url': reverse('core:project_detail', args=[project.pk])
                },
                {'label': 'Nuevo Guión', 'url': None}
            ]
        return [
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
                status='pending',
                created_by=request.user
            )
            
            # Procesar guión con el servicio configurado (n8n o LangChain)
            service = get_script_service()
            
            # LangChain procesa síncronamente, n8n es asíncrono
            if hasattr(service, 'process_script'):
                # LangChain: procesamiento síncrono
                try:
                    script = service.process_script(script)
                    messages.success(request, f'Guión "{title}" procesado exitosamente.')
                    return redirect('core:script_detail', script_id=script.pk)
                except Exception as e:
                    logger.error(f"Error al procesar guión con LangChain: {e}")
                    messages.error(request, f'Error al procesar guión: {str(e)}')
                    return redirect('core:script_detail', script_id=script.pk)
            else:
                # n8n: procesamiento asíncrono (comportamiento original)
                try:
                    service.send_script_for_processing(script)
                    messages.success(request, f'Guión "{title}" creado y enviado para procesamiento.')
                except Exception as e:
                    messages.warning(request, f'Guión "{title}" creado pero hubo un problema al enviarlo para procesamiento: {str(e)}')
                
                # Redirigir inmediatamente al detalle del guión
                return redirect('core:script_detail', script_id=script.pk)
            
        except Exception as e:
            messages.error(request, f'Error inesperado: {str(e)}')
            return self.get(request, *args, **kwargs)


class ScriptCreatePartialView(ServiceMixin, FormView):
    """Vista parcial para crear guión (sin layout completo)"""
    template_name = 'scripts/create_partial.html'
    form_class = ScriptForm
    
    def get_project(self):
        project_id = self.kwargs['project_id']
        return get_object_or_404(Project, pk=project_id)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_project()
        context['project'] = project
        return context
    
    def post(self, request, *args, **kwargs):
        """Manejar creación de guión"""
        project = self.get_project()
        
        title = request.POST.get('title')
        original_script = request.POST.get('original_script')
        desired_duration_min = request.POST.get('desired_duration_min', 5)
        
        if not all([title, original_script]):
            messages.error(request, 'Todos los campos son requeridos')
            return self.get(request, *args, **kwargs)
        
        try:
            script = Script.objects.create(
                project=project,
                title=title,
                original_script=original_script,
                desired_duration_min=int(desired_duration_min),
                status='pending'
            )
            
            service = get_script_service()
            
            if hasattr(service, 'process_script'):
                try:
                    script = service.process_script(script)
                    messages.success(request, f'Guión "{title}" procesado exitosamente.')
                    return redirect('core:script_detail', script_id=script.pk)
                except Exception as e:
                    logger.error(f"Error al procesar guión con LangChain: {e}")
                    messages.error(request, f'Error al procesar guión: {str(e)}')
                    return redirect('core:script_detail', script_id=script.pk)
            else:
                try:
                    service.send_script_for_processing(script)
                    messages.success(request, f'Guión "{title}" creado y enviado para procesamiento.')
                except Exception as e:
                    messages.warning(request, f'Guión "{title}" creado pero hubo un problema al enviarlo para procesamiento: {str(e)}')
                
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
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['delete_url'] = reverse('core:script_delete', args=[self.object.pk])
        context['detail_url'] = reverse('core:script_detail', args=[self.object.pk])
        return context
    
    def get_success_url(self):
        if self.object.project:
            return reverse('core:project_detail', kwargs={'project_id': self.object.project.pk})
        return reverse('core:dashboard')
    
    def get_breadcrumbs(self):
        breadcrumbs = []
        if self.object.project:
            breadcrumbs.append({
                'label': self.object.project.name, 
                'url': reverse('core:project_detail', args=[self.object.project.pk])
            })
        breadcrumbs.extend([
            {
                'label': self.object.title, 
                'url': reverse('core:script_detail', args=[self.object.pk])
            },
            {'label': 'Eliminar', 'url': None}
        ])
        return breadcrumbs
    
    def delete(self, request, *args, **kwargs):
        """Manejar eliminación con soporte HTMX"""
        self.object = self.get_object()
        success_url = self.get_success_url()
        script_title = self.object.title
        self.object.delete()
        
        # Si es petición HTMX, devolver respuesta vacía (el elemento se eliminará)
        if request.headers.get('HX-Request'):
            from django.http import HttpResponse
            return HttpResponse(status=200)
        
        messages.success(request, f'Guion "{script_title}" eliminado')
        return redirect(success_url)


class ScriptRetryView(ServiceMixin, View):
    """Reintentar procesamiento de guión"""
    
    def post(self, request, script_id):
        script = get_object_or_404(Script, pk=script_id)
        
        try:
            # Resetear estado
            script.status = 'pending'
            script.error_message = None
            script.save()
            
            # Reprocesar con el servicio configurado (n8n o LangChain)
            service = get_script_service()
            
            if hasattr(service, 'process_script'):
                # LangChain: procesamiento síncrono
                try:
                    script = service.process_script(script)
                    messages.success(request, f'Guión "{script.title}" reprocesado exitosamente.')
                except Exception as e:
                    logger.error(f"Error al reprocesar guión con LangChain: {e}")
                    messages.error(request, f'Error al reprocesar guión: {str(e)}')
            else:
                # n8n: procesamiento asíncrono (comportamiento original)
                if service.send_script_for_processing(script):
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
            'breadcrumbs': self.get_breadcrumbs(),
            'user_role': project.get_user_role(request.user),
            'project_owner': project.owner,
            'project_members': project.members.select_related('user').all()
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
                    # Serializar ai_config a JSON string para el template
                    if 'scene' in scene_data and scene_data['scene'].ai_config:
                        scene_data['ai_config_json'] = json.dumps(scene_data['scene'].ai_config)
                    else:
                        scene_data['ai_config_json'] = '{}'
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
        enable_audio = request.POST.get('enable_audio', 'true').lower() == 'true'
        default_voice_id = request.POST.get('default_voice_id', 'pFZP5JQG7iQjIQuC4Bku')
        default_voice_name = request.POST.get('default_voice_name', 'Aria')
        
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
                enable_audio=enable_audio,
                default_voice_id=default_voice_id if enable_audio else None,
                default_voice_name=default_voice_name if enable_audio else None,
                status='pending'
            )
            
            # Procesar con el servicio configurado (n8n o LangChain)
            service = get_script_service()
            
            try:
                if hasattr(service, 'process_script'):
                    # LangChain: procesamiento síncrono
                    script = service.process_script(script)
                    return JsonResponse({
                        'status': 'success',
                        'script_id': script.id,
                        'scenes_count': script.db_scenes.count(),
                        'message': 'Script procesado exitosamente'
                    })
                else:
                    # n8n: procesamiento asíncrono (comportamiento original)
                    service.send_script_for_processing(script)
                    return JsonResponse({
                        'status': 'success',
                        'script_id': script.id,
                        'message': 'Script enviado para procesamiento'
                    })
                
            except Exception as e:
                logger.error(f"Error al procesar guión: {e}")
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
                # Serializar ai_config a JSON string para el template
                if 'scene' in scene_data and scene_data['scene'].ai_config:
                    scene_data['ai_config_json'] = json.dumps(scene_data['scene'].ai_config)
                else:
                    scene_data['ai_config_json'] = '{}'
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
        except InsufficientCreditsException as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
        except RateLimitExceededException as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
            
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
                'audio_status': scene.audio_status,
                'final_video_status': scene.final_video_status,
                'preview_status': scene.preview_image_status,
                'video_url': scene_data.get('video_url'),
                'audio_url': scene_data.get('audio_url'),
                'final_video_url': scene_data.get('final_video_url'),
                'preview_url': scene_data.get('preview_image_url'),
                'error_message': scene.error_message,
                'audio_error_message': scene.audio_error_message
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
        except InsufficientCreditsException as e:
            logger.error(f"Créditos insuficientes para escena {scene_id}: {e}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
        except RateLimitExceededException as e:
            logger.error(f"Límite mensual excedido para escena {scene_id}: {e}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
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
            
            # Actualizar visual_prompt si viene
            if 'visual_prompt' in data:
                scene.visual_prompt = data['visual_prompt']
                logger.info(f"  visual_prompt actualizado")
            
            # Actualizar audio_voice_id y audio_voice_name si vienen
            if 'audio_voice_id' in data:
                scene.audio_voice_id = data['audio_voice_id']
                logger.info(f"  audio_voice_id actualizado a: {data['audio_voice_id']}")
            
            if 'audio_voice_name' in data:
                scene.audio_voice_name = data['audio_voice_name']
                logger.info(f"  audio_voice_name actualizado a: {data['audio_voice_name']}")
            
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
                visual_prompt=original_scene.visual_prompt,
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


class SceneGenerateAudioView(View):
    """Generar audio para una escena manualmente"""
    
    def post(self, request, scene_id):
        try:
            scene = get_object_or_404(Scene, id=scene_id)
            
            data = json.loads(request.body)
            script_text = data.get('script_text')
            voice_id = data.get('voice_id')
            voice_name = data.get('voice_name')
            
            if not script_text:
                return JsonResponse({
                    'status': 'error',
                    'message': 'El guión no puede estar vacío'
                }, status=400)
            
            if not voice_id:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Debes especificar un voice_id'
                }, status=400)
            
            logger.info(f"=== GENERANDO AUDIO MANUAL PARA ESCENA {scene.scene_id} ===")
            logger.info(f"  Texto: {script_text[:100]}...")
            logger.info(f"  Voz: {voice_name} ({voice_id})")
            
            # Actualizar script_text y voz si se proporcionaron
            scene.script_text = script_text
            scene.audio_voice_id = voice_id
            scene.audio_voice_name = voice_name
            scene.save(update_fields=['script_text', 'audio_voice_id', 'audio_voice_name', 'updated_at'])
            
            # Generar audio
            scene_service = SceneService()
            scene_service._generate_scene_audio(scene, voice_id, voice_name)
            
            # Obtener URL firmada del audio
            audio_url = None
            if scene.audio_gcs_path:
                from .storage.gcs import gcs_storage
                audio_url = gcs_storage.get_signed_url(scene.audio_gcs_path, expiration=3600)
            
            return JsonResponse({
                'status': 'success',
                'message': 'Audio generado correctamente',
                'audio_url': audio_url
            })
            
        except Exception as e:
            logger.error(f"Error al generar audio para escena {scene_id}: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Error al generar audio: {str(e)}'
            }, status=500)


class SceneCombineAudioView(View):
    """Forzar combinación de video + audio manualmente"""
    
    def post(self, request, scene_id):
        try:
            scene = get_object_or_404(Scene, id=scene_id)
            
            # Verificar que el video y audio estén completados
            if scene.video_status != 'completed':
                return JsonResponse({
                    'status': 'error',
                    'message': 'El video no está completado'
                }, status=400)
            
            if scene.audio_status != 'completed':
                return JsonResponse({
                    'status': 'error',
                    'message': 'El audio no está completado'
                }, status=400)
            
            logger.info(f"=== COMBINACIÓN MANUAL SOLICITADA PARA ESCENA {scene.scene_id} ===")
            
            # Resetear el estado del video final a pending para permitir la recombinación
            scene.final_video_status = 'pending'
            scene.save(update_fields=['final_video_status', 'updated_at'])
            
            # Combinar
            scene_service = SceneService()
            scene_service._auto_combine_video_audio_if_ready(scene)
            
            # Refrescar para obtener el estado actualizado
            scene.refresh_from_db()
            
            # Obtener URL firmada si está listo
            final_video_url = None
            if scene.final_video_status == 'completed' and scene.final_video_gcs_path:
                from .storage.gcs import gcs_storage
                final_video_url = gcs_storage.get_signed_url(scene.final_video_gcs_path, expiration=3600)
            
            return JsonResponse({
                'status': 'success',
                'message': 'Video combinado correctamente',
                'final_video_url': final_video_url,
                'final_video_status': scene.final_video_status
            })
            
        except Exception as e:
            logger.error(f"Error al combinar video+audio para escena {scene_id}: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Error al combinar: {str(e)}'
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

# DEPRECATED: Esta clase ya no se usa. Reemplazada por ScriptAgentService (LangChain)
# Código comentado para referencia histórica
# class N8nWebhookView(View):
#     """Webhook para recibir respuestas de n8n"""
#     
#     from django.views.decorators.csrf import csrf_exempt
#     from django.utils.decorators import method_decorator
#     
#     @method_decorator(csrf_exempt)
#     def dispatch(self, *args, **kwargs):
#         return super().dispatch(*args, **kwargs)
#     
#     def post(self, request):
#         """Procesar respuesta del webhook de n8n - DEPRECATED con LangChain"""
#         from django.conf import settings
#         
#         # Si LangChain está activo, este endpoint no debería usarse
#         if getattr(settings, 'USE_LANGCHAIN_AGENT', False):
#             logger.warning("N8nWebhookView llamado pero LangChain está activo")
#             return JsonResponse({
#                 'status': 'deprecated',
#                 'message': 'Este endpoint ya no se usa con LangChain. El procesamiento es síncrono ahora.'
#             }, status=410)  # 410 Gone
#         
#         try:
#             import json
#             
#             # Log de inicio
#             logger.info("=" * 80)
#             logger.info("=== WEBHOOK N8N RECIBIDO ===")
#             logger.info(f"Timestamp: {timezone.now()}")
#             logger.info(f"Request headers: {dict(request.headers)}")
#             logger.info(f"Request body (raw): {request.body.decode('utf-8')}")
#             
#             # Obtener datos del webhook
#             data = json.loads(request.body)
#             
#             # Log de los datos parseados
#             logger.info(f"Datos parseados:")
#             logger.info(f"  - status: {data.get('status')}")
#             logger.info(f"  - script_id: {data.get('script_id')}")
#             logger.info(f"  - message: {data.get('message')}")
#             logger.info(f"  - project: {data.get('project', {})}")
#             logger.info(f"  - scenes count: {len(data.get('scenes', []))}")
#             
#             # Procesar respuesta usando el servicio (solo n8n en este punto)
#             from core.services import N8nService
#             n8n_service = N8nService()
#             script = n8n_service.process_webhook_response(data)
#             
#             logger.info(f"✓ Webhook n8n procesado exitosamente para guión {script.id}")
#             logger.info(f"  - Nuevo estado: {script.status}")
#             logger.info(f"  - Escenas guardadas: {len(script.scenes)}")
#             logger.info("=" * 80)
#             
#             return JsonResponse({
#                 'status': 'success', 
#                 'message': 'Datos procesados',
#                 'script_id': script.id
#             })
#             
#         except json.JSONDecodeError as e:
#             logger.error(f"✗ JSON inválido en webhook: {e}")
#             return JsonResponse({'error': 'JSON inválido'}, status=400)
#         except (ValidationException, ServiceException) as e:
#             logger.error(f"✗ Error de validación en webhook n8n: {e}")
#             return JsonResponse({'error': str(e)}, status=400)
#         except Exception as e:
#             logger.error(f"✗ Error inesperado en webhook n8n: {e}")
#             logger.exception("Traceback completo:")
#             return JsonResponse({'error': 'Error interno'}, status=500)


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
        if not password:
            return "La contraseña no puede estar vacía."
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



# ====================
# MUSIC VIEWS
# ====================

class MusicCreateView(BreadcrumbMixin, ServiceMixin, View):
    """Crear nueva música con ElevenLabs Music"""
    template_name = 'music/create.html'
    
    def get_project(self):
        """Obtener proyecto del contexto (opcional)"""
        project_id = self.kwargs.get('project_id')
        if project_id:
            return get_object_or_404(Project, pk=project_id)
        return None
    
    def get_context_data(self):
        """Preparar contexto para el template"""
        project = self.get_project()
        context = {
            'breadcrumbs': self.get_breadcrumbs()
        }
        if project:
            context.update({
                'project': project,
                'user_role': project.get_user_role(self.request.user) if hasattr(self, 'request') else None,
                'project_owner': project.owner,
                'project_members': project.members.select_related('user').all()
            })
        return context
    
    def get_breadcrumbs(self):
        project = self.get_project()
        if project:
            return [
                {
                    'label': project.name, 
                    'url': reverse('core:project_detail', args=[project.pk])
                },
                {'label': '🎵 Nueva Música', 'url': None}
            ]
        return [
            {'label': '🎵 Nueva Música', 'url': None}
        ]
    
    def get(self, request, *args, **kwargs):
        """Mostrar formulario de creación"""
        self.request = request  # Guardar request para get_context_data
        context = self.get_context_data()
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        """Manejar creación de música"""
        from .models import Music
        
        project = self.get_project()
        
        # Obtener datos básicos
        name = request.POST.get('name')
        prompt = request.POST.get('prompt')
        duration_sec = request.POST.get('duration_sec', 30)
        
        # Validaciones básicas
        if not all([name, prompt]):
            messages.error(request, 'El nombre y el prompt son requeridos')
            return self.get(request, *args, **kwargs)
        
        try:
            duration_ms = int(duration_sec) * 1000
            
            # Crear objeto Music
            music = Music.objects.create(
                project=project,
                name=name,
                prompt=prompt,
                duration_ms=duration_ms,
                status='pending',
                created_by=request.user
            )
            
            # Generar música automáticamente después de crear
            try:
                from .services import ElevenLabsMusicService
                music_service = ElevenLabsMusicService()
                music_service.generate_music(music)
                messages.success(request, f'Música "{name}" creada y generada exitosamente!')
            except ServiceException as e:
                messages.warning(request, f'Música "{name}" creada, pero hubo un error al generarla: {str(e)}')
            except Exception as e:
                logger.error(f"Error al generar música: {e}")
                messages.warning(request, f'Música "{name}" creada, pero hubo un error inesperado al generarla: {str(e)}')
            
            return redirect('core:music_detail', music_id=music.pk)
            
        except (ValidationException, ServiceException) as e:
            messages.error(request, str(e))
            return self.get(request, *args, **kwargs)
        except Exception as e:
            messages.error(request, f'Error inesperado: {str(e)}')
            return self.get(request, *args, **kwargs)


class MusicDetailView(BreadcrumbMixin, ServiceMixin, DetailView):
    """Vista de detalle de música"""
    model = Music
    template_name = 'music/detail.html'
    context_object_name = 'music'
    pk_url_kwarg = 'music_id'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener URL firmada si existe el archivo
        if self.object.gcs_path:
            try:
                from .storage.gcs import gcs_storage
                context['signed_url'] = gcs_storage.get_signed_url(self.object.gcs_path)
            except Exception as e:
                logger.error(f"Error al obtener URL firmada: {e}")
                context['signed_url'] = None
        
        return context
    
    def get_breadcrumbs(self):
        if self.object.project:
            return [
                {
                    'label': self.object.project.name, 
                    'url': reverse('core:project_detail', args=[self.object.project.pk])
                },
                {'label': f'🎵 {self.object.name}', 'url': None}
            ]
        return [
            {'label': f'🎵 {self.object.name}', 'url': None}
        ]


class MusicDeleteView(BreadcrumbMixin, DeleteView):
    """Eliminar música"""
    model = Music
    template_name = 'music/delete.html'
    context_object_name = 'music'
    pk_url_kwarg = 'music_id'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['delete_url'] = reverse('core:music_delete', args=[self.object.pk])
        context['detail_url'] = reverse('core:music_detail', args=[self.object.pk])
        return context
    
    def get_success_url(self):
        if self.object.project:
            return reverse('core:project_detail', kwargs={'project_id': self.object.project.pk})
        return reverse('core:dashboard')
    
    def get_breadcrumbs(self):
        breadcrumbs = []
        if self.object.project:
            breadcrumbs.append({
                'label': self.object.project.name, 
                'url': reverse('core:project_detail', args=[self.object.project.pk])
            })
        breadcrumbs.extend([
            {
                'label': self.object.name, 
                'url': reverse('core:music_detail', args=[self.object.pk])
            },
            {'label': 'Eliminar', 'url': None}
        ])
        return breadcrumbs
    
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
        
        music_name = self.object.name
        self.object.delete()
        
        messages.success(request, f'Música "{music_name}" eliminada')
        return redirect(success_url)


class MusicGenerateView(ServiceMixin, View):
    """Generar música usando ElevenLabs Music API"""
    
    def post(self, request, music_id):
        from .models import Music
        from .services import ElevenLabsMusicService
        
        music = get_object_or_404(Music, pk=music_id)
        
        try:
            music_service = ElevenLabsMusicService()
            result = music_service.generate_music(music)
            
            messages.success(request, f'Música "{music.name}" generada exitosamente!')
            return redirect('core:music_detail', music_id=music.pk)
            
        except ServiceException as e:
            messages.error(request, str(e))
            return redirect('core:music_detail', music_id=music.pk)
        except Exception as e:
            logger.error(f"Error al generar música: {e}")
            messages.error(request, f'Error inesperado: {str(e)}')
            return redirect('core:music_detail', music_id=music.pk)


class MusicStatusView(View):
    """API endpoint para verificar el estado de la música"""
    
    def get(self, request, music_id):
        from .models import Music
        
        music = get_object_or_404(Music, pk=music_id)
        
        response_data = {
            'status': music.status,
            'error_message': music.error_message
        }
        
        if music.status == 'completed' and music.gcs_path:
            try:
                from .storage.gcs import gcs_storage
                response_data['signed_url'] = gcs_storage.get_signed_url(music.gcs_path)
                response_data['song_metadata'] = music.song_metadata
            except Exception as e:
                logger.error(f"Error al obtener URL firmada: {e}")
        
        return JsonResponse(response_data)


class MusicCompositionPlanView(View):
    """API endpoint para crear un composition plan"""
    
    def post(self, request, music_id):
        from .models import Music
        from .services import ElevenLabsMusicService
        import json
        
        music = get_object_or_404(Music, pk=music_id)
        
        try:
            data = json.loads(request.body)
            prompt = data.get('prompt', music.prompt)
            duration_ms = data.get('duration_ms', music.duration_ms)
            
            music_service = ElevenLabsMusicService()
            composition_plan = music_service.create_composition_plan(prompt, duration_ms)
            
            # Guardar el plan en el objeto Music
            music.composition_plan = composition_plan
            music.save(update_fields=['composition_plan'])
            
            return JsonResponse({
                'status': 'success',
                'composition_plan': composition_plan
            })
            
        except ServiceException as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
        except Exception as e:
            logger.error(f"Error al crear composition plan: {e}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)


# ====================
# PROJECT INVITATIONS
# ====================

class ProjectInviteView(BreadcrumbMixin, ServiceMixin, View):
    """Vista para invitar usuarios a un proyecto"""
    template_name = 'projects/invite.html'
    
    def get_project(self):
        """Obtener proyecto y verificar permisos"""
        project_id = self.kwargs['project_id']
        project = ProjectService.get_project_with_videos(project_id)
        
        if not ProjectService.user_can_edit(project, self.request.user):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied('No tienes permisos para invitar usuarios a este proyecto')
        
        return project
    
    def get_breadcrumbs(self):
        project = self.get_project()
        return [
            {'label': project.name, 'url': reverse('core:project_detail', args=[project.pk])},
            {'label': 'Invitar Usuario', 'url': None}
        ]
    
    def get(self, request, *args, **kwargs):
        project = self.get_project()
        context = {
            'project': project,
            'breadcrumbs': self.get_breadcrumbs()
        }
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        project = self.get_project()
        email = request.POST.get('email', '').strip()
        role = request.POST.get('role', 'editor')
        
        if not email:
            messages.error(request, 'El email es requerido')
            return self.get(request, *args, **kwargs)
        
        try:
            invitation = InvitationService.create_invitation(
                project=project,
                email=email,
                invited_by=request.user,
                role=role
            )
            
            # Enviar email de invitación
            send_invitation_email(request, invitation)
            
            messages.success(request, f'Invitación enviada a {email}')
            # Si es petición HTMX o desde el tab, redirigir al tab de invitaciones
            if request.headers.get('HX-Request') or request.GET.get('from_tab'):
                return redirect('core:project_invitations_partial', project_id=project.pk)
            return redirect('core:project_invitations', project_id=project.pk)
            
        except ValidationException as e:
            messages.error(request, str(e))
            return self.get(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error al crear invitación: {e}")
            messages.error(request, f'Error inesperado: {str(e)}')
            return self.get(request, *args, **kwargs)


class ProjectInvitePartialView(ServiceMixin, View):
    """Vista parcial para el formulario de invitar usuario (sin layout completo)"""
    
    def get_project(self):
        project_id = self.kwargs['project_id']
        project = ProjectService.get_project_with_videos(project_id)
        
        if not ProjectService.user_can_edit(project, self.request.user):
            return HttpResponse('No tienes permisos', status=403)
        
        return project
    
    def get(self, request, *args, **kwargs):
        project = self.get_project()
        return render(request, 'projects/partials/invite_form.html', {
            'project': project
        })
    
    def post(self, request, *args, **kwargs):
        project = self.get_project()
        email = request.POST.get('email', '').strip()
        role = request.POST.get('role', 'editor')
        
        if not email:
            return render(request, 'projects/partials/invite_form.html', {
                'project': project,
                'error': 'El email es requerido'
            })
        
        try:
            invitation = InvitationService.create_invitation(
                project=project,
                email=email,
                invited_by=request.user,
                role=role
            )
            
            # Enviar email de invitación
            send_invitation_email(request, invitation)
            
            # Redirigir al tab de invitaciones para mostrar la lista actualizada
            return redirect('core:project_invitations_partial', project_id=project.pk)
            
        except ValidationException as e:
            return render(request, 'projects/partials/invite_form.html', {
                'project': project,
                'error': str(e)
            })
        except Exception as e:
            logger.error(f"Error al crear invitación: {e}")
            return render(request, 'projects/partials/invite_form.html', {
                'project': project,
                'error': f'Error inesperado: {str(e)}'
            })


class ProjectInvitationsListView(BreadcrumbMixin, ServiceMixin, View):
    """Lista de invitaciones de un proyecto"""
    template_name = 'projects/invitations.html'
    
    def get_project(self):
        """Obtener proyecto y verificar permisos"""
        project_id = self.kwargs['project_id']
        project = ProjectService.get_project_with_videos(project_id)
        
        if not ProjectService.user_can_edit(project, self.request.user):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied('No tienes permisos para ver las invitaciones de este proyecto')
        
        return project
    
    def get_breadcrumbs(self):
        project = self.get_project()
        return [
            {'label': project.name, 'url': reverse('core:project_detail', args=[project.pk])},
            {'label': 'Invitaciones', 'url': None}
        ]
    
    def get(self, request, *args, **kwargs):
        project = self.get_project()
        
        try:
            invitations = InvitationService.get_project_invitations(project, request.user)
        except ValidationException as e:
            messages.error(request, str(e))
            invitations = []
        
        context = {
            'project': project,
            'invitations': invitations,
            'breadcrumbs': self.get_breadcrumbs()
        }
        return render(request, self.template_name, context)


class ProjectInvitationsPartialView(ServiceMixin, View):
    """Vista parcial para la lista de invitaciones (sin layout completo)"""
    
    def get_project(self):
        project_id = self.kwargs['project_id']
        project = ProjectService.get_project_with_videos(project_id)
        
        if not ProjectService.user_can_edit(project, self.request.user):
            return HttpResponse('No tienes permisos', status=403)
        
        return project
    
    def get(self, request, *args, **kwargs):
        project = self.get_project()
        
        try:
            invitations = InvitationService.get_project_invitations(project, request.user)
        except ValidationException as e:
            invitations = []
        
        return render(request, 'projects/partials/invitations_list.html', {
            'project': project,
            'invitations': invitations
        })


class AcceptInvitationView(View):
    """Vista para aceptar una invitación"""
    
    def get(self, request, token):
        from .models import ProjectInvitation
        
        try:
            invitation = ProjectInvitation.objects.get(token=token)
        except ProjectInvitation.DoesNotExist:
            messages.error(request, 'Invitación no encontrada')
            return redirect('core:dashboard')
        
        # Verificar que el usuario esté autenticado
        if not request.user.is_authenticated:
            messages.info(request, 'Debes iniciar sesión para aceptar la invitación')
            return redirect('core:login')
        
        # Verificar que el email coincida
        if invitation.email.lower() != request.user.email.lower():
            messages.error(request, 'Esta invitación es para otro usuario')
            return redirect('core:dashboard')
        
        # Verificar que pueda ser aceptada
        if not invitation.can_be_accepted():
            if invitation.is_expired():
                messages.error(request, 'La invitación ha expirado')
            else:
                messages.error(request, 'La invitación no puede ser aceptada')
            return redirect('core:dashboard')
        
        try:
            InvitationService.accept_invitation(token, request.user)
            messages.success(request, f'Te has unido al proyecto "{invitation.project.name}"')
            return redirect('core:project_detail', project_id=invitation.project.pk)
        except ValidationException as e:
            messages.error(request, str(e))
            return redirect('core:dashboard')
        except Exception as e:
            logger.error(f"Error al aceptar invitación: {e}")
            messages.error(request, f'Error inesperado: {str(e)}')
            return redirect('core:dashboard')


class CancelInvitationView(View):
    """Vista para cancelar una invitación"""
    
    def post(self, request, invitation_id):
        try:
            InvitationService.cancel_invitation(int(invitation_id), request.user)
            messages.success(request, 'Invitación cancelada')
        except ValidationException as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f"Error al cancelar invitación: {e}")
            messages.error(request, f'Error inesperado: {str(e)}')
        
        # Redirigir a la lista de invitaciones del proyecto
        from .models import ProjectInvitation
        try:
            invitation = ProjectInvitation.objects.get(id=invitation_id)
            return redirect('core:project_invitations', project_id=invitation.project.pk)
        except ProjectInvitation.DoesNotExist:
            return redirect('core:dashboard')


# ====================
# MOVE TO PROJECT VIEWS
# ====================

class MoveToProjectView(View):
    """Vista para mover items sin proyecto a un proyecto"""
    
    def get(self, request, item_type, item_id):
        """Mostrar modal con lista de proyectos"""
        # Mapeo de tipos a modelos
        model_map = {
            'video': Video,
            'image': Image,
            'audio': Audio,
            'music': Music,
            'script': Script
        }
        
        if item_type not in model_map:
            messages.error(request, 'Tipo de item no válido')
            return redirect('core:dashboard')
        
        # Obtener el item
        try:
            item = model_map[item_type].objects.get(id=item_id, created_by=request.user)
        except model_map[item_type].DoesNotExist:
            messages.error(request, f'{item_type.capitalize()} no encontrado')
            return redirect('core:dashboard')
        
        # Obtener proyectos del usuario
        user_projects = ProjectService.get_user_projects(request.user)
        
        context = {
            'item': item,
            'item_type': item_type,
            'projects': user_projects
        }
        
        return render(request, 'partials/move_to_project_modal.html', context)
    
    def post(self, request, item_type, item_id):
        """Mover el item al proyecto seleccionado"""
        # Mapeo de tipos a modelos
        model_map = {
            'video': Video,
            'image': Image,
            'audio': Audio,
            'music': Music,
            'script': Script
        }
        
        if item_type not in model_map:
            messages.error(request, 'Tipo de item no válido')
            return redirect('core:dashboard')
        
        # Obtener datos
        project_id = request.POST.get('project_id')
        if not project_id:
            messages.error(request, 'Debes seleccionar un proyecto')
            return redirect('core:dashboard')
        
        try:
            # Obtener el item y verificar permisos
            item = model_map[item_type].objects.get(id=item_id, created_by=request.user)
            
            # Obtener el proyecto y verificar permisos
            project = Project.objects.get(id=project_id)
            if not project.has_member(request.user) and project.owner != request.user:
                messages.error(request, 'No tienes permisos para este proyecto')
                return redirect('core:dashboard')
            
            # Mover el item al proyecto
            item.project = project
            item.save()
            
            messages.success(request, f'{item_type.capitalize()} movido a "{project.name}"')
            
            # Redirigir al detalle del item
            redirect_map = {
                'video': 'core:video_detail',
                'image': 'core:image_detail',
                'audio': 'core:audio_detail',
                'music': 'core:music_detail',
                'script': 'core:script_detail'
            }
            
            return redirect(redirect_map[item_type], **{f'{item_type}_id': item.id})
            
        except model_map[item_type].DoesNotExist:
            messages.error(request, f'{item_type.capitalize()} no encontrado')
            return redirect('core:dashboard')
        except Project.DoesNotExist:
            messages.error(request, 'Proyecto no encontrado')
            return redirect('core:dashboard')
        except Exception as e:
            logger.error(f"Error al mover {item_type} a proyecto: {e}")
            messages.error(request, f'Error inesperado: {str(e)}')
            return redirect('core:dashboard')


# ====================
# RAG DOCUMENTATION ASSISTANT
# ====================

class DocumentationAssistantView(LoginRequiredMixin, View):
    """Vista para inicializar el asistente (el template se incluye en base.html)"""
    
    def get(self, request):
        """El template se carga automáticamente en base.html, esta view solo valida acceso"""
        # El template se incluye directamente en base.html
        # Esta view existe por si necesitamos lógica adicional en el futuro
        return JsonResponse({'status': 'ok'})


class DocumentationAssistantChatView(LoginRequiredMixin, View):
    """Vista para procesar mensajes del chat (HTMX)"""
    
    def post(self, request):
        """Procesa un mensaje del usuario"""
        from .rag.assistant import DocumentationAssistant
        import json
        
        question = request.POST.get('question', '').strip()
        chat_history_json = request.POST.get('chat_history', '[]')
        
        if not question:
            return JsonResponse({
                'error': 'La pregunta no puede estar vacía'
            }, status=400)
        
        try:
            # Parsear historial si existe
            chat_history = []
            if chat_history_json:
                try:
                    chat_history = json.loads(chat_history_json)
                except json.JSONDecodeError:
                    chat_history = []
            
            # Inicializar asistente
            assistant = DocumentationAssistant()
            
            # Procesar pregunta
            result = assistant.ask(question, chat_history)
            
            # Preparar respuesta
            response_data = {
                'answer': result['answer'],
                'sources': result.get('sources', []),
                'question': question
            }
            
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"Error al procesar pregunta: {e}", exc_info=True)
            return JsonResponse({
                'error': f'Error al procesar tu pregunta: {str(e)}'
            }, status=500)


class DocumentationAssistantReindexView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Vista para re-indexar la documentación (solo admin)"""
    
    def test_func(self):
        """Solo usuarios con permisos de staff pueden re-indexar"""
        return self.request.user.is_staff
    
    def post(self, request):
        """Fuerza la re-indexación de la documentación"""
        from .rag.assistant import DocumentationAssistant
        from .rag.vector_store import VectorStoreManager
        
        try:
            # Eliminar índice anterior
            vector_store_manager = VectorStoreManager()
            deleted = vector_store_manager.delete_index()
            
            if deleted:
                logger.info("Índice anterior eliminado")
            
            # Crear nuevo índice
            assistant = DocumentationAssistant(reindex=True)
            messages.success(request, 'Documentación re-indexada exitosamente desde docs/api')
        except Exception as e:
            logger.error(f"Error al re-indexar: {e}", exc_info=True)
            messages.error(request, f'Error al re-indexar: {str(e)}')
        
        return redirect('core:dashboard')


# ====================
# CREATION AGENT (Chat de Creación)
# ====================

class CreationAgentView(LoginRequiredMixin, View):
    """Vista principal del chat de creación"""
    template_name = 'chat/creation_agent.html'
    
    def get(self, request):
        return render(request, self.template_name)


class CreationAgentChatView(LoginRequiredMixin, View):
    """Vista para procesar mensajes del chat de creación"""
    
    def post(self, request):
        """Procesa un mensaje del usuario"""
        from core.agents.creation_agent import CreationAgent
        import json
        
        message = request.POST.get('message', '').strip()
        chat_history_json = request.POST.get('chat_history', '[]')
        
        if not message:
            return JsonResponse({
                'error': 'El mensaje no puede estar vacío'
            }, status=400)
        
        try:
            # Parsear historial si existe
            chat_history = []
            if chat_history_json:
                try:
                    chat_history = json.loads(chat_history_json)
                except json.JSONDecodeError:
                    chat_history = []
            
            # Crear agente con user_id del usuario actual
            agent = CreationAgent(user_id=request.user.id)
            
            # Procesar mensaje
            result = agent.chat(message, chat_history)
            
            # Preparar respuesta
            response_data = {
                'answer': result.get('answer', ''),
                'tool_results': result.get('tool_results', [])
            }
            
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"Error en CreationAgentChatView: {e}", exc_info=True)
            return JsonResponse({
                'error': f'Error al procesar tu mensaje: {str(e)}'
            }, status=500)


# ====================
# CREDITS DASHBOARD
# ====================

class CreditsDashboardView(ServiceMixin, View):
    """Dashboard de créditos del usuario"""
    template_name = 'credits/dashboard.html'
    
    def get(self, request):
        """Mostrar dashboard de créditos"""
        user = request.user
        
        # Obtener créditos del usuario
        credits = CreditService.get_or_create_user_credits(user)
        
        # Obtener transacciones recientes (últimas 50)
        recent_transactions = CreditTransaction.objects.filter(user=user).order_by('-created_at')[:50]
        
        # Obtener uso por servicio (últimos 30 días)
        from datetime import timedelta
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        usage_by_service = ServiceUsage.objects.filter(
            user=user,
            created_at__gte=thirty_days_ago
        ).values('service_name').annotate(
            total_credits=Sum('credits_spent'),
            count=Count('id')
        ).order_by('-total_credits')
        
        context = {
            'credits': credits,
            'recent_transactions': recent_transactions,
            'usage_by_service': usage_by_service,
            'show_header': True,
        }
        
        return render(request, self.template_name, context)


# ====================
# STOCK SEARCH API
# ====================

class StockSearchView(View):
    """Búsqueda unificada de contenido stock en múltiples APIs"""
    
    def get(self, request):
        """
        Busca imágenes, videos o audios en múltiples fuentes de stock
        
        Query params:
            - query: Término de búsqueda (requerido)
            - type: Tipo de contenido ('image', 'video' o 'audio', default: 'image')
            - sources: Fuentes separadas por coma (freepik,pexels,unsplash,pixabay,freesound)
            - orientation: horizontal, vertical, square (opcional, solo para images/videos)
            - license: all, free, premium (solo para Freepik, default: 'all')
            - audio_type: music, sound_effects, all (solo para audio, default: 'all')
            - page: Número de página (default: 1)
            - per_page: Resultados por página (default: 20)
            - use_cache: Usar caché (default: true)
        """
        from core.services.stock_service import StockService
        from core.services.stock_cache import StockCache
        
        query = request.GET.get('query')
        if not query:
            return JsonResponse({
                'success': False,
                'error': {
                    'code': 'MISSING_QUERY',
                    'message': 'El parámetro "query" es requerido'
                }
            }, status=400)
        
        # Validar tipo de contenido
        content_type = request.GET.get('type', 'image').lower()
        if content_type not in ['image', 'video', 'audio']:
            return JsonResponse({
                'success': False,
                'error': {
                    'code': 'INVALID_TYPE',
                    'message': 'El parámetro "type" debe ser "image", "video" o "audio"'
                }
            }, status=400)
        
        # Parsear fuentes
        sources_str = request.GET.get('sources', '')
        sources = None
        if sources_str:
            sources = [s.strip() for s in sources_str.split(',') if s.strip()]
        
        # Parsear orientación
        orientation = request.GET.get('orientation', '').lower()
        if orientation and orientation not in ['horizontal', 'vertical', 'square']:
            orientation = None
        
        # Parsear otros parámetros con validación
        license_filter = request.GET.get('license', 'all')
        if license_filter not in ['all', 'free', 'premium']:
            license_filter = 'all'
        
        try:
            page = max(1, int(request.GET.get('page', 1)))
        except (ValueError, TypeError):
            page = 1
        
        try:
            per_page = max(1, min(100, int(request.GET.get('per_page', 20))))
        except (ValueError, TypeError):
            per_page = 20
        
        use_cache = request.GET.get('use_cache', 'true').lower() == 'true'
        
        try:
            stock_service = StockService()
            
            # Verificar si hay fuentes disponibles
            available_sources = stock_service.get_available_sources()
            if not available_sources:
                logger.warning("StockSearchView: No hay APIs de stock configuradas")
                return JsonResponse({
                    'success': False,
                    'error': {
                        'code': 'NO_SOURCES_CONFIGURED',
                        'message': 'No hay APIs de stock configuradas. Verifica las API keys en settings.'
                    }
                }, status=500)
            
            # Filtrar fuentes solicitadas con las disponibles
            if sources:
                sources = [s for s in sources if s in available_sources]
                if not sources:
                    return JsonResponse({
                        'success': False,
                        'error': {
                            'code': 'NO_AVAILABLE_SOURCES',
                            'message': f'Las fuentes solicitadas no están disponibles. Fuentes disponibles: {", ".join(available_sources)}'
                        }
                    }, status=400)
            else:
                sources = available_sources
            
            # Intentar obtener del caché
            cached_results = None
            if use_cache:
                try:
                    cache_kwargs = {
                        'query': query,
                        'content_type': content_type,
                        'sources': sources,
                        'orientation': orientation,
                        'license_filter': license_filter,
                        'page': page,
                        'per_page': per_page
                    }
                    if content_type == 'audio':
                        audio_type = request.GET.get('audio_type', 'all')
                        cache_kwargs['audio_type'] = audio_type if audio_type in ['music', 'sound_effects', 'all'] else 'all'
                    cached_results = StockCache.get(**cache_kwargs)
                except Exception as e:
                    logger.warning(f"Error al obtener del caché: {e}", exc_info=True)
            
            if cached_results:
                logger.info(f"Stock search cache HIT para '{query}'")
                return JsonResponse({
                    'success': True,
                    'cached': True,
                    'data': cached_results
                })
            
            # Buscar en las APIs
            if content_type == 'image':
                results = stock_service.search_images(
                    query=query,
                    sources=sources,
                    orientation=orientation,
                    license_filter=license_filter,
                    page=page,
                    per_page=per_page
                )
            elif content_type == 'video':
                results = stock_service.search_videos(
                    query=query,
                    sources=sources,
                    orientation=orientation,
                    page=page,
                    per_page=per_page
                )
            else:  # audio
                audio_type = request.GET.get('audio_type', 'all')  # 'music', 'sound_effects', 'all'
                audio_type = audio_type if audio_type in ['music', 'sound_effects', 'all'] else 'all'
                results = stock_service.search_audio(
                    query=query,
                    sources=sources,
                    audio_type=audio_type,
                    page=page,
                    per_page=per_page
                )
            
            # Guardar en caché
            if use_cache:
                try:
                    cache_kwargs = {
                        'query': query,
                        'content_type': content_type,
                        'results': results,
                        'sources': sources,
                        'orientation': orientation,
                        'license_filter': license_filter,
                        'page': page,
                        'per_page': per_page
                    }
                    if content_type == 'audio':
                        cache_kwargs['audio_type'] = audio_type
                    StockCache.set(**cache_kwargs)
                except Exception as e:
                    logger.warning(f"Error al guardar en caché: {e}", exc_info=True)
            
            logger.info(f"Stock search para '{query}': {results.get('total', 0)} resultados de {len(sources)} fuentes")
            
            return JsonResponse({
                'success': True,
                'cached': False,
                'data': results
            })
            
        except Exception as e:
            logger.error(f"Error en búsqueda de stock: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': {
                    'code': 'SEARCH_ERROR',
                    'message': str(e)
                }
            }, status=500)


class StockSourcesView(View):
    """Lista las fuentes de stock disponibles"""
    
    def get(self, request):
        """Retorna las fuentes de stock configuradas y disponibles"""
        from core.services.stock_service import StockService
        
        try:
            stock_service = StockService()
            available_sources = stock_service.get_available_sources()
            
            return JsonResponse({
                'success': True,
                'sources': available_sources,
                'total': len(available_sources)
            })
            
        except Exception as e:
            logger.error(f"Error obteniendo fuentes de stock: {e}")
            return JsonResponse({
                'success': False,
                'error': {
                    'code': 'SOURCES_ERROR',
                    'message': str(e)
                }
            }, status=500)


class StockListView(LoginRequiredMixin, View):
    """Vista principal para búsqueda de contenido stock"""
    template_name = 'stock/list.html'
    
    def get(self, request, **kwargs):
        """Muestra la página de búsqueda de stock"""
        from core.services.stock_service import StockService
        
        # Obtener parámetros de búsqueda
        query = request.GET.get('q', '').strip()
        # Obtener type desde kwargs (URL) o desde GET params
        content_type = kwargs.get('type') or request.GET.get('type', 'image')
        content_type = content_type.lower() if content_type else 'image'  # image, video, audio
        sources_str = request.GET.get('sources', '')
        orientation = request.GET.get('orientation', '')
        license_filter = request.GET.get('license', 'all')
        audio_type = request.GET.get('audio_type', 'all')  # Para audio: music, sound_effects, all
        page = int(request.GET.get('page', 1))
        
        # Parsear fuentes
        sources = None
        if sources_str:
            sources = [s.strip() for s in sources_str.split(',') if s.strip()]
        
        # Obtener fuentes disponibles y eliminar duplicados (case-insensitive)
        stock_service = StockService()
        available_sources_raw = stock_service.get_available_sources()
        
        # Eliminar duplicados case-insensitive manteniendo el formato original
        seen_lower = set()
        unique_sources = []
        for source in available_sources_raw:
            if source and isinstance(source, str):
                source_clean = source.strip()
                source_lower = source_clean.lower()
                if source_lower and source_lower not in seen_lower:
                    seen_lower.add(source_lower)
                    unique_sources.append(source_clean)
        
        available_sources = unique_sources
        logger.debug(f"Fuentes disponibles (sin duplicados): {available_sources}")
        
        # Obtener proyectos del usuario para el modal de mover a proyecto
        user_projects = ProjectService.get_user_projects(request.user)
        
        # Eliminar duplicados por ID usando values() para evitar duplicados en la consulta
        # y luego convertir a lista de diccionarios únicos
        projects_dict = {}
        for p in user_projects.only('id', 'name'):
            if p.id not in projects_dict:
                projects_dict[p.id] = {'id': p.id, 'name': p.name}
        
        # Convertir a lista y luego a JSON
        unique_projects_list = list(projects_dict.values())
        projects_json = json.dumps(unique_projects_list)
        
        context = {
            'query': query,
            'content_type': content_type,
            'sources': sources or [],
            'orientation': orientation,
            'license_filter': license_filter,
            'audio_type': audio_type,
            'page': page,
            'available_sources': json.dumps(available_sources),
            'projects': projects_json
        }
        
        return render(request, self.template_name, context)


class StockVideoProxyView(LoginRequiredMixin, View):
    """Proxy para streaming de videos de stock sin descargarlos completamente"""
    
    def get(self, request):
        """
        Hace streaming de un video desde la URL proporcionada
        
        Query params:
            - url: URL del video a reproducir
        """
        import requests
        from urllib.parse import unquote
        
        video_url = request.GET.get('url')
        if not video_url:
            return HttpResponse('URL no proporcionada', status=400)
        
        # Decodificar URL si está codificada
        video_url = unquote(video_url)
        
        # Validar que sea una URL válida
        if not video_url.startswith(('http://', 'https://')):
            return HttpResponse('URL inválida', status=400)
        
        # Validar que la URL parezca ser un video ANTES de hacer la petición
        video_extensions = ['.mp4', '.webm', '.mov', '.avi', '.mkv', '.m4v', '.flv', '.wmv']
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg']
        
        # Verificar extensiones de imagen primero (más común)
        if any(video_url.lower().endswith(ext) for ext in image_extensions):
            return HttpResponse('Esta URL parece ser una imagen, no un video', status=400)
        
        # Verificar si tiene extensión de video o contiene indicadores de video
        has_video_ext = any(video_url.lower().endswith(ext) for ext in video_extensions)
        has_video_indicator = '/videos/' in video_url.lower() or '/video/' in video_url.lower()
        
        if not has_video_ext and not has_video_indicator:
            # Si no tiene indicadores claros, permitir pero registrar advertencia
            logger.warning(f"URL sin indicadores claros de video: {video_url}")
        
        try:
            # Hacer streaming del video
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Obtener el rango de bytes si está presente (para video streaming)
            range_header = request.META.get('HTTP_RANGE', '')
            
            req_headers = headers.copy()
            if range_header:
                req_headers['Range'] = range_header
            
            response = requests.get(
                video_url,
                headers=req_headers,
                stream=True,
                timeout=30
            )
            
            # Verificar que sea un video
            content_type = response.headers.get('Content-Type', '')
            if 'video' not in content_type and 'application/octet-stream' not in content_type:
                # Intentar detectar por extensión
                if not any(video_url.lower().endswith(ext) for ext in ['.mp4', '.webm', '.mov', '.avi', '.mkv']):
                    return HttpResponse('URL no parece ser un video', status=400)
            
            # Crear respuesta de streaming
            stream_response = StreamingHttpResponse(
                response.iter_content(chunk_size=8192),
                content_type=content_type or 'video/mp4'
            )
            
            # Copiar headers importantes
            if 'Content-Length' in response.headers:
                stream_response['Content-Length'] = response.headers['Content-Length']
            if 'Content-Range' in response.headers:
                stream_response['Content-Range'] = response.headers['Content-Range']
            if 'Accept-Ranges' in response.headers:
                stream_response['Accept-Ranges'] = response.headers['Accept-Ranges']
            
            # Headers para video streaming
            stream_response['Accept-Ranges'] = 'bytes'
            stream_response['Cache-Control'] = 'public, max-age=3600'  # Cache por 1 hora
            
            # Status code
            status_code = response.status_code
            if status_code == 206:  # Partial Content (para range requests)
                stream_response.status_code = 206
            else:
                stream_response.status_code = 200
            
            return stream_response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en proxy de video: {e}")
            return HttpResponse(f'Error al obtener el video: {str(e)}', status=500)
        except Exception as e:
            logger.error(f"Error inesperado en proxy de video: {e}", exc_info=True)
            return HttpResponse('Error interno', status=500)


class StockDownloadView(LoginRequiredMixin, View):
    """Vista para descargar contenido stock y guardarlo en BD"""
    
    def post(self, request):
        """
        Descarga contenido stock y lo guarda en BD como Audio/Music/Image/Video
        
        Body JSON:
            - item: Objeto con datos del item de stock
            - content_type: 'image', 'video', 'audio'
            - project_id: ID del proyecto (opcional)
        """
        from django.core.files.base import ContentFile
        import requests
        from io import BytesIO
        
        try:
            data = json.loads(request.body)
            item = data.get('item')
            content_type = data.get('content_type', 'image')
            project_id = data.get('project_id')
            
            logger.info(f"StockDownloadView recibido: content_type={content_type}, project_id={project_id}, item_keys={list(item.keys()) if item else 'None'}")
            
            if not item:
                logger.error(f"StockDownloadView: Item no proporcionado. Data recibida: {data}")
                return JsonResponse({
                    'success': False,
                    'error': 'Item no proporcionado'
                }, status=400)
            
            # Obtener la URL directa del archivo (priorizar download_url sobre url)
            # download_url es la URL directa del archivo, url puede ser la página web
            # Para Freepik: 'url' es HTML, 'preview' es la URL directa
            download_url = item.get('download_url') or item.get('preview') or item.get('original_url')
            
            # Si download_url es una página HTML (especialmente Freepik), usar preview
            if download_url and isinstance(download_url, str) and download_url.endswith(('.htm', '.html')):
                logger.warning(f"StockDownloadView: download_url es HTML, usando preview en su lugar")
                download_url = item.get('preview') or item.get('thumbnail')
            
            # Fallback: intentar 'url' solo si no es HTML
            if not download_url:
                url_candidate = item.get('url')
                if url_candidate and isinstance(url_candidate, str) and not url_candidate.endswith(('.htm', '.html')):
                    download_url = url_candidate
            
            logger.info(f"StockDownloadView: download_url={download_url}, item.url={item.get('url')}, item.download_url={item.get('download_url')}, item.preview={item.get('preview')}")
            
            if not download_url:
                logger.error(f"StockDownloadView: URL de descarga no disponible. Item recibido: {json.dumps(item, default=str)}")
                return JsonResponse({
                    'success': False,
                    'error': 'URL de descarga no disponible en el item'
                }, status=400)
            
            # Obtener proyecto si se especificó
            project = None
            if project_id:
                try:
                    project = Project.objects.get(id=project_id)
                    # Verificar acceso usando ProjectService (incluye owner y colaboradores)
                    from core.services import ProjectService
                    if not ProjectService.user_has_access(project, request.user):
                        return JsonResponse({
                            'success': False,
                            'error': 'No tienes acceso a este proyecto'
                        }, status=403)
                except Project.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'error': 'Proyecto no encontrado'
                    }, status=404)
            
            # Descargar el archivo desde la URL directa
            try:
                logger.info(f"Descargando archivo de stock desde: {download_url}")
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(download_url, timeout=30, stream=True, headers=headers)
                response.raise_for_status()
                
                # Leer contenido en chunks para manejar archivos grandes
                file_bytes = b''
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file_bytes += chunk
                        # Limitar tamaño máximo (100MB)
                        if len(file_bytes) > 100 * 1024 * 1024:
                            raise ValueError('Archivo demasiado grande (máximo 100MB)')
                
                file_content = BytesIO(file_bytes)
                
                # Obtener content-type HTTP
                http_content_type = response.headers.get('Content-Type', '')
                
                # Detectar tipo de archivo usando magic bytes (más confiable que Content-Type)
                file_content.seek(0)
                first_bytes = file_content.read(16)
                file_content.seek(0)
                
                file_extension = None
                detected_mime = None
                
                # Detección por magic bytes
                if first_bytes.startswith(b'\xFF\xD8\xFF'):
                    file_extension = 'jpg'
                    detected_mime = 'image/jpeg'
                elif first_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
                    file_extension = 'png'
                    detected_mime = 'image/png'
                elif first_bytes.startswith(b'GIF87a') or first_bytes.startswith(b'GIF89a'):
                    file_extension = 'gif'
                    detected_mime = 'image/gif'
                elif first_bytes.startswith(b'RIFF') and len(first_bytes) > 8 and first_bytes[8:12] == b'WEBP':
                    file_extension = 'webp'
                    detected_mime = 'image/webp'
                elif first_bytes.startswith(b'\x00\x00\x00\x18ftypmp4') or first_bytes.startswith(b'\x00\x00\x00\x20ftypmp4'):
                    file_extension = 'mp4'
                    detected_mime = 'video/mp4'
                elif first_bytes.startswith(b'\x1a\x45\xdf\xa3'):
                    file_extension = 'webm'
                    detected_mime = 'video/webm'
                elif first_bytes.startswith(b'ID3') or first_bytes.startswith(b'\xFF\xFB') or first_bytes.startswith(b'\xFF\xF3'):
                    file_extension = 'mp3'
                    detected_mime = 'audio/mpeg'
                elif first_bytes.startswith(b'RIFF') and len(first_bytes) > 8 and first_bytes[8:12] == b'WAVE':
                    file_extension = 'wav'
                    detected_mime = 'audio/wav'
                elif first_bytes.startswith(b'OggS'):
                    file_extension = 'ogg'
                    detected_mime = 'audio/ogg'
                
                # Si no se detectó por magic bytes, usar Content-Type HTTP
                if not file_extension and http_content_type:
                    if 'image/jpeg' in http_content_type or 'image/jpg' in http_content_type:
                        file_extension = 'jpg'
                        detected_mime = 'image/jpeg'
                    elif 'image/png' in http_content_type:
                        file_extension = 'png'
                        detected_mime = 'image/png'
                    elif 'image/gif' in http_content_type:
                        file_extension = 'gif'
                        detected_mime = 'image/gif'
                    elif 'image/webp' in http_content_type:
                        file_extension = 'webp'
                        detected_mime = 'image/webp'
                    elif 'video/mp4' in http_content_type:
                        file_extension = 'mp4'
                        detected_mime = 'video/mp4'
                    elif 'video/webm' in http_content_type:
                        file_extension = 'webm'
                        detected_mime = 'video/webm'
                    elif 'audio/mpeg' in http_content_type or 'audio/mp3' in http_content_type:
                        file_extension = 'mp3'
                        detected_mime = 'audio/mpeg'
                    elif 'audio/wav' in http_content_type:
                        file_extension = 'wav'
                        detected_mime = 'audio/wav'
                    elif 'audio/ogg' in http_content_type:
                        file_extension = 'ogg'
                        detected_mime = 'audio/ogg'
                
                # Si no se pudo determinar desde magic bytes ni Content-Type, intentar desde URL
                if not file_extension:
                    url_path = download_url.split('?')[0]  # Remover query params
                    url_ext = url_path.split('.')[-1].lower() if '.' in url_path else None
                    # Validar extensión común
                    valid_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'webm', 'mp3', 'wav', 'ogg']
                    if url_ext in valid_extensions:
                        file_extension = url_ext
                
                # Fallback según tipo de contenido
                if not file_extension:
                    if content_type == 'image':
                        file_extension = 'jpg'
                        detected_mime = 'image/jpeg'
                    elif content_type == 'video':
                        file_extension = 'mp4'
                        detected_mime = 'video/mp4'
                    elif content_type == 'audio':
                        file_extension = 'mp3'
                        detected_mime = 'audio/mpeg'
                    else:
                        file_extension = 'bin'
                        detected_mime = 'application/octet-stream'
                
                # Usar MIME detectado por magic bytes si está disponible, sino usar HTTP Content-Type
                final_content_type = detected_mime or http_content_type
                
            except Exception as e:
                logger.error(f"Error descargando archivo de stock desde {download_url}: {e}", exc_info=True)
                return JsonResponse({
                    'success': False,
                    'error': f'Error al descargar el archivo: {str(e)}'
                }, status=500)
            
            # Guardar según el tipo de contenido
            if content_type == 'audio':
                # Determinar si es música o efecto de sonido
                audio_type = item.get('audio_type', 'music')
                
                if audio_type == 'music':
                    # Crear Music
                    from core.storage.gcs import gcs_storage
                    
                    music = Music.objects.create(
                        name=item.get('title', 'Música de stock'),
                        prompt=item.get('description', ''),
                        created_by=request.user,
                        project=project,
                        status='completed',
                        duration_ms=item.get('duration', 0) * 1000 if item.get('duration') else 0
                    )
                    
                    # Subir a GCS
                    # Usar path con proyecto si está disponible, sino sin proyecto
                    if project:
                        gcs_path = f"projects/{project.id}/music/{music.id}/music.{file_extension}"
                    else:
                        gcs_path = f"music/{music.id}/music.{file_extension}"
                    
                    file_content.seek(0)
                    gcs_full_path = gcs_storage.upload_from_bytes(
                        file_content.read(),
                        gcs_path,
                        content_type=final_content_type or 'audio/mpeg'
                    )
                    
                    # Guardar el path completo retornado por upload_from_bytes (formato: gs://bucket/path)
                    music.gcs_path = gcs_full_path
                    music.save()
                    
                    return JsonResponse({
                        'success': True,
                        'message': 'Música guardada correctamente',
                        'item': {
                            'id': music.id,
                            'type': 'music',
                            'name': music.name
                        }
                    })
                else:
                    # Crear Audio
                    from core.storage.gcs import gcs_storage
                    
                    audio = Audio.objects.create(
                        title=item.get('title', 'Audio de stock'),
                        text=item.get('description', ''),
                        voice_id='stock',
                        voice_name='Stock Audio',
                        created_by=request.user,
                        project=project,
                        status='completed'
                    )
                    
                    # Subir a GCS
                    # Usar path con proyecto si está disponible, sino sin proyecto
                    if project:
                        gcs_path = f"projects/{project.id}/audios/{audio.id}/audio.{file_extension}"
                    else:
                        gcs_path = f"audios/{audio.id}/audio.{file_extension}"
                    
                    file_content.seek(0)
                    gcs_full_path = gcs_storage.upload_from_bytes(
                        file_content.read(),
                        gcs_path,
                        content_type=final_content_type or 'audio/mpeg'
                    )
                    
                    # Guardar el path completo retornado por upload_from_bytes (formato: gs://bucket/path)
                    audio.gcs_path = gcs_full_path
                    audio.save()
                    
                    return JsonResponse({
                        'success': True,
                        'message': 'Audio guardado correctamente',
                        'item': {
                            'id': audio.id,
                            'type': 'audio',
                            'title': audio.title
                        }
                    })
            
            elif content_type == 'image':
                from core.storage.gcs import gcs_storage
                
                image = Image.objects.create(
                    title=item.get('title', 'Imagen de stock'),
                    prompt=item.get('description', ''),
                    created_by=request.user,
                    project=project,
                    status='completed',
                    type='text_to_image'
                )
                
                # Subir a GCS
                # Usar path con proyecto si está disponible, sino sin proyecto
                if project:
                    gcs_path = f"projects/{project.id}/images/{image.id}/image.{file_extension}"
                else:
                    gcs_path = f"images/{image.id}/image.{file_extension}"
                
                file_content.seek(0)
                gcs_full_path = gcs_storage.upload_from_bytes(
                    file_content.read(),
                    gcs_path,
                    content_type=final_content_type or 'image/jpeg'
                )
                
                # Guardar el path completo retornado por upload_from_bytes (formato: gs://bucket/path)
                image.gcs_path = gcs_full_path
                image.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Imagen guardada correctamente',
                    'item': {
                        'id': image.id,
                        'type': 'image',
                        'title': image.title
                    }
                })
            
            elif content_type == 'video':
                from core.storage.gcs import gcs_storage
                
                video = Video.objects.create(
                    title=item.get('title', 'Video de stock'),
                    script=item.get('description', ''),
                    created_by=request.user,
                    project=project,
                    status='completed',
                    type='general'
                )
                
                # Subir a GCS
                # Usar path con proyecto si está disponible, sino sin proyecto
                if project:
                    gcs_path = f"projects/{project.id}/videos/{video.id}/video.{file_extension}"
                else:
                    gcs_path = f"videos/{video.id}/video.{file_extension}"
                
                file_content.seek(0)
                gcs_full_path = gcs_storage.upload_from_bytes(
                    file_content.read(),
                    gcs_path,
                    content_type=final_content_type or 'video/mp4'
                )
                
                # Guardar el path completo retornado por upload_from_bytes (formato: gs://bucket/path)
                video.gcs_path = gcs_full_path
                video.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Video guardado correctamente',
                    'item': {
                        'id': video.id,
                        'type': 'video',
                        'title': video.title
                    }
                })
            
            else:
                return JsonResponse({
                    'success': False,
                    'error': f'Tipo de contenido no soportado: {content_type}'
                }, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'JSON inválido'
            }, status=400)
        except Exception as e:
            logger.error(f"Error en StockDownloadView: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
