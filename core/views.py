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
from django.contrib.auth.decorators import permission_required, login_required
from django.utils import timezone
from django.core.paginator import Paginator
from django.db import models
from datetime import datetime
from django.db.models import Max, Q, Sum, Count
from django.contrib.auth import authenticate, login, logout
import os
from django.contrib.auth.models import User, Group
from .forms import CustomUserCreationForm, PendingUserCreationForm, ActivationSetPasswordForm
from django.db import IntegrityError
import json

from celery import current_app

from django.core.mail import send_mail
from django.utils.html import strip_tags

# Lazy import to avoid CI failures (rembg requires onnxruntime)
def get_remove_image_background_task():
    from core.tasks import remove_image_background_task
    return remove_image_background_task

from .models import Project, Video, Image, Audio, Script, Scene, UserCredits, CreditTransaction, ServiceUsage, Notification, GenerationTask, PromptTemplate, ProjectMember
from .forms import VideoBaseForm, HeyGenAvatarV2Form, HeyGenAvatarIVForm, GeminiVeoVideoForm, SoraVideoForm, GeminiImageForm, AudioForm, ScriptForm
from .services import ProjectService, VideoService, ImageService, AudioService, APIService, SceneService, VideoCompositionService, ValidationException, ServiceException, ImageGenerationException, InvitationService
from .services.credits import CreditService, InsufficientCreditsException, RateLimitExceededException
from .ai_services.model_config import get_model_info_for_item
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
# Solo muestra documentación pública (docs/public/)
def docs_structure(request):
    base_dir = os.path.join(settings.BASE_DIR, 'docs', 'public')

    def build_tree(path, relative_path=''):
        tree = {}
        if not os.path.exists(path):
            return tree
        for item in sorted(os.listdir(path)):
            item_path = os.path.join(path, item)
            # Ignorar archivos ocultos y __pycache__
            if item.startswith('.') or item == '__pycache__':
                continue
            if os.path.isdir(item_path):
                subtree = build_tree(item_path, os.path.join(relative_path, item))
                if subtree:  # Solo agregar si tiene contenido
                    tree[item] = subtree
            elif item.endswith('.md'):
                # Guardar ruta relativa desde docs/public/
                rel_path = os.path.join(relative_path, item).replace('\\', '/')
                tree[item] = rel_path
        return tree

    structure = build_tree(base_dir)
    return JsonResponse(structure)

# Vista para devolver el contenido de un archivo markdown
# Solo accede a documentación pública (docs/public/)
def docs_md_view(request, path):
    # path puede ser: "api/services/google/video/text_to_video" o "app/GUIA_USUARIO"
    # Eliminar trailing slash si existe
    path = path.rstrip('/')
    
    try:
        # Construir ruta completa desde docs/public/
        md_file_path = os.path.join(settings.BASE_DIR, 'docs', 'public', path + '.md')
        
        # Normalizar la ruta para evitar problemas de seguridad
        md_file_path = os.path.normpath(md_file_path)
        base_dir = os.path.normpath(os.path.join(settings.BASE_DIR, 'docs', 'public'))
        
        # Debug logging (solo en desarrollo)
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"docs_md_view - path recibido: {path}")
        logger.debug(f"docs_md_view - md_file_path: {md_file_path}")
        logger.debug(f"docs_md_view - base_dir: {base_dir}")
        logger.debug(f"docs_md_view - existe: {os.path.exists(md_file_path)}")
        
        # Verificar que el archivo esté dentro del directorio permitido
        if not md_file_path.startswith(base_dir):
            logger.warning(f"Ruta no permitida: {md_file_path} no está en {base_dir}")
            return JsonResponse({
                'error': 'Ruta no permitida',
                'content': ''
            }, status=400)
        
        if not os.path.exists(md_file_path):
            logger.warning(f"Archivo no encontrado: {md_file_path}")
            # Listar archivos en el directorio para debug
            parent_dir = os.path.dirname(md_file_path)
            if os.path.exists(parent_dir):
                files = os.listdir(parent_dir)
                logger.debug(f"Archivos en {parent_dir}: {files}")
            return JsonResponse({
                'error': f'Documento no encontrado: {path}',
                'content': ''
            }, status=404)
        
        # Leer el archivo
        try:
            with open(md_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Intentar con otra codificación si UTF-8 falla
            with open(md_file_path, 'r', encoding='latin-1') as f:
                content = f.read()
        except Exception as e:
            return JsonResponse({
                'error': f'Error al leer el archivo: {str(e)}',
                'content': ''
            }, status=500)
        
        return JsonResponse({'content': content})
    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error en docs_md_view: {e}", exc_info=True)
        return JsonResponse({
            'error': f'Error del servidor: {str(e)}',
            'content': ''
        }, status=500)

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
    from django.core.mail import EmailMultiAlternatives
    
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
        
        # Renderizar mensajes (texto plano y HTML)
        subject = f'Invitación para unirte al proyecto "{invitation.project.name}"'
        text_content = render_to_string('projects/invitation_email.txt', context)
        html_content = render_to_string('projects/invitation_email.html', context)
        
        # Enviar email con HTML
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
        email = EmailMultiAlternatives(
            subject,
            text_content,
            from_email,
            [invitation.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f"Email de invitación enviado a {invitation.email} para proyecto {invitation.project.id}")
        
    except Exception as e:
        logger.error(f"Error enviando email de invitación a {invitation.email}: {e}")
        # No lanzar excepción para no interrumpir el flujo


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


class HeyGenPreloadMixin:
    """Mixin para precargar datos de HeyGen en background cuando se accede a vistas de creación"""
    
    def dispatch(self, request, *args, **kwargs):
        """Precargar datos de HeyGen en background al acceder a la vista"""
        response = super().dispatch(request, *args, **kwargs)
        
        # Precargar en background usando threading (no bloquea la respuesta)
        import threading
        def preload_heygen_data():
            try:
                api_service = APIService()
                # Precargar avatares, voces e image assets con caché
                # Esto los guardará en Redis para uso futuro
                api_service.list_avatars(use_cache=True)
                api_service.list_voices(use_cache=True)
                api_service.list_image_assets(use_cache=True)
                logger.debug("✅ Datos de HeyGen precargados en background")
            except Exception as e:
                logger.debug(f"⚠️ Error precargando datos de HeyGen (no crítico): {e}")
        
        # Ejecutar en thread separado para no bloquear la respuesta
        thread = threading.Thread(target=preload_heygen_data, daemon=True)
        thread.start()
        
        return response


class SidebarProjectsMixin:
    """Mixin para exponer los proyectos del usuario en plantillas con sidebar."""
    _sidebar_projects_cache = None

    def get_sidebar_projects(self):
        if self._sidebar_projects_cache is None:
            self._sidebar_projects_cache = ProjectService.get_user_projects(self.request.user)
        return self._sidebar_projects_cache

    def add_sidebar_projects_to_context(self, context):
        context.setdefault('projects', self.get_sidebar_projects())
        return context

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return self.add_sidebar_projects_to_context(context)

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

    
    def get_queryset(self):
        """Obtener proyectos optimizado"""
        return ProjectService.get_user_projects(self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['show_header'] = True
        
        # Obtener query de búsqueda
        search_query = self.request.GET.get('q', '').strip()
        context['search_query'] = search_query

        # 1. OBTENER FILTRO DE LA URL (Nuevo)
        filter_type = self.request.GET.get('filter', 'personal') # Default: personal
        context['current_filter'] = filter_type
        
        user = self.request.user
        
        # 2. DEFINIR LÓGICA DE FILTRADO (Nuevo)
        if filter_type == 'shared':
            # COMPARTIDO: Items en proyectos donde soy miembro pero NO dueño
            shared_project_ids = ProjectMember.objects.filter(user=user).values_list('project_id', flat=True)
            # Filtro: Está en un proyecto compartido Y el dueño del proyecto no soy yo
            base_filter = Q(project_id__in=shared_project_ids) & ~Q(project__owner=user)
        else:
            # PERSONAL: Items creados por mí (estén en proyecto o no)
            base_filter = Q(created_by=user)

        # 3. ESTADÍSTICAS
        all_user_projects = ProjectService.get_user_projects(user)
        all_project_ids = all_user_projects.values_list('id', flat=True)
        stats_filter = Q(project_id__in=all_project_ids) | Q(project__isnull=True, created_by=user)

        context.update({
            'total_videos': Video.objects.filter(stats_filter).count(),
            'total_images': Image.objects.filter(stats_filter).count(),
            'total_scripts': Script.objects.filter(stats_filter).count(),
            'completed_videos': Video.objects.filter(stats_filter, status='completed').count(),
            'processing_videos': Video.objects.filter(stats_filter, status='processing').count(),
            'completed_scripts': Script.objects.filter(stats_filter, status='completed').count(),
        })
        
        # 4. APLICAR FILTRO A LA LISTA DE ITEMS (Modificado)
        # La lógica de carga de items se ha movido al frontend (Alpine.js)
        # para mejorar el tiempo de carga inicial.
        # Se mantiene la variable 'current_filter' para que el frontend sepa qué cargar.
        
        # Eliminamos la carga síncrona de items para optimizar
        context['recent_items'] = []
        context['page_obj'] = None

        
        return context

# ====================
# PROJECT VIEWS
# ====================
class ProjectItemsManagementView:
    """Clase para gestionar operaciones de items dentro de proyectos"""
    
    # Modelos que usan UUID (Video, Image, Audio)
    UUID_MODELS = (Video, Image, Audio)
    # Modelos que usan ID numérico (Script)
    ID_MODELS = (Script,)
    ITEM_MODELS = UUID_MODELS + ID_MODELS
    
    @classmethod
    def get_item(cls, item_id):
        """Buscar un item en todos los modelos (soporta UUID o ID)"""
        import uuid as uuid_module
        
        # Intentar primero por UUID en modelos que lo usan
        try:
            item_uuid = uuid_module.UUID(str(item_id))
            for model in cls.UUID_MODELS:
                try:
                    return model.objects.get(uuid=item_uuid)
                except model.DoesNotExist:
                    continue
        except (ValueError, TypeError):
            pass
        
        # Intentar por ID numérico
        try:
            numeric_id = int(item_id)
            for model in cls.ID_MODELS:
                try:
                    return model.objects.get(id=numeric_id)
                except model.DoesNotExist:
                    continue
        except (ValueError, TypeError):
            pass
        
        return None
    
    @classmethod
    def move_item(cls, request, item_id):
        if request.method != "POST":
            return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
        
        import json
        import uuid as uuid_module
        data = json.loads(request.body)
        project_id = data.get('project_id')  # Puede ser UUID string o null
        
        item = cls.get_item(item_id)
        if not item:
            return JsonResponse({'success': False, 'error': 'Item no encontrado'}, status=404)
        
        # Si project_id es null/None, quitar del proyecto
        if not project_id:
            item.project = None
            item.save()
            return JsonResponse({'success': True, 'new_project_name': None})
        
        # Buscar proyecto por UUID
        try:
            project_uuid = uuid_module.UUID(str(project_id))
            project = Project.objects.get(uuid=project_uuid)
        except (ValueError, Project.DoesNotExist):
            return JsonResponse({'success': False, 'error': 'Proyecto no encontrado'}, status=404)
        
        # Mover item al proyecto
        item.project = project
        item.save()
        
        return JsonResponse({'success': True, 'new_project_name': project.name})

class ProjectOverviewView(SidebarProjectsMixin, BreadcrumbMixin, ServiceMixin, DetailView):
    """Vista general de un proyecto con estadísticas y links rápidos"""
    model = Project
    template_name = 'projects/overview.html'
    context_object_name = 'project'
    pk_url_kwarg = 'project_uuid'
    slug_field = 'uuid'
    slug_url_kwarg = 'project_uuid'
    
    def get_object(self, queryset=None):
        """Obtener proyecto y verificar permisos"""
        project_uuid = self.kwargs.get('project_uuid')
        project = get_object_or_404(Project, uuid=project_uuid)
        
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
        project = self.object
        
        # Estadísticas del proyecto
        context['stats'] = {
            'videos': {
                'total': project.videos.count(),
                'completed': project.videos.filter(status='completed').count(),
                'processing': project.videos.filter(status='processing').count(),
                'pending': project.videos.filter(status='pending').count(),
            },
            'images': {
                'total': project.images.count(),
                'completed': project.images.filter(status='completed').count(),
                'processing': project.images.filter(status='processing').count(),
                'pending': project.images.filter(status='pending').count(),
            },
            'audios': {
                'total': project.audios.count(),
                'completed': project.audios.filter(status='completed').count(),
                'processing': project.audios.filter(status='processing').count(),
                'pending': project.audios.filter(status='pending').count(),
            },
            'scripts': {
                'total': project.scripts.count(),
                'completed': project.scripts.filter(status='completed').count(),
            },
        }
        
        # Últimos items creados (máximo 5 de cada tipo)
        from django.db.models import Q
        from django.utils import timezone
        from datetime import timedelta
        
        # Últimos videos
        recent_videos = project.videos.select_related('project').order_by('-created_at')[:5]
        context['recent_videos'] = recent_videos
        
        # Últimas imágenes
        recent_images = project.images.select_related('project').order_by('-created_at')[:5]
        context['recent_images'] = recent_images
        
        # Últimos audios
        recent_audios = project.audios.select_related('project').order_by('-created_at')[:5]
        context['recent_audios'] = recent_audios
        
        # Información del proyecto
        context['user_role'] = project.get_user_role(self.request.user)
        context['project_owner'] = project.owner
        context['project_members'] = project.members.select_related('user').all()
        
        return context


class ProjectDetailView(SidebarProjectsMixin, BreadcrumbMixin, ServiceMixin, DetailView):
    """Detalle de un proyecto con sus videos (legacy - mantiene tabs)"""
    model = Project
    template_name = 'projects/detail.html'
    context_object_name = 'project'
    pk_url_kwarg = 'project_uuid'
    slug_field = 'uuid'
    slug_url_kwarg = 'project_uuid'
    
    def get(self, request, *args, **kwargs):
        """Si no hay tab especificado, redirigir a overview"""
        if 'tab' not in kwargs:
            project_uuid = kwargs.get('project_uuid')
            return redirect('core:project_overview', project_uuid=project_uuid)
        return super().get(request, *args, **kwargs)
    
    def get_object(self, queryset=None):
        """Obtener proyecto con videos optimizado y verificar permisos"""
        project_uuid = self.kwargs.get('project_uuid')
        project = ProjectService.get_project_with_videos_by_uuid(project_uuid)
        
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
                'id': str(video.uuid),
                'title': video.title,
                'status': video.status,
                'created_at': video.created_at,
                'project': video.project,
                'signed_url': None,
                'detail_url': reverse('core:project_video_detail', args=[self.object.uuid, video.uuid]),
                'delete_url': reverse('core:video_delete', args=[video.uuid]),
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
                'id': str(image.uuid),
                'title': image.title,
                'status': image.status,
                'created_at': image.created_at,
                'project': image.project,
                'signed_url': None,
                'detail_url': reverse('core:project_image_detail', args=[self.object.uuid, image.uuid]),
                'delete_url': reverse('core:image_delete', args=[image.uuid]),
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
                'id': str(audio.uuid),
                'title': audio.title,
                'status': audio.status,
                'created_at': audio.created_at,
                'project': audio.project,
                'signed_url': None,
                'audio_background': audio.background_gradient,
                'detail_url': reverse('core:project_audio_detail', args=[self.object.uuid, audio.uuid]),
                'delete_url': reverse('core:audio_delete', args=[audio.uuid]),
            }
            if audio.status == 'completed' and audio.gcs_path:
                try:
                    audio_data = audio_service.get_audio_with_signed_url(audio)
                    item_data['signed_url'] = audio_data.get('signed_url')
                except Exception:
                    pass
            audios_items.append(item_data)
        
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
            'scripts'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['show_header'] = True
        
        # Agregar estadísticas de proyectos
        user_projects = ProjectService.get_user_projects(self.request.user)
        context['total_projects'] = user_projects.count()
        
        return context


class LibraryItem:
    __slots__ = ('item', 'type', 'created_at', 'title', 'status')
    def __init__(self, item, item_type):
        self.item = item
        self.type = item_type
        self.created_at = item.created_at
        self.title = item.title if hasattr(item, 'title') else (getattr(item, 'name', 'Sin título'))
        self.status = getattr(item, 'status', None)

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
        
        # Helper para evitar repetición
        def get_videos():
            return Video.objects.filter(created_by=user).select_related('project')\
                .only('uuid', 'title', 'created_at', 'status', 'project__name', 'project__uuid', 'gcs_path', 'script')
        
        def get_images():
            return Image.objects.filter(created_by=user).select_related('project')\
                .only('uuid', 'title', 'created_at', 'status', 'project__name', 'project__uuid', 'gcs_path', 'prompt')
                
        def get_audios():
            return Audio.objects.filter(created_by=user).select_related('project')\
                .only('uuid', 'title', 'created_at', 'status', 'project__name', 'project__uuid', 'gcs_path', 'text')
        
        def get_scripts():
            return Script.objects.filter(created_by=user).select_related('project')\
                .only('id', 'title', 'created_at', 'status', 'project__name', 'project__uuid', 'original_script')

        # Filtrar por tipo si se especifica
        if item_type == 'video':
            querysets = [('video', get_videos())]
        elif item_type == 'image':
            querysets = [('image', get_images())]
        elif item_type == 'audio':
            querysets = [('audio', get_audios())]
        elif item_type == 'script':
            querysets = [('script', get_scripts())]
        else:
            # Todos los tipos mezclados
            querysets = [
                ('video', get_videos()),
                ('image', get_images()),
                ('audio', get_audios()),
                ('script', get_scripts()),
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
                elif item_type_name == 'script':
                    queryset = queryset.filter(Q(title__icontains=search_query) | Q(original_script__icontains=search_query))
            
            # Convertir a lista y agregar tipo
            # Usar LibraryItem es mucho más rápido que crear tipos dinámicos
            for item in queryset:
                all_items.append(LibraryItem(item, item_type_name))
        
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
        # Estas consultas son rápidas (COUNT)
        context['stats'] = {
            'total': Video.objects.filter(created_by=user).count() + 
                    Image.objects.filter(created_by=user).count() + 
                    Audio.objects.filter(created_by=user).count() + 
                    Script.objects.filter(created_by=user).count(),
            'videos': Video.objects.filter(created_by=user).count(),
            'images': Image.objects.filter(created_by=user).count(),
            'audios': Audio.objects.filter(created_by=user).count(),
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
                detail_url = reverse('core:video_detail', args=[item.uuid])
                delete_url = reverse('core:video_delete', args=[item.uuid])
            elif item_wrapper.type == 'image':
                detail_url = reverse('core:image_detail', args=[item.uuid])
                delete_url = reverse('core:image_delete', args=[item.uuid])
            elif item_wrapper.type == 'audio':
                detail_url = reverse('core:audio_detail', args=[item.uuid])
                delete_url = reverse('core:audio_delete', args=[item.uuid])
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
                    logger.error(f"Error al generar URL firmada para {item_wrapper.type} {item.id if hasattr(item, 'id') else 'unknown'}: {e}")
            
            # Para videos, images y audios usar UUID como id; para el resto usar id numérico
            item_id = str(item.uuid) if item_wrapper.type in ('video', 'image', 'audio') else item.id
            
            items_with_urls.append({
                'type': item_wrapper.type,
                'id': item_id,
                'object': item, # Agregado para que el template pueda acceder a propiedades (script, prompt)
                'title': item_wrapper.title,
                'status': item_wrapper.status,
                'created_at': item_wrapper.created_at,
                'project': item.project if hasattr(item, 'project') else None,
                'signed_url': signed_url,
                'detail_url': detail_url,
                'delete_url': delete_url,
                'audio_background': item.background_gradient if item_wrapper.type == 'audio' else None,
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
        return reverse('core:project_overview', kwargs={'project_uuid': self.object.uuid})
    
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
    
    def post(self, request, project_uuid):
        """Actualizar nombre del proyecto"""
        project = get_object_or_404(Project, uuid=project_uuid)
        
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
    pk_url_kwarg = 'project_uuid'
    slug_field = 'uuid'
    slug_url_kwarg = 'project_uuid'
    
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
            {'label': self.object.name, 'url': reverse('core:project_overview', args=[self.object.uuid])},
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
            return redirect('core:project_overview', project_uuid=self.object.uuid)


# ====================
# VIDEO VIEWS
# ====================

class VideoLibraryView(SidebarProjectsMixin, BreadcrumbMixin, ServiceMixin, HeyGenPreloadMixin, View):
    """Vista unificada para creación y biblioteca de videos"""
    template_name = 'creation/base_creation.html'
    
    def get_project(self):
        """Obtener proyecto del contexto (opcional)"""
        project_uuid = self.kwargs.get('project_uuid')
        if project_uuid:
            return get_object_or_404(Project, uuid=project_uuid)
        return None
    
    def get(self, request, *args, **kwargs):
        from django.db.models import Q
        
        project = self.get_project()
        user = request.user
        
        # Calcular conteo de videos
        if project:
            video_count = Video.objects.filter(project=project).count()
        else:
            user_projects = ProjectService.get_user_projects(user)
            user_project_ids = [p.id for p in user_projects]
            base_filter = Q(project_id__in=user_project_ids) | Q(project__isnull=True, created_by=user)
            video_count = Video.objects.filter(base_filter).count()
        
        # Obtener template "General" por defecto (sin servicio específico)
        default_template = None
        default_template_id = None
        try:
            from core.utils.prompt_templates import get_default_template
            # Intentar obtener un template "General" genérico (sin servicio específico)
            default_template = PromptTemplate.objects.filter(
                name='General',
                template_type='video',
                is_public=True,
                is_active=True
            ).order_by('-usage_count').first()
            
            if default_template:
                default_template_id = str(default_template.uuid)
        except Exception as e:
            logger.error(f"Error obteniendo template por defecto: {e}")
        
        context = {
            'project': project,
            'active_tab': 'video',
            'breadcrumbs': self.get_breadcrumbs(),
            'projects': ProjectService.get_user_projects(request.user),
            'items_count': video_count,
            'default_template_id': default_template_id,  # Template "General" por defecto
        }
        
        if project:
            context['user_role'] = project.get_user_role(request.user)
            context['project_owner'] = project.owner
            context['project_members'] = project.members.select_related('user').all()
        
        return render(request, self.template_name, context)
    
    def get_breadcrumbs(self):
        project = self.get_project()
        if project:
            return [
                {
                    'label': project.name, 
                    'url': reverse('core:project_overview', args=[project.uuid])
                },
                {'label': 'Videos', 'url': None}
            ]
        return [
            {'label': 'Videos', 'url': None}
        ]


class VideoDetailView(SidebarProjectsMixin, BreadcrumbMixin, ServiceMixin, DetailView):
    """Detalle de un video - usa el layout de creación unificado"""
    model = Video
    template_name = 'creation/base_creation.html'
    context_object_name = 'video'
    
    def get_object(self, queryset=None):
        """Buscar video por UUID"""
        if queryset is None:
            queryset = self.get_queryset()
        video_uuid = self.kwargs.get('video_uuid')
        return get_object_or_404(queryset, uuid=video_uuid)
    
    def get_project(self):
        """Obtener proyecto de la URL o del objeto"""
        project_uuid = self.kwargs.get('project_uuid')
        if project_uuid:
            return get_object_or_404(Project, uuid=project_uuid)
        return self.object.project
    
    def get_breadcrumbs(self):
        project = self.get_project()
        breadcrumbs = []
        if project:
            breadcrumbs.append({
                'label': project.name, 
                'url': reverse('core:project_overview', args=[project.uuid])
            })
            breadcrumbs.append({
                'label': 'Videos', 
                'url': reverse('core:project_videos_library', args=[project.uuid])
            })
        else:
            breadcrumbs.append({'label': 'Videos', 'url': reverse('core:video_library')})
        breadcrumbs.append({'label': self.object.title, 'url': None})
        return breadcrumbs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_project()
        context['active_tab'] = 'video'
        context['initial_item_type'] = 'video'
        context['initial_item_id'] = str(self.object.uuid)
        if project:
            context['project'] = project
            context['user_role'] = project.get_user_role(self.request.user)
            context['project_owner'] = project.owner
            context['project_members'] = project.members.select_related('user').all()
        return context


class VideoCreateView(SidebarProjectsMixin, BreadcrumbMixin, ServiceMixin, FormView):
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
        project_uuid = self.kwargs.get('project_uuid')
        if project_uuid:
            return get_object_or_404(Project, uuid=project_uuid)
        return None
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_project()
        if project:
            context['project'] = project
            context['user_role'] = project.get_user_role(self.request.user)
            context['project_owner'] = project.owner
            context['project_members'] = project.members.select_related('user').all()
            context.setdefault('active_tab', 'videos')
        return context
    
    def get_breadcrumbs(self):
        project = self.get_project()
        if project:
            return [
                {
                    'label': project.name, 
                    'url': reverse('core:project_detail', args=[project.uuid])
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
            
            # Encolar generación de video automáticamente después de crear
            try:
                task = video_service.generate_video_async(video)
                messages.success(request, f'Video "{title}" creado y encolado para generación. El proceso puede tardar varios minutos.')
                # Disparar toast directamente
                request.session['show_toast'] = {
                    'type': 'success',
                    'title': 'Video encolado',
                    'message': f'"{title}" está en cola para generación',
                    'auto_close': 5
                }
            except (ValidationException, ServiceException) as e:
                messages.warning(request, f'Video "{title}" creado, pero hubo un error al encolar la generación: {str(e)}')
                request.session['show_toast'] = {
                    'type': 'warning',
                    'title': 'Error al encolar',
                    'message': str(e),
                    'auto_close': 8
                }
            except Exception as e:
                messages.warning(request, f'Video "{title}" creado, pero hubo un error inesperado al encolar la generación: {str(e)}')
                request.session['show_toast'] = {
                    'type': 'error',
                    'title': 'Error inesperado',
                    'message': str(e),
                    'auto_close': 10
                }
            
            return redirect('core:video_detail', video_uuid=video.uuid)
            
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
        elif video_type == 'manim_quote':
            config = self._build_manim_config(request)
        
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
            'generate_audio': request.POST.get('generate_audio') == 'on',  # Checkbox devuelve 'on' si está marcado
        }
        
        # Parámetros específicos de Veo 3/3.1
        if request.POST.get('resolution'):
            config['resolution'] = request.POST.get('resolution')
        if request.POST.get('resize_mode'):
            config['resize_mode'] = request.POST.get('resize_mode')
        
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

    def _build_manim_config(self, request):
        """Configuración para Manim Animations (Citas, Gráficos, etc.)"""
        # El tipo exacto de animación (quote, bar_chart, etc.)
        animation_type = request.POST.get('manim_animation_type', 'quote')
        
        config = {
            'animation_type': animation_type,
            'model_id': 'manim-quote',
            'quality': request.POST.get('quality', 'k'),
            'font_family': request.POST.get('font_family', 'normal'),
            'text_color': request.POST.get('text_color_text', request.POST.get('text_color', '#FFFFFF')),
            'container_color': request.POST.get('container_color_text', request.POST.get('container_color', '#0066CC')),
        }
        
        if animation_type == 'quote':
            display_time = request.POST.get('display_time')
            try:
                display_time_val = float(display_time) if display_time else None
            except (ValueError, TypeError):
                display_time_val = None
            config.update({
                'author': request.POST.get('author', ''),
                'display_time': display_time_val,
            })
        elif animation_type in ['bar_chart', 'modern_bar_chart', 'line_chart']:
            try:
                bar_width = float(request.POST.get('bar_width', 0.8))
            except (ValueError, TypeError):
                bar_width = 0.8
            
            # Estructurar datos para el gráfico de barras (Clásico o Moderno)
            try:
                num_bars = int(request.POST.get('num_bars', 0))
            except (ValueError, TypeError):
                num_bars = 0
                
            labels = []
            values = []
            bar_colors = []
            top_texts = []
            
            for i in range(1, num_bars + 1):
                label = request.POST.get(f'bar_label_{i}', f'Item {i}')
                value_str = request.POST.get(f'bar_value_{i}', '0')
                try:
                    value = float(value_str) if value_str.strip() else 0.0
                except (ValueError, TypeError):
                    value = 0.0
                    
                color = request.POST.get(f'bar_color_{i}', '#0066CC')
                top_text = request.POST.get(f'bar_top_text_{i}', '')
                
                labels.append(label)
                values.append(value)
                bar_colors.append(color)
                top_texts.append(top_text)
            
            config.update({
                'title': request.POST.get('chart_title', 'Gráfico de Barras'),
                'x_axis_label': request.POST.get('x_axis_label', 'Categorías'),
                'y_axis_label': request.POST.get('y_axis_label', 'Valores'),
                'bar_width': bar_width,
                'show_labels': request.POST.get('show_labels') == 'on',
                'labels': labels,
                'values': values,
                'bar_colors': bar_colors,
                'top_texts': top_texts,
            })

            if animation_type == 'line_chart':
                if bar_colors:
                    config['line_color'] = bar_colors[0]
                
                # Configuración extra para Line Chart
                try:
                    point_radius = float(request.POST.get('point_radius', 0.1))
                    line_width = float(request.POST.get('line_width', 4))
                except (ValueError, TypeError):
                    point_radius = 0.1
                    line_width = 4
                
                config['point_radius'] = point_radius
                config['line_width'] = line_width
            
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
        project_uuid = self.kwargs['project_uuid']
        return get_object_or_404(Project, uuid=project_uuid)
    
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
            
            # Encolar generación de video automáticamente después de crear
            try:
                task = video_service.generate_video_async(video)
                messages.success(request, f'Video "{title}" creado y encolado para generación. El proceso puede tardar varios minutos.')
                # Disparar toast directamente
                request.session['show_toast'] = {
                    'type': 'success',
                    'title': 'Video encolado',
                    'message': f'"{title}" está en cola para generación',
                    'auto_close': 5
                }
            except (ValidationException, ServiceException) as e:
                messages.warning(request, f'Video "{title}" creado, pero hubo un error al encolar la generación: {str(e)}')
                request.session['show_toast'] = {
                    'type': 'warning',
                    'title': 'Error al encolar',
                    'message': str(e),
                    'auto_close': 8
                }
            except Exception as e:
                messages.warning(request, f'Video "{title}" creado, pero hubo un error inesperado al encolar la generación: {str(e)}')
                request.session['show_toast'] = {
                    'type': 'error',
                    'title': 'Error inesperado',
                    'message': str(e),
                    'auto_close': 10
                }
            
            return redirect('core:video_detail', video_uuid=video.uuid)
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
        elif video_type == 'manim_quote':
            config = self._build_manim_quote_config(request)
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
        config = {
            'veo_model': request.POST.get('veo_model', 'veo-2.0-generate-001'),
            'aspect_ratio': request.POST.get('aspect_ratio', '16:9'),
            'duration': int(request.POST.get('duration', 8)),
            'generate_audio': request.POST.get('generate_audio') == 'on',  # Checkbox devuelve 'on' si está marcado
        }
        
        # Parámetros específicos de Veo 3/3.1
        if request.POST.get('resolution'):
            config['resolution'] = request.POST.get('resolution')
        if request.POST.get('resize_mode'):
            config['resize_mode'] = request.POST.get('resize_mode')
        
        return config
    
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
    
    def _build_manim_quote_config(self, request):
        """Configuración para Manim Quote y Bar Chart"""
        # Determinar el tipo de animación
        animation_type = request.POST.get('manim_animation_type', 'quote')
        
        config = {
            'animation_type': animation_type,
            'model_id': 'manim-quote',
            'quality': request.POST.get('quality', 'k'),
            'font_family': request.POST.get('font_family', 'normal'),
            'text_color': request.POST.get('text_color_text', request.POST.get('text_color', '#FFFFFF')),
            'container_color': request.POST.get('container_color_text', request.POST.get('container_color', '#0066CC')),
        }
        
        if animation_type in ['bar_chart', 'modern_bar_chart']:
            # Estructurar datos para el gráfico de barras (Clásico o Moderno)
            try:
                num_bars = int(request.POST.get('num_bars', 0))
            except (ValueError, TypeError):
                num_bars = 0
            
            labels = []
            values = []
            bar_colors = []
            top_texts = []
            
            for i in range(1, num_bars + 1):
                label = request.POST.get(f'bar_label_{i}', f'Item {i}')
                value_str = request.POST.get(f'bar_value_{i}', '0')
                try:
                    value = float(value_str) if value_str.strip() else 0.0
                except (ValueError, TypeError):
                    value = 0.0
                    
                color = request.POST.get(f'bar_color_{i}', '#0066CC')
                top_text = request.POST.get(f'bar_top_text_{i}', '')
                
                labels.append(label)
                values.append(value)
                bar_colors.append(color)
                top_texts.append(top_text)
            
            config.update({
                'title': request.POST.get('chart_title', 'Gráfico de Barras'),
                'x_axis_label': request.POST.get('x_axis_label', 'Categorías'),
                'y_axis_label': request.POST.get('y_axis_label', 'Valores'),
                'bar_width': float(request.POST.get('bar_width', 0.8)),
                'show_labels': request.POST.get('show_labels') == 'on',
                'labels': labels,
                'values': values,
                'bar_colors': bar_colors,
                'top_texts': top_texts,
            })
            
        else:
            # Configuración para citas (quote)
            config.update({
                'author': request.POST.get('author'),
            })
        
        # Duración opcional - siempre intentar parsearla si existe
        duration = request.POST.get('duration')
        if duration:
            try:
                config['duration'] = float(duration)
            except (ValueError, TypeError):
                # Si no se puede parsear, dejar que la animación calcule automáticamente
                pass
        
        # Tiempo de visualización opcional (segundos que permanece en pantalla) - solo para quotes
        if animation_type == 'quote':
            display_time = request.POST.get('display_time')
            if display_time:
                try:
                    config['display_time'] = float(display_time)
                except (ValueError, TypeError):
                    pass
        
        return config


class VideoDeleteView(BreadcrumbMixin, DeleteView):
    """Eliminar video"""
    model = Video
    template_name = 'videos/delete.html'
    context_object_name = 'video'
    
    def get_object(self, queryset=None):
        """Buscar video por UUID"""
        if queryset is None:
            queryset = self.get_queryset()
        video_uuid = self.kwargs.get('video_uuid')
        return get_object_or_404(queryset, uuid=video_uuid)
    
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
            return reverse('core:project_detail', kwargs={'project_uuid': self.object.project.uuid})
        return reverse('core:dashboard')
    
    def get_breadcrumbs(self):
        breadcrumbs = []
        if self.object.project:
            breadcrumbs.append({
                'label': self.object.project.name, 
                'url': reverse('core:project_detail', args=[self.object.project.uuid])
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
        """Override para eliminar archivo de GCS y notificaciones relacionadas"""
        self.object = self.get_object()
        success_url = self.get_success_url()
        video_uuid = str(self.object.uuid)
        video_title = self.object.title
        
        # Eliminar notificaciones relacionadas con este video
        try:
            from .models import Notification
            Notification.objects.filter(
                metadata__item_uuid=video_uuid,
                metadata__item_type='video'
            ).delete()
        except Exception as e:
            logger.error(f"Error al eliminar notificaciones: {e}")
        
        # Eliminar de GCS si existe
        if self.object.gcs_path:
            try:
                from .storage.gcs import gcs_storage
                gcs_storage.delete_file(self.object.gcs_path)
            except Exception as e:
                logger.error(f"Error al eliminar archivo: {e}")
        
        self.object.delete()
        
        messages.success(request, f'Video "{video_title}" eliminado')
        return redirect(success_url)


class PublicVideoDetailView(View):
    """Vista pública para compartir videos"""
    template_name = 'videos/public_detail.html'

    def get(self, request, video_uuid):
        # Obtener video sin verificar permisos de usuario (acceso público por UUID)
        video = get_object_or_404(Video, uuid=video_uuid)

        # Verificar que el video esté completado
        if video.status != 'completed' or not video.gcs_path:
            raise Http404("El video no está disponible o sigue procesando")

        # Generar URL firmada
        video_service = VideoService()
        try:
            video_data = video_service.get_video_with_signed_urls(video)
            signed_url = video_data.get('signed_url')
        except Exception as e:
            logger.error(f"Error generando URL firmada para video público {video_uuid}: {e}")
            signed_url = None

        context = {
            'video': video,
            'signed_url': signed_url,
            'hide_header': True,  # Para ocultar navegación en layouts que lo soporten
        }

        return render(request, self.template_name, context)


class PublicImageDetailView(View):
    """Vista pública para compartir imágenes"""
    template_name = 'images/public_detail.html'

    def get(self, request, image_uuid):
        # Obtener imagen sin verificar permisos de usuario (acceso público por UUID)
        image = get_object_or_404(Image, uuid=image_uuid)

        # Verificar que la imagen esté completada
        if image.status != 'completed' or not image.gcs_path:
            raise Http404("La imagen no está disponible o sigue procesando")

        # Generar URL firmada
        image_service = ImageService()
        try:
            image_data = image_service.get_image_with_signed_urls(image)
            signed_url = image_data.get('signed_url')
        except Exception as e:
            logger.error(f"Error generando URL firmada para imagen pública {image_uuid}: {e}")
            signed_url = None

        context = {
            'image': image,
            'signed_url': signed_url,
            'hide_header': True,
        }

        return render(request, self.template_name, context)


class PublicAudioDetailView(View):
    """Vista pública para compartir audios"""
    template_name = 'audios/public_detail.html'

    def get(self, request, audio_uuid):
        # Obtener audio sin verificar permisos de usuario (acceso público por UUID)
        audio = get_object_or_404(Audio, uuid=audio_uuid)

        # Verificar que el audio esté completado
        if audio.status != 'completed' or not audio.gcs_path:
            raise Http404("El audio no está disponible o sigue procesando")

        # Generar URL firmada
        audio_service = AudioService()
        try:
            audio_data = audio_service.get_audio_with_signed_url(audio)
            signed_url = audio_data.get('signed_url')
        except Exception as e:
            logger.error(f"Error generando URL firmada para audio público {audio_uuid}: {e}")
            signed_url = None

        context = {
            'audio': audio,
            'signed_url': signed_url,
            'hide_header': True,
        }

        return render(request, self.template_name, context)


# ====================
# VIDEO ACTIONS
# ====================

class VideoGenerateView(ServiceMixin, View):
    """Generar video usando API externa"""
    
    def post(self, request, video_uuid):
        video = get_object_or_404(Video, uuid=video_uuid)
        video_service = self.get_video_service()
        
        try:
            task = video_service.generate_video_async(video)
            messages.success(
                request, 
                'Video encolado para generación. El proceso puede tardar varios minutos.'
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
        
        return redirect('core:video_detail', video_uuid=video.uuid)


class VideoRecreateView(ServiceMixin, View):
    """Recrear un video con los mismos parámetros"""
    
    def post(self, request, video_uuid):
        from django.db.models import Q
        
        original_video = get_object_or_404(Video, uuid=video_uuid)
        video_service = self.get_video_service()
        
        # Verificar permisos - validación robusta
        if not request.user.is_authenticated:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied('Debes estar autenticado para recrear videos')
        
        if original_video.project:
            # Si tiene proyecto, verificar acceso al proyecto
            if not ProjectService.user_has_access(original_video.project, request.user):
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied('No tienes acceso a este video')
        else:
            # Si no tiene proyecto, solo el creador puede recrearlo
            if not original_video.created_by or original_video.created_by != request.user:
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied('No tienes acceso a este video')
        
        try:
            # Calcular número de versión basado en UUID del item original
            # Determinar el UUID del item original (puede ser el mismo si es el primero)
            original_item_uuid = original_video.config.get('original_item_uuid')
            if not original_item_uuid:
                # Si no tiene original_item_uuid, este es el item original
                original_item_uuid = str(original_video.uuid)
            
            # Contar todos los items que pertenecen a la misma "familia" de versiones
            # (todos los que tienen el mismo original_item_uuid, o el original mismo)
            version_filter = (
                Q(config__original_item_uuid=original_item_uuid) |
                Q(uuid=original_item_uuid)
            )
            if original_video.project:
                version_filter &= Q(project=original_video.project)
            else:
                version_filter &= Q(project__isnull=True, created_by=request.user)
            
            # Contar items en la familia de versiones
            version_count = Video.objects.filter(version_filter).count()
            
            # Calcular siguiente versión
            next_version = version_count + 1
            
            # Extraer título base (sin sufijo de versión si existe)
            base_title = original_video.title
            import re
            match = re.match(r'^(.+?)(\s+- v\d+)?$', base_title)
            if match:
                base_title = match.group(1)
            
            new_title = f"{base_title} - v{next_version}"
            
            # Crear nuevo video copiando la configuración
            new_config = original_video.config.copy() if original_video.config else {}
            # Marcar el UUID del item original para rastrear versiones
            new_config['original_item_uuid'] = original_item_uuid
            
            new_video = video_service.create_video(
                created_by=request.user,
                project=original_video.project,
                title=new_title,
                video_type=original_video.type,
                script=original_video.script,
                config=new_config
            )
            
            # Generar el video automáticamente
            task = video_service.generate_video_async(new_video)
            
            messages.success(
                request,
                f'Video "{new_title}" creado y encolado para generación.'
            )
            
            # Redirigir al nuevo video
            if new_video.project:
                return redirect('core:project_video_detail', project_uuid=new_video.project.uuid, video_uuid=new_video.uuid)
            else:
                return redirect('core:video_detail', video_uuid=new_video.uuid)
                
        except InsufficientCreditsException as e:
            messages.error(request, str(e))
            return redirect('core:video_detail', video_uuid=original_video.uuid)
        except RateLimitExceededException as e:
            messages.error(request, str(e))
            return redirect('core:video_detail', video_uuid=original_video.uuid)
        except (ValidationException, ServiceException) as e:
            messages.error(request, str(e))
            return redirect('core:video_detail', video_uuid=original_video.uuid)
        except Exception as e:
            logger.error(f'Error al recrear video: {e}', exc_info=True)
            messages.error(request, f'Error inesperado: {str(e)}')
            return redirect('core:video_detail', video_uuid=original_video.uuid)


class VideoStatusView(ServiceMixin, View):
    """API endpoint para consultar estado del video"""
    
    def get(self, request, video_uuid):
        video = get_object_or_404(Video, uuid=video_uuid)
        
        # Si ya está en estado final, verificar si se cobraron créditos
        if video.status in ['completed', 'error']:
            # Verificar y cobrar créditos si no se han cobrado aún
            if video.status == 'completed' and video.created_by:
                try:
                    from core.services.credits import CreditService
                    # Verificar si ya se cobraron créditos
                    if not video.metadata.get('credits_charged'):
                        logger.info(f"Video {video.uuid} completado pero sin créditos cobrados. Cobrando ahora...")
                        CreditService.deduct_credits_for_video(video.created_by, video)
                        video.refresh_from_db()  # Refrescar después del cobro
                except Exception as e:
                    logger.error(f"Error al verificar/cobrar créditos para video {video.uuid}: {e}")
            
            response_data = {
                'status': video.status,
                'message': 'Video ya procesado',
                'updated_at': video.updated_at.isoformat()
            }
            
            # Si está completado, incluir URL del video
            if video.status == 'completed':
                try:
                    video_service = self.get_video_service()
                    video_data = video_service.get_video_with_signed_urls(video)
                    if video_data.get('signed_url'):
                        response_data['video_url'] = video_data['signed_url']
                    elif video_data.get('all_videos') and len(video_data['all_videos']) > 0:
                        # Si hay múltiples videos, usar el primero
                        response_data['video_url'] = video_data['all_videos'][0].get('signed_url')
                except Exception as e:
                    logger.error(f"Error al obtener URL del video {video.uuid}: {e}")
            
            return JsonResponse(response_data)
        
        if not video.external_id:
            return JsonResponse({
                'error': 'Video no tiene external_id',
                'status': video.status
            }, status=400)
        
        # Consultar estado usando servicio
        video_service = self.get_video_service()
        try:
            status_data = video_service.check_video_status(video)
            # Refrescar video desde BD después de check_video_status
            video.refresh_from_db()
            
            # Si ahora está completado, verificar créditos
            if video.status == 'completed' and video.created_by:
                try:
                    from core.services.credits import CreditService
                    if not video.metadata.get('credits_charged'):
                        logger.info(f"Video {video.uuid} completado después de check_status. Cobrando créditos...")
                        CreditService.deduct_credits_for_video(video.created_by, video)
                        video.refresh_from_db()
                except Exception as e:
                    logger.error(f"Error al cobrar créditos para video {video.uuid}: {e}")
            
            response_data = {
                'status': video.status,
                'external_status': status_data,
                'updated_at': video.updated_at.isoformat()
            }
            
            # Si está completado, incluir URL del video
            if video.status == 'completed':
                try:
                    video_service = self.get_video_service()
                    video_data = video_service.get_video_with_signed_urls(video)
                    if video_data.get('signed_url'):
                        response_data['video_url'] = video_data['signed_url']
                    elif video_data.get('all_videos') and len(video_data['all_videos']) > 0:
                        # Si hay múltiples videos, usar el primero
                        response_data['video_url'] = video_data['all_videos'][0].get('signed_url')
                except Exception as e:
                    logger.error(f"Error al obtener URL del video {video.uuid}: {e}")
            
            return JsonResponse(response_data)
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


class ModelConfigAPIView(View):
    """API endpoint para obtener configuración de modelos"""
    
    def get(self, request):
        """
        Retorna configuración de modelos
        
        Query params:
            type: Filtrar por tipo ('video', 'image', 'audio')
            service: Filtrar por servicio ('gemini_veo', 'openai', etc.)
            grouped: Si es 'true', agrupa por servicio
        """
        from .utils.model_capabilities import (
            get_models_by_type,
            get_models_grouped_by_service,
            get_models_by_service,
        )
        
        item_type = request.GET.get('type')
        service = request.GET.get('service')
        grouped = request.GET.get('grouped', 'false').lower() == 'true'
        
        try:
            if grouped:
                # Agrupar por servicio
                models_data = get_models_grouped_by_service(item_type)
                return JsonResponse({
                    'models': models_data,
                    'grouped': True
                })
            elif service:
                # Filtrar por servicio
                models = get_models_by_service(service)
                if item_type:
                    models = [m for m in models if m.get('type') == item_type]
                return JsonResponse({
                    'models': models,
                    'grouped': False
                })
            elif item_type:
                # Filtrar por tipo
                models = get_models_by_type(item_type)
                return JsonResponse({
                    'models': models,
                    'grouped': False
                })
            else:
                # Todos los modelos
                from .ai_services.model_config import MODEL_CAPABILITIES
                all_models = [
                    {**model, 'id': model_id}
                    for model_id, model in MODEL_CAPABILITIES.items()
                ]
                return JsonResponse({
                    'models': all_models,
                    'grouped': False
                })
        except Exception as e:
            logger.error(f"Error al obtener configuración de modelos: {e}")
            return JsonResponse({
                'error': 'Error al cargar configuración de modelos',
                'error_detail': str(e),
                'models': []
            }, status=500)


class ModelCapabilitiesAPIView(View):
    """API endpoint para obtener capacidades de un modelo específico"""
    
    def get(self, request, model_id):
        """
        Retorna capacidades de un modelo específico
        
        Args:
            model_id: ID del modelo (ej: 'veo-3.1-generate-preview', 'sora-2')
        """
        from .ai_services.model_config import get_model_capabilities
        
        try:
            capabilities = get_model_capabilities(model_id)
            
            if not capabilities:
                return JsonResponse({
                    'error': f'Modelo {model_id} no encontrado'
                }, status=404)
            
            return JsonResponse({
                'model_id': model_id,
                'capabilities': capabilities
            })
        except Exception as e:
            logger.error(f"Error al obtener capacidades del modelo {model_id}: {e}")
            return JsonResponse({
                'error': 'Error al cargar capacidades del modelo',
                'error_detail': str(e)
            }, status=500)


class VideoModelsAPIView(View):
    """API endpoint para obtener modelos de video que soporten image-to-video"""
    
    def get(self, request):
        """
        Retorna modelos de video que soporten image-to-video
        
        Query params:
            image_to_video: Si es 'true', solo retorna modelos que soporten image-to-video
        """
        from .ai_services.model_config import get_models_by_type
        
        try:
            image_to_video_only = request.GET.get('image_to_video', 'false').lower() == 'true'
            
            # Obtener todos los modelos de video (retorna lista de diccionarios)
            video_models = get_models_by_type('video')
            
            # Filtrar por image_to_video si se solicita
            if image_to_video_only:
                filtered_models = []
                excluded_services = ['heygen']  # Excluir servicios que requieren flujo especial
                
                for model_info in video_models:
                    model_id = model_info.get('id', '')
                    service = model_info.get('service', '')
                    supports = model_info.get('supports', {})
                    
                    # Excluir modelos HeyGen (requieren avatar, no imagen genérica)
                    if service in excluded_services or 'heygen' in model_id.lower():
                        continue
                    
                    # Solo incluir modelos que realmente soporten image-to-video genérico
                    if supports.get('image_to_video') or supports.get('references', {}).get('start_image'):
                        filtered_models.append(model_info)
                
                video_models = filtered_models
            
            # Formatear respuesta (ya viene con 'id' incluido desde get_models_by_type)
            models_list = []
            for model_info in video_models:
                models_list.append({
                    'id': model_info.get('id', ''),
                    'name': model_info.get('name', model_info.get('id', '')),
                    'description': model_info.get('description', ''),
                    'service': model_info.get('service', ''),
                    'logo': model_info.get('logo', ''),
                    'supports': model_info.get('supports', {}),
                })
            
            return JsonResponse({
                'models': models_list,
                'count': len(models_list)
            })
        except Exception as e:
            logger.error(f"Error al obtener modelos de video: {e}", exc_info=True)
            return JsonResponse({
                'error': 'Error al cargar modelos de video',
                'error_detail': str(e),
                'models': []
            }, status=500)


class EstimateCostAPIView(LoginRequiredMixin, View):
    """API endpoint para calcular costo estimado de generación"""
    
    def post(self, request):
        """
        Calcula costo estimado basado en modelo y configuración
        
        Body JSON:
        {
            "model_id": "veo-3.1-generate-preview",
            "item_type": "video",  // "video", "image", "audio"
            "config": {
                "duration": 8,
                "generate_audio": true,
                "mode": "std",
                ...
            },
            "text": "..."  // Para audio (caracteres)
        }
        """
        from .services.credits import CreditService
        from .ai_services.model_config import get_model_capabilities, VIDEO_TYPE_TO_MODEL_ID
        from decimal import Decimal
        import json
        
        try:
            data = json.loads(request.body)
            model_id = data.get('model_id')
            item_type = data.get('item_type', 'video')
            config = data.get('config', {})
            text = data.get('text', '')
            
            if not model_id:
                return JsonResponse({
                    'error': 'model_id es requerido'
                }, status=400)
            
            # Obtener capacidades del modelo
            model_capabilities = get_model_capabilities(model_id)
            if not model_capabilities:
                return JsonResponse({
                    'error': f'Modelo {model_id} no encontrado'
                }, status=404)
            
            # Calcular costo según tipo
            if item_type == 'video':
                duration = config.get('duration') or 8
                # Usar el método mejorado que acepta model_id directamente
                cost = CreditService.estimate_video_cost(
                    video_type=None, 
                    duration=duration, 
                    config=config, 
                    model_id=model_id
                )
                    
            elif item_type == 'image':
                model_id = data.get('model_id')
                image_type = data.get('image_type', 'text_to_image')
                quality = data.get('config', {}).get('quality', 'medium')
                cost = CreditService.estimate_image_cost(
                    model_id=model_id,
                    image_type=image_type,
                    quality=quality
                )
                
            elif item_type == 'audio':
                cost = CreditService.estimate_audio_cost(text)
                
            else:
                return JsonResponse({
                    'error': f'Tipo de item no válido: {item_type}'
                }, status=400)
            
            return JsonResponse({
                'model_id': model_id,
                'item_type': item_type,
                'estimated_cost': float(cost),
                'estimated_cost_formatted': f'{cost:.2f}'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'JSON inválido'
            }, status=400)
        except Exception as e:
            logger.error(f"Error al calcular costo estimado: {e}")
            return JsonResponse({
                'error': 'Error al calcular costo',
                'error_detail': str(e)
            }, status=500)


class DynamicFormFieldsView(LoginRequiredMixin, View):
    """Vista para renderizar campos dinámicos del formulario según el modelo seleccionado"""
    
    def get(self, request):
        model_id = request.GET.get('model_id')
        if not model_id:
            return HttpResponse('')
        
        from core.forms.dynamic import get_model_specific_fields
        from core.ai_services.model_config import get_model_capabilities, MODEL_CAPABILITIES
        from core.services.credits import CreditService
        from decimal import Decimal
        
        # Obtener capacidades del modelo
        capabilities = get_model_capabilities(model_id)
        if not capabilities:
            return HttpResponse('<p class="text-red-500">Modelo no encontrado</p>')
        
        supports = capabilities.get('supports', {})
        service = capabilities.get('service', '')

        # Tipo de animación para modelos Manim (quote, bar_chart, etc.)
        manim_animation_type = None
        if service == 'manim':
            manim_animation_type = request.GET.get('manim_animation_type') or 'quote'
            
            # Ajustar supports según el tipo de animación
            if manim_animation_type == 'modern_bar_chart':
                supports['bar_width'] = True
        
        # Generar opciones de duración si solo hay min/max sin options
        if supports.get('duration') and not supports['duration'].get('options') and not supports['duration'].get('fixed'):
            if supports['duration'].get('min') and supports['duration'].get('max'):
                min_val = supports['duration']['min']
                max_val = supports['duration']['max']
                supports['duration']['options'] = list(range(min_val, max_val + 1))
        
        # Verificar si hay referencias habilitadas (solo para mostrar los campos)
        # NOTA: No forzamos duración aquí porque solo se requiere 8s cuando realmente se sube una imagen
        has_references = False
        if supports.get('references'):
            refs = supports['references']
            has_references = any([
                refs.get('start_image'),
                refs.get('end_image'),
                refs.get('style_image'),
                refs.get('asset_image')
            ])
        
        # Obtener campos específicos del modelo (avatares, voces, etc.)
        model_specific = get_model_specific_fields(model_id, service)
        logger.info(f"DynamicFormFieldsView: Modelo {model_id}, campos específicos: {len(model_specific.get('fields', []))}")
        
        # Calcular costo estimado
        estimated_cost = Decimal('0')
        estimated_cost_formatted = '0.00'
        try:
            if capabilities.get('type') == 'video':
                # Obtener duración por defecto
                duration = 8
                if supports.get('duration'):
                    dur_config = supports['duration']
                    if dur_config.get('fixed'):
                        duration = dur_config['fixed']
                    elif dur_config.get('options'):
                        duration = dur_config['options'][0]
                    elif dur_config.get('min'):
                        duration = dur_config['min']
                
                video_type = None
                from core.ai_services.model_config import VIDEO_TYPE_TO_MODEL_ID
                for vtype, mid in VIDEO_TYPE_TO_MODEL_ID.items():
                    if mid == model_id:
                        video_type = vtype
                        break
                
                if not video_type:
                    if 'veo' in model_id:
                        video_type = 'gemini_veo'
                    elif 'sora' in model_id:
                        video_type = 'sora'
                    elif 'heygen' in model_id:
                        video_type = 'heygen_avatar_v2' if 'v2' in model_id else 'heygen_avatar_iv'
                    elif 'kling' in model_id:
                        video_type = model_id.replace('-', '_')
                    elif 'higgsfield' in model_id or 'seedance' in model_id:
                        if 'dop/standard' in model_id:
                            video_type = 'higgsfield_dop_standard'
                        elif 'dop/preview' in model_id:
                            video_type = 'higgsfield_dop_preview'
                        elif 'seedance' in model_id:
                            video_type = 'higgsfield_seedance_v1_pro'
                        elif 'kling-video' in model_id:
                            video_type = 'higgsfield_kling_v2_1_pro'
                    elif 'vuela' in model_id:
                        video_type = 'vuela_ai'
                
                if video_type:
                    config = {}
                    estimated_cost = CreditService.estimate_video_cost(
                        video_type=video_type,
                        duration=duration,
                        config=config,
                        model_id=model_id
                    )
                    estimated_cost_formatted = f'{int(estimated_cost)}'
        except Exception as e:
            logger.error(f"Error calculando costo estimado: {e}")
        
        # Debug: Log de referencias (para verificar en consola del servidor)
        references = supports.get('references', {})
        logger.info(f"[DynamicFormFields] Modelo: {model_id}")
        logger.info(f"[DynamicFormFields] Referencias disponibles: {references}")
        logger.info(f"[DynamicFormFields] style_image: {references.get('style_image')} (tipo: {type(references.get('style_image')).__name__})")
        logger.info(f"[DynamicFormFields] asset_image: {references.get('asset_image')} (tipo: {type(references.get('asset_image')).__name__})")
        
        # Obtener template "General" por defecto según el servicio
        default_template = None
        default_template_id = None
        recommended_service_for_template = service
        
        if capabilities.get('type') == 'video':
            from core.utils.prompt_templates import get_default_template
            template_type = 'video'
            # Mapear servicio del modelo al servicio esperado por templates
            service_mapping = {
                'openai': 'sora',  # Sora usa 'openai' en model_config pero 'sora' en templates
                'gemini_veo': 'gemini_veo',
                'higgsfield': 'higgsfield',
                'kling': 'kling',
            }
            recommended_service_for_template = service_mapping.get(service, service)
            default_template = get_default_template(template_type, recommended_service_for_template)
            if default_template:
                default_template_id = str(default_template.uuid)
        
        # Obtener resoluciones disponibles para modelos de imagen
        image_resolutions = {}
        if capabilities.get('type') == 'image':
            from core.ai_services.gemini_image import GeminiImageClient
            if model_id in GeminiImageClient.MODEL_CONFIGS:
                model_config = GeminiImageClient.MODEL_CONFIGS[model_id]
                if 'resolutions' in model_config:
                    image_resolutions = model_config['resolutions']
        
        # Renderizar template con los campos
        context = {
            'model_id': model_id,
            'capabilities': capabilities,
            'supports': supports,
            'manim_animation_type': manim_animation_type,
            'model_specific_fields': model_specific.get('fields', []),
            'model_specific_data': model_specific.get('data', {}),
            'estimated_cost': float(estimated_cost),
            'estimated_cost_formatted': estimated_cost_formatted,
            'has_references': has_references,
            'recommended_service': recommended_service_for_template,  # Para el selector de templates
            'default_template_id': default_template_id,  # Template "General" por defecto
            'image_resolutions': image_resolutions,  # Resoluciones disponibles para modelos de imagen
        }
        
        logger.debug(f"DynamicFormFieldsView: Contexto para {model_id}: supports.references = {supports.get('references')}")
        
        # Renderizar template según el tipo
        item_type = capabilities.get('type', 'video')
        if item_type == 'image':
            return render(request, 'images/_dynamic_fields.html', context)
        else:
            return render(request, 'videos/_dynamic_fields.html', context)


class LibraryItemsAPIView(ServiceMixin, View):
    """API endpoint para obtener items de la biblioteca filtrados por tipo y proyecto"""
    
    DEFAULT_LIMIT = 20
    MAX_LIMIT = 100
    
    def get(self, request):
        """
        Retorna items de la biblioteca con paginación
        
        Query params:
            type: Filtrar por tipo ('video', 'image', 'audio')
            project_id: Filtrar por proyecto (opcional)
            limit: Número de items a retornar (default: 20, max: 100)
            offset: Número de items a saltar (default: 0)
            include_urls: Si incluir signed URLs (default: true) - false para carga rápida
        """
        from django.db.models import Q
        
        item_type = request.GET.get('type', 'all')
        # Aceptar tanto project_id como project_uuid para compatibilidad
        project_id = request.GET.get('project_id')
        project_uuid = request.GET.get('project_uuid')
        user = request.user
        
        # Incluir URLs (para carga rápida, puede ser false)
        include_urls = request.GET.get('include_urls', 'true').lower() != 'false'
        
        # Filtro de dashboard (personal/shared)
        dashboard_filter = request.GET.get('filter')

        # Paginación
        try:
            limit = min(int(request.GET.get('limit', self.DEFAULT_LIMIT)), self.MAX_LIMIT)
        except (ValueError, TypeError):
            limit = self.DEFAULT_LIMIT
        
        try:
            offset = max(int(request.GET.get('offset', 0)), 0)
        except (ValueError, TypeError):
            offset = 0
        
        # Obtener proyectos del usuario
        user_projects = ProjectService.get_user_projects(user)
        user_project_ids = [p.id for p in user_projects]
        
        # Construir filtro base
        if dashboard_filter == 'shared':
            # Items en proyectos donde soy miembro pero no dueño
            shared_project_ids = ProjectMember.objects.filter(user=user).values_list('project_id', flat=True)
            base_filter = Q(project_id__in=shared_project_ids) & ~Q(project__owner=user)
        elif dashboard_filter == 'personal':
            # Items creados por mí (en cualquier proyecto o sin proyecto)
            base_filter = Q(created_by=user)
        else:
            # Por defecto: todo lo que tengo acceso
            base_filter = Q(project_id__in=user_project_ids) | Q(project__isnull=True, created_by=user)
        
        # Si hay project_uuid o project_id específico, filtrar por ese proyecto (sobrescribe dashboard_filter)
        project = None
        if project_uuid:
            try:
                project = get_object_or_404(Project, uuid=project_uuid)
                if not ProjectService.user_has_access(project, user):
                    return JsonResponse({'error': 'No tienes acceso a este proyecto'}, status=403)
                base_filter = Q(project_id=project.id)
            except (ValueError, Project.DoesNotExist):
                return JsonResponse({'error': 'Proyecto no encontrado'}, status=404)
        elif project_id:
            try:
                project_id_int = int(project_id)
                if project_id_int in user_project_ids:
                    base_filter = Q(project_id=project_id_int)
                else:
                    # Verificar permisos del proyecto
                    project = get_object_or_404(Project, pk=project_id_int)
                    if not ProjectService.user_has_access(project, user):
                        return JsonResponse({'error': 'No tienes acceso a este proyecto'}, status=403)
                    base_filter = Q(project_id=project_id_int)
            except (ValueError, Project.DoesNotExist):
                return JsonResponse({'error': 'Proyecto no encontrado'}, status=404)
        
        items_data = []
        total_count = 0
        
        try:
            if item_type == 'video':
                queryset = Video.objects.filter(base_filter).select_related('project').order_by('-created_at')
                total_count = queryset.count()
                videos = queryset[offset:offset + limit]
                video_service = self.get_video_service()
                for video in videos:
                    # Usar URL del proyecto si hay proyecto específico, sino URL genérica
                    if project:
                        detail_url = reverse('core:project_video_detail', args=[project.uuid, video.uuid])
                    else:
                        detail_url = reverse('core:video_detail', args=[video.uuid])
                    
                    item_data = {
                        'id': str(video.uuid),
                        'type': 'video',
                        'title': video.title,
                        'status': video.status,
                        'status_display': video.get_status_display(),
                        'created_at': video.created_at.isoformat(),
                        'project': video.project.name if video.project else None,
                        'video_type': video.get_type_display(),
                        'script': video.script[:100] if video.script else '',
                        'signed_url': None,
                        'has_media': video.status == 'completed' and bool(video.gcs_path),
                        'detail_url': detail_url,
                        'delete_url': reverse('core:video_delete', args=[video.uuid]),
                    }
                    # Solo generar signed URLs si se pide explícitamente
                    if include_urls and video.status == 'completed' and video.gcs_path:
                        try:
                            video_data = video_service.get_video_with_signed_urls(video)
                            item_data['signed_url'] = video_data.get('signed_url')
                        except Exception:
                            pass
                    items_data.append(item_data)
                    
            elif item_type == 'image':
                queryset = Image.objects.filter(base_filter).select_related('project').order_by('-created_at')
                total_count = queryset.count()
                images = queryset[offset:offset + limit]
                image_service = self.get_image_service()
                for image in images:
                    # Usar URL del proyecto si hay proyecto específico, sino URL genérica
                    if project:
                        detail_url = reverse('core:project_image_detail', args=[project.uuid, image.uuid])
                    else:
                        detail_url = reverse('core:image_detail', args=[image.uuid])
                    
                    item_data = {
                        'id': str(image.uuid),
                        'type': 'image',
                        'title': image.title,
                        'status': image.status,
                        'status_display': image.get_status_display(),
                        'created_at': image.created_at.isoformat(),
                        'project': image.project.name if image.project else None,
                        'image_type': image.get_type_display(),
                        'prompt': image.prompt[:100] if image.prompt else '',
                        'signed_url': None,
                        'has_media': image.status == 'completed' and bool(image.gcs_path),
                        'detail_url': detail_url,
                        'delete_url': reverse('core:image_delete', args=[image.uuid]),
                    }
                    # Solo generar signed URLs si se pide explícitamente
                    if include_urls and image.status == 'completed' and image.gcs_path:
                        try:
                            image_data = image_service.get_image_with_signed_urls(image)
                            item_data['signed_url'] = image_data.get('signed_url')
                        except Exception:
                            pass
                    items_data.append(item_data)
                    
            elif item_type == 'audio':
                queryset = Audio.objects.filter(base_filter).select_related('project').order_by('-created_at')
                total_count = queryset.count()
                audios = queryset[offset:offset + limit]
                audio_service = self.get_audio_service()
                for audio in audios:
                    # Obtener info del modelo usando el model_id del audio
                    model_id = audio.model_id or 'elevenlabs'  # Default a elevenlabs si no hay model_id
                    model_info = get_model_info_for_item('audio', model_key=model_id)
                    
                    # Usar URL del proyecto si hay proyecto específico, sino URL genérica
                    if project:
                        detail_url = reverse('core:project_audio_detail', args=[project.uuid, audio.uuid])
                    else:
                        detail_url = reverse('core:audio_detail', args=[audio.uuid])
                    
                    item_data = {
                        'id': str(audio.uuid),
                        'type': 'audio',
                        'title': audio.title,
                        'status': audio.status,
                        'status_display': audio.get_status_display(),
                        'created_at': audio.created_at.isoformat(),
                        'project': audio.project.name if audio.project else None,
                        'signed_url': None,
                        'has_media': audio.status == 'completed' and bool(audio.gcs_path),
                        'detail_url': detail_url,
                        'delete_url': reverse('core:audio_delete', args=[audio.uuid]),
                        'model': model_info,  # Información del modelo (nombre, logo, servicio)
                        'audio_type': audio.type,  # 'tts' o 'music'
                        'audio_background': audio.background_gradient, # Nuevo campo para miniatura dinámica
                    }
                    # Solo generar signed URLs si se pide explícitamente
                    if include_urls and audio.status == 'completed' and audio.gcs_path:
                        try:
                            audio_data = audio_service.get_audio_with_signed_url(audio)
                            item_data['signed_url'] = audio_data.get('signed_url')
                        except Exception:
                            pass
                    items_data.append(item_data)

            elif item_type == 'all':
                # Fetch items from all models
                # We fetch limit+offset from each to ensure correct global sort
                fetch_limit = offset + limit

                videos = Video.objects.filter(base_filter).select_related('project').order_by('-created_at')[:fetch_limit]
                images = Image.objects.filter(base_filter).select_related('project').order_by('-created_at')[:fetch_limit]
                audios = Audio.objects.filter(base_filter).select_related('project').order_by('-created_at')[:fetch_limit]
                scripts = Script.objects.filter(base_filter).select_related('project').order_by('-created_at')[:fetch_limit]

                # Calculate total count
                total_count = (
                    Video.objects.filter(base_filter).count() +
                    Image.objects.filter(base_filter).count() +
                    Audio.objects.filter(base_filter).count() +
                    Script.objects.filter(base_filter).count()
                )

                # Combine and sort
                all_objs = sorted(
                    list(videos) + list(images) + list(audios) + list(scripts),
                    key=lambda x: x.created_at,
                    reverse=True
                )

                # Slice page
                page_objs = all_objs[offset:offset + limit]

                # Services
                video_service = self.get_video_service()
                image_service = self.get_image_service()
                audio_service = self.get_audio_service()

                for item in page_objs:
                    # Determine type and format
                    if isinstance(item, Video):
                        detail_url = reverse('core:project_video_detail', args=[item.project.uuid, item.uuid]) if item.project else reverse('core:video_detail', args=[item.uuid])

                        item_data = {
                            'id': str(item.uuid),
                            'type': 'video',
                            'title': item.title,
                            'status': item.status,
                            'status_display': item.get_status_display(),
                            'created_at': item.created_at.isoformat(),
                            'project': item.project.name if item.project else None,
                            'video_type': item.get_type_display(),
                            'script': item.script[:100] if item.script else '',
                            'signed_url': None,
                            'has_media': item.status == 'completed' and bool(item.gcs_path),
                            'detail_url': detail_url,
                            'delete_url': reverse('core:video_delete', args=[item.uuid]),
                        }
                        if include_urls and item.status == 'completed' and item.gcs_path:
                            try:
                                video_data = video_service.get_video_with_signed_urls(item)
                                item_data['signed_url'] = video_data.get('signed_url')
                            except Exception:
                                pass
                        items_data.append(item_data)

                    elif isinstance(item, Image):
                        detail_url = reverse('core:project_image_detail', args=[item.project.uuid, item.uuid]) if item.project else reverse('core:image_detail', args=[item.uuid])

                        item_data = {
                            'id': str(item.uuid),
                            'type': 'image',
                            'title': item.title,
                            'status': item.status,
                            'status_display': item.get_status_display(),
                            'created_at': item.created_at.isoformat(),
                            'project': item.project.name if item.project else None,
                            'image_type': item.get_type_display(),
                            'prompt': item.prompt[:100] if item.prompt else '',
                            'signed_url': None,
                            'has_media': item.status == 'completed' and bool(item.gcs_path),
                            'detail_url': detail_url,
                            'delete_url': reverse('core:image_delete', args=[item.uuid]),
                        }
                        if include_urls and item.status == 'completed' and item.gcs_path:
                            try:
                                image_data = image_service.get_image_with_signed_urls(item)
                                item_data['signed_url'] = image_data.get('signed_url')
                            except Exception:
                                pass
                        items_data.append(item_data)

                    elif isinstance(item, Audio):
                        detail_url = reverse('core:project_audio_detail', args=[item.project.uuid, item.uuid]) if item.project else reverse('core:audio_detail', args=[item.uuid])
                        model_id = item.model_id or 'elevenlabs'
                        model_info = get_model_info_for_item('audio', model_key=model_id)

                        item_data = {
                            'id': str(item.uuid),
                            'type': 'audio',
                            'title': item.title,
                            'status': item.status,
                            'status_display': item.get_status_display(),
                            'created_at': item.created_at.isoformat(),
                            'project': item.project.name if item.project else None,
                            'signed_url': None,
                            'has_media': item.status == 'completed' and bool(item.gcs_path),
                            'detail_url': detail_url,
                            'delete_url': reverse('core:audio_delete', args=[item.uuid]),
                            'model': model_info,
                            'audio_type': item.type,
                            'audio_background': item.background_gradient,
                        }
                        if include_urls and item.status == 'completed' and item.gcs_path:
                            try:
                                audio_data = audio_service.get_audio_with_signed_url(item)
                                item_data['signed_url'] = audio_data.get('signed_url')
                            except Exception:
                                pass
                        items_data.append(item_data)

                    elif isinstance(item, Script):
                        # Script uses numeric ID
                        detail_url = reverse('core:script_detail', args=[item.id])

                        item_data = {
                            'id': item.id,
                            'type': 'script',
                            'title': item.title,
                            'status': item.status,
                            'status_display': item.get_status_display(),
                            'created_at': item.created_at.isoformat(),
                            'project': item.project.name if item.project else None,
                            'signed_url': None,
                            'detail_url': detail_url,
                            'delete_url': reverse('core:script_delete', args=[item.id]),
                        }
                        items_data.append(item_data)

            else:
                return JsonResponse({'error': 'Tipo no válido'}, status=400)
                
            has_more = (offset + len(items_data)) < total_count
            return JsonResponse({
                'items': items_data,
                'count': len(items_data),
                'total': total_count,
                'offset': offset,
                'limit': limit,
                'has_more': has_more,
                'type': item_type
            })
            
        except Exception as e:
            logger.error(f"Error al obtener items de biblioteca: {e}")
            return JsonResponse({
                'error': 'Error al cargar items',
                'error_detail': str(e),
                'items': []
            }, status=500)


class ItemDetailAPIView(ServiceMixin, View):
    """API endpoint para obtener detalles completos de un item (video, image, audio)"""
    
    def get(self, request, item_type, item_id):
        """
        Retorna detalles completos de un item
        
        Args:
            item_type: 'video', 'image', 'audio'
            item_id: UUID del item (str)
        """
        from django.db.models import Q
        import uuid as uuid_module
        
        user = request.user
        user_projects = ProjectService.get_user_projects(user)
        user_project_ids = [p.id for p in user_projects]
        
        # Parámetro opcional para filtrar por proyecto específico
        project_id = request.GET.get('project_id')
        if project_id:
            try:
                project_id = int(project_id)
            except (ValueError, TypeError):
                project_id = None
        
        # Validar y convertir item_id a UUID
        try:
            item_uuid = uuid_module.UUID(item_id)
        except (ValueError, TypeError):
            return JsonResponse({'error': 'ID de item inválido'}, status=400)
        
        try:
            if item_type == 'video':
                video = get_object_or_404(Video, uuid=item_uuid)
                
                # Verificar acceso - manejar caso donde created_by puede ser None
                has_project_access = video.project_id in user_project_ids if video.project_id else False
                has_direct_access = video.project is None and video.created_by_id and video.created_by_id == user.id
                
                if not (has_project_access or has_direct_access):
                    return JsonResponse({'error': 'No tienes acceso a este video'}, status=403)
                
                # Determinar el contexto del proyecto para navegación (ID para filtros, UUID para URLs)
                # Si viene project_id en la petición, usar ese; sino usar el del item
                nav_project_id = project_id or (video.project_id if video.project else None)
                nav_project_uuid = video.project.uuid if video.project else None
                
                # Filtro para navegación: solo items del mismo proyecto o sin proyecto
                if nav_project_id:
                    nav_filter = Q(project_id=nav_project_id)
                else:
                    nav_filter = Q(project__isnull=True, created_by=user)
                
                # Obtener signed URL de forma segura
                signed_url = None
                try:
                    video_service = self.get_video_service()
                    video_data = video_service.get_video_with_signed_urls(video)
                    signed_url = video_data.get('signed_url') if video_data else None
                except Exception:
                    pass
                
                # Obtener items previo y siguiente dentro del mismo contexto
                prev_item = None
                next_item = None
                try:
                    prev_item = Video.objects.filter(
                        nav_filter,
                        created_at__lt=video.created_at
                    ).order_by('-created_at').first()
                    
                    next_item = Video.objects.filter(
                        nav_filter,
                        created_at__gt=video.created_at
                    ).order_by('created_at').first()
                except Exception:
                    pass
                
                # Serializar config de forma segura
                config = video.config if isinstance(video.config, dict) else {}
                
                # Obtener info del modelo usando model_id del config si está disponible
                model_id = config.get('model_id') or config.get('veo_model')
                if model_id:
                    model_info = get_model_info_for_item('video', model_id)
                else:
                    model_info = get_model_info_for_item('video', video.type)
                
                # Obtener información del prompt template si existe
                prompt_template_info = None
                prompt_template_id = config.get('prompt_template_id')
                if prompt_template_id:
                    try:
                        from core.models import PromptTemplate
                        template = PromptTemplate.objects.filter(uuid=prompt_template_id, is_active=True).first()
                        if template:
                            preview_url = template.preview_url or ''
                            # Si es una URL de GCS, convertir a URL firmada
                            if preview_url and preview_url.startswith('gs://'):
                                try:
                                    from core.storage.gcs import gcs_storage
                                    preview_url = gcs_storage.get_signed_url(preview_url, expiration=3600)
                                except Exception as e:
                                    logger.warning(f'Error obteniendo URL firmada para preview: {e}')
                            
                            prompt_template_info = {
                                'uuid': str(template.uuid),
                                'name': template.name,
                                'description': template.description or '',
                                'preview_url': preview_url,
                            }
                    except Exception as e:
                        logger.warning(f'Error obteniendo prompt template {prompt_template_id}: {e}')
                
                # URL de detalle con contexto de proyecto si aplica
                if nav_project_uuid:
                    detail_url = reverse('core:project_video_detail', args=[nav_project_uuid, video.uuid])
                    prev_url = reverse('core:project_video_detail', args=[nav_project_uuid, prev_item.uuid]) if prev_item else None
                    next_url = reverse('core:project_video_detail', args=[nav_project_uuid, next_item.uuid]) if next_item else None
                else:
                    detail_url = reverse('core:video_detail', args=[video.uuid])
                    prev_url = reverse('core:video_detail', args=[prev_item.uuid]) if prev_item else None
                    next_url = reverse('core:video_detail', args=[next_item.uuid]) if next_item else None
                
                return JsonResponse({
                    'item': {
                        'id': str(video.uuid),
                        'type': 'video',
                        'title': video.title or 'Sin título',
                        'status': video.status,
                        'status_display': video.get_status_display(),
                        'created_at': video.created_at.isoformat() if video.created_at else None,
                        'completed_at': video.completed_at.isoformat() if video.completed_at else None,
                        'project': {
                            'id': video.project.id if video.project else None,
                            'uuid': str(video.project.uuid) if video.project else None,
                            'name': video.project.name if video.project else None,
                        },
                        'video_type': video.get_type_display() if video.type else None,
                        'video_type_key': video.type,
                        'script': video.script or '',
                        'prompt': video.script or '',  # Video usa script, no prompt
                        'config': config,
                        'error_message': video.error_message or '',
                        'signed_url': signed_url,
                        'detail_url': detail_url,
                        'delete_url': reverse('core:video_delete', args=[video.uuid]),
                        'generate_url': reverse('core:video_generate', args=[video.uuid]),
                        # Información del modelo
                        'model': model_info,
                        # Datos adicionales
                        'duration': video.duration,
                        'resolution': video.resolution,
                        'aspect_ratio': config.get('aspect_ratio') or config.get('orientation'),
                        # Información del prompt template
                        'prompt_template': prompt_template_info,
                    },
                    'navigation': {
                        'prev': {
                            'uuid': str(prev_item.uuid),
                            'type': 'video',
                            'title': prev_item.title or 'Sin título',
                            'url': prev_url
                        } if prev_item else None,
                        'next': {
                            'uuid': str(next_item.uuid),
                            'type': 'video',
                            'title': next_item.title or 'Sin título',
                            'url': next_url
                        } if next_item else None,
                        'project_id': nav_project_id,
                    }
                })
                
            elif item_type == 'image':
                image = get_object_or_404(Image, uuid=item_uuid)
                if not (image.project_id in user_project_ids or (image.project is None and image.created_by == user)):
                    return JsonResponse({'error': 'No tienes acceso a esta imagen'}, status=403)
                
                # Determinar el contexto del proyecto para navegación (ID para filtros, UUID para URLs)
                nav_project_id = project_id or (image.project_id if image.project else None)
                nav_project_uuid = image.project.uuid if image.project else None
                
                # Filtro para navegación: solo items del mismo proyecto o sin proyecto
                if nav_project_id:
                    nav_filter = Q(project_id=nav_project_id)
                else:
                    nav_filter = Q(project__isnull=True, created_by=user)
                
                image_service = self.get_image_service()
                image_data = image_service.get_image_with_signed_url(image)
                
                # Obtener items previo y siguiente dentro del mismo contexto
                prev_item = Image.objects.filter(
                    nav_filter,
                    created_at__lt=image.created_at
                ).order_by('-created_at').first()
                
                next_item = Image.objects.filter(
                    nav_filter,
                    created_at__gt=image.created_at
                ).order_by('created_at').first()
                
                # Obtener info del modelo usando model_id del config si está disponible
                model_id = image.config.get('model_id')
                if model_id:
                    model_info = get_model_info_for_item('image', model_id)
                else:
                    model_info = get_model_info_for_item('image', image.type)
                
                # Obtener información del prompt template si existe (optimizado para evitar N+1)
                prompt_template_info = None
                prompt_template_id = image.config.get('prompt_template_id')
                if prompt_template_id:
                    try:
                        from core.models import PromptTemplate
                        # Usar only() para limitar campos y optimizar query
                        template = PromptTemplate.objects.filter(
                            uuid=prompt_template_id, 
                            is_active=True
                        ).only('uuid', 'name', 'description', 'preview_url').first()
                        if template:
                            preview_url = template.preview_url or ''
                            # Si es una URL de GCS, convertir a URL firmada
                            if preview_url and preview_url.startswith('gs://'):
                                try:
                                    from core.storage.gcs import gcs_storage
                                    preview_url = gcs_storage.get_signed_url(preview_url, expiration=3600)
                                except Exception as e:
                                    logger.warning(f'Error obteniendo URL firmada para preview: {e}')
                            
                            prompt_template_info = {
                                'uuid': str(template.uuid),
                                'name': template.name,
                                'description': template.description or '',
                                'preview_url': preview_url,
                            }
                    except Exception as e:
                        logger.warning(f'Error obteniendo prompt template {prompt_template_id}: {e}')
                
                # URL de detalle con contexto de proyecto si aplica
                if nav_project_uuid:
                    detail_url = reverse('core:project_image_detail', args=[nav_project_uuid, image.uuid])
                    prev_url = reverse('core:project_image_detail', args=[nav_project_uuid, prev_item.uuid]) if prev_item else None
                    next_url = reverse('core:project_image_detail', args=[nav_project_uuid, next_item.uuid]) if next_item else None
                else:
                    detail_url = reverse('core:image_detail', args=[image.uuid])
                    prev_url = reverse('core:image_detail', args=[prev_item.uuid]) if prev_item else None
                    next_url = reverse('core:image_detail', args=[next_item.uuid]) if next_item else None
                
                return JsonResponse({
                    'item': {
                        'id': str(image.uuid),
                        'type': 'image',
                        'title': image.title,
                        'status': image.status,
                        'status_display': image.get_status_display(),
                        'created_at': image.created_at.isoformat(),
                        'completed_at': image.completed_at.isoformat() if image.completed_at else None,
                        'project': {
                            'id': image.project.id if image.project else None,
                            'uuid': str(image.project.uuid) if image.project else None,
                            'name': image.project.name if image.project else None,
                        },
                        'image_type': image.get_type_display(),
                        'image_type_key': image.type,
                        'prompt': image.prompt,
                        'aspect_ratio': image.aspect_ratio,
                        'width': image.width,
                        'height': image.height,
                        'config': image.config or {},
                        'metadata': image.metadata or {},
                        'error_message': image.error_message,
                        'signed_url': image_data.get('signed_url'),
                        'detail_url': detail_url,
                        'delete_url': reverse('core:image_delete', args=[image.uuid]),
                        'generate_url': reverse('core:image_generate', args=[image.uuid]),
                        # Información del modelo
                        'model': model_info,
                        # Información del prompt template
                        'prompt_template': prompt_template_info,
                    },
                    'navigation': {
                        'prev': {
                            'uuid': str(prev_item.uuid),
                            'type': 'image',
                            'title': prev_item.title or 'Sin título',
                            'url': prev_url
                        } if prev_item else None,
                        'next': {
                            'uuid': str(next_item.uuid),
                            'type': 'image',
                            'title': next_item.title or 'Sin título',
                            'url': next_url
                        } if next_item else None,
                        'project_id': nav_project_id,
                    }
                })
                
            elif item_type == 'audio':
                audio = get_object_or_404(Audio, uuid=item_uuid)
                if not (audio.project_id in user_project_ids or (audio.project is None and audio.created_by == user)):
                    return JsonResponse({'error': 'No tienes acceso a este audio'}, status=403)
                
                # Determinar el contexto del proyecto para navegación (ID para filtros, UUID para URLs)
                nav_project_id = project_id or (audio.project_id if audio.project else None)
                nav_project_uuid = audio.project.uuid if audio.project else None
                
                # Filtro para navegación: solo items del mismo proyecto o sin proyecto
                if nav_project_id:
                    nav_filter = Q(project_id=nav_project_id)
                else:
                    nav_filter = Q(project__isnull=True, created_by=user)
                
                audio_service = self.get_audio_service()
                audio_data = audio_service.get_audio_with_signed_url(audio)
                
                # Obtener items previo y siguiente dentro del mismo contexto
                prev_item = Audio.objects.filter(
                    nav_filter,
                    created_at__lt=audio.created_at
                ).order_by('-created_at').first()
                
                next_item = Audio.objects.filter(
                    nav_filter,
                    created_at__gt=audio.created_at
                ).order_by('created_at').first()
                
                # Obtener info del modelo usando el model_id del audio
                model_id = audio.model_id or 'elevenlabs'  # Default a elevenlabs si no hay model_id
                model_info = get_model_info_for_item('audio', model_key=model_id)
                
                # URL de detalle con contexto de proyecto si aplica
                if nav_project_uuid:
                    detail_url = reverse('core:project_audio_detail', args=[nav_project_uuid, audio.uuid])
                    prev_url = reverse('core:project_audio_detail', args=[nav_project_uuid, prev_item.uuid]) if prev_item else None
                    next_url = reverse('core:project_audio_detail', args=[nav_project_uuid, next_item.uuid]) if next_item else None
                else:
                    detail_url = reverse('core:audio_detail', args=[audio.uuid])
                    prev_url = reverse('core:audio_detail', args=[prev_item.uuid]) if prev_item else None
                    next_url = reverse('core:audio_detail', args=[next_item.uuid]) if next_item else None
                
                return JsonResponse({
                    'item': {
                        'id': str(audio.uuid),
                        'type': 'audio',
                        'title': audio.title,
                        'status': audio.status,
                        'status_display': audio.get_status_display(),
                        'created_at': audio.created_at.isoformat(),
                        'completed_at': audio.completed_at.isoformat() if audio.completed_at else None,
                        'project': {
                            'id': audio.project.id if audio.project else None,
                            'uuid': str(audio.project.uuid) if audio.project else None,
                            'name': audio.project.name if audio.project else None,
                        },
                        'text': audio.text,
                        'prompt': audio.prompt if audio.type == 'music' else audio.text,  # Para música usar prompt, para TTS usar text
                        'error_message': audio.error_message,
                        'signed_url': audio_data.get('signed_url'),
                        'detail_url': detail_url,
                        'delete_url': reverse('core:audio_delete', args=[audio.uuid]),
                        # Información del modelo
                        'model': model_info,
                        # Datos adicionales de audio
                        'voice_id': audio.voice_id,
                        'voice_name': audio.voice_name,
                        'duration': audio.duration,
                        'audio_type': audio.type,  # 'tts' o 'music'
                        'audio_background': audio.background_gradient, # Nuevo campo para miniatura dinámica
                    },
                    'navigation': {
                        'prev': {
                            'uuid': str(prev_item.uuid),
                            'type': 'audio',
                            'title': prev_item.title or 'Sin título',
                            'url': prev_url
                        } if prev_item else None,
                        'next': {
                            'uuid': str(next_item.uuid),
                            'type': 'audio',
                            'title': next_item.title or 'Sin título',
                            'url': next_url
                        } if next_item else None,
                        'project_id': nav_project_id,
                    }
                })
            else:
                return JsonResponse({'error': 'Tipo no válido'}, status=400)
                
        except Exception as e:
            logger.error(f"Error al obtener detalles del item: {e}")
            return JsonResponse({
                'error': 'Error al cargar detalles',
                'error_detail': str(e)
            }, status=500)


class CreateItemAPIView(ServiceMixin, View):
    """API endpoint para crear items (video, image, audio) vía AJAX"""
    
    def post(self, request):
        """
        Crea un nuevo item según el tipo especificado
        
        Body JSON o FormData:
            type: 'video', 'image', 'audio'
            model_id: ID del modelo seleccionado
            title: Título del item
            prompt/script/text: Contenido según tipo
            project_id: ID del proyecto (opcional)
            settings: Diccionario con configuración adicional (JSON string si es FormData)
            start_image, end_image, style_image, asset_image: Archivos de imagen (opcional, solo FormData)
        """
        import json
        
        # Detectar si es FormData o JSON
        is_form_data = request.content_type and 'multipart/form-data' in request.content_type
        
        logger.info(f"[CreateItemAPIView] Content-Type: {request.content_type}")
        logger.info(f"[CreateItemAPIView] Es FormData: {is_form_data}")
        logger.info(f"[CreateItemAPIView] request.FILES keys: {list(request.FILES.keys())}")
        
        if is_form_data:
            data = request.POST.copy()
            # Parsear settings si viene como JSON string
            if 'settings' in data:
                try:
                    settings = json.loads(data['settings'])
                except (json.JSONDecodeError, TypeError):
                    settings = {}
            else:
                settings = {}
        else:
            try:
                data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
            except json.JSONDecodeError:
                data = request.POST
            settings = data.get('settings', {})
        
        item_type = data.get('type')
        model_id = data.get('model_id')
        title = data.get('title')
        project_id = data.get('project_id')
        
        if not all([item_type, model_id, title]):
            return JsonResponse({
                'success': False,
                'error': 'Faltan campos requeridos: type, model_id, title'
            }, status=400)
        
        project = None
        if project_id:
            try:
                project = get_object_or_404(Project, pk=project_id)
                if not ProjectService.user_has_access(project, request.user):
                    return JsonResponse({
                        'success': False,
                        'error': 'No tienes acceso a este proyecto'
                    }, status=403)
            except (ValueError, Project.DoesNotExist):
                return JsonResponse({
                    'success': False,
                    'error': 'Proyecto no encontrado'
                }, status=404)
        
        try:
            if item_type == 'video':
                return self._create_video(request, data, project, settings)
            elif item_type == 'image':
                return self._create_image(request, data, project, settings)
            elif item_type == 'audio':
                return self._create_audio(request, data, project, settings)
            else:
                return JsonResponse({
                    'success': False,
                    'error': f'Tipo no válido: {item_type}'
                }, status=400)
        except Exception as e:
            logger.error(f"Error al crear item: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    def _create_video(self, request, data, project, settings):
        """Crear video"""
        from .ai_services.model_config import get_video_type_from_model_id
        from datetime import datetime
        
        model_id = data.get('model_id')
        title = data.get('title')
        script = data.get('script') or data.get('prompt', '')
        
        # Mapear model_id a video_type usando la función helper
        video_type = get_video_type_from_model_id(model_id)
        
        if not video_type:
            raise ValidationException(f'No se pudo determinar el tipo de video para el modelo: {model_id}')
        
        video_service = self.get_video_service()
        
        # Construir configuración
        # Asegurar que settings es un diccionario
        if not isinstance(settings, dict):
            settings = {}
        
        # Convertir duration a int, usando valor por defecto si es None o vacío
        duration = settings.get('duration')
        if duration is None or duration == '':
            # Obtener duración por defecto del modelo
            from core.ai_services.model_config import get_model_capabilities
            capabilities = get_model_capabilities(model_id)
            if capabilities:
                supports = capabilities.get('supports', {})
                dur_config = supports.get('duration', {})
                # Si duration es False, no usar duración (ej: HeyGen Avatar IV)
                if dur_config is False:
                    duration = None
                elif isinstance(dur_config, dict):
                    if dur_config.get('fixed'):
                        duration = dur_config['fixed']
                    elif dur_config.get('options'):
                        duration = dur_config['options'][0]
                    elif dur_config.get('min'):
                        duration = dur_config['min']
                    else:
                        duration = 8  # Default general
                else:
                    duration = 8
            else:
                duration = 8
        else:
            # Convertir a int si es string
            try:
                duration = int(duration)
            except (ValueError, TypeError):
                duration = 8
        
        config = {
            'model_id': model_id,  # Guardar model_id para usar el modelo correcto al generar
            'aspect_ratio': settings.get('aspect_ratio'),
            'mode': settings.get('mode'),
            'negative_prompt': settings.get('negative_prompt'),
            'seed': settings.get('seed'),
        }
        
        # Solo agregar prompt_template_id si existe, no está vacío, y el modelo lo soporta
        # HeyGen y Manim no usan prompt templates
        prompt_template_id = data.get('prompt_template_id')
        is_heygen = 'heygen' in model_id.lower() if model_id else False
        is_manim = 'manim' in model_id.lower() if model_id else False
        
        if prompt_template_id and prompt_template_id.strip() and not is_heygen and not is_manim:
            config['prompt_template_id'] = prompt_template_id.strip()
        
        # Solo agregar duration si no es None (para modelos que no requieren duración)
        if duration is not None:
            config['duration'] = duration
        
        # Para Veo, también guardar veo_model (nombre del modelo de Veo)
        if video_type == 'gemini_veo':
            config['veo_model'] = model_id  # El model_id ya es el nombre del modelo de Veo (ej: veo-2.0-generate-exp)
        
        # Para Manim Quote, añadir campos específicos
        if video_type == 'manim_quote':
            # Tipo de animación de Manim (quote por defecto, o bar_chart, etc.)
            config['animation_type'] = settings.get('manim_animation_type') or data.get('manim_animation_type') or 'quote'
            config['author'] = settings.get('author') or data.get('author')
            config['quality'] = settings.get('quality') or data.get('quality', 'k')
            config['container_color'] = settings.get('container_color') or data.get('container_color') or '#0066CC'
            config['text_color'] = settings.get('text_color') or data.get('text_color') or '#FFFFFF'
            config['font_family'] = settings.get('font_family') or data.get('font_family') or 'normal'
            # Si duration viene como string desde el formulario, convertir a float (Manim acepta decimales)
            if duration:
                try:
                    duration = float(duration)
                    config['duration'] = duration
                except (ValueError, TypeError):
                    pass
        
        # Para HeyGen Avatar V2, añadir campos específicos
        if video_type == 'heygen_avatar_v2':
            # Obtener avatar_id y voice_id (requeridos)
            config['avatar_id'] = settings.get('avatar_id') if 'avatar_id' in settings else data.get('avatar_id')
            config['voice_id'] = settings.get('voice_id') if 'voice_id' in settings else data.get('voice_id')
            
            # Validar campos requeridos ANTES de crear el video
            if not config.get('avatar_id'):
                raise ValidationException('El campo Avatar es requerido para HeyGen Avatar V2. Por favor selecciona un avatar.')
            if not config.get('voice_id'):
                raise ValidationException('El campo Voz es requerido para HeyGen Avatar V2. Por favor selecciona una voz.')
            # Convertir has_background a boolean correctamente
            has_bg_setting = settings.get('has_background', False)
            has_bg_data = data.get('has_background', False)
            has_background = has_bg_setting if 'has_background' in settings else has_bg_data
            logger.info(f"[HeyGen V2] has_background raw - settings: {has_bg_setting}, data: {has_bg_data}, final: {has_background}")
            if isinstance(has_background, str):
                config['has_background'] = has_background.lower() in ('true', '1', 'yes', 'on')
            else:
                config['has_background'] = bool(has_background)
            config['background_url'] = settings.get('background_url') if 'background_url' in settings else data.get('background_url')
            logger.info(f"[HeyGen V2] Background config - has_background: {config['has_background']}, background_url: {config.get('background_url')}")
            config['voice_speed'] = settings.get('voice_speed') if 'voice_speed' in settings else data.get('voice_speed', 1.0)
            config['voice_pitch'] = settings.get('voice_pitch') if 'voice_pitch' in settings else data.get('voice_pitch', 50)
            config['voice_emotion'] = settings.get('voice_emotion') if 'voice_emotion' in settings else data.get('voice_emotion', 'Excited')
            # Convertir valores numéricos si vienen como string
            try:
                if isinstance(config['voice_speed'], str):
                    config['voice_speed'] = float(config['voice_speed'])
            except (ValueError, TypeError):
                config['voice_speed'] = 1.0
            try:
                if isinstance(config['voice_pitch'], str):
                    config['voice_pitch'] = int(config['voice_pitch'])
            except (ValueError, TypeError):
                config['voice_pitch'] = 50
        
        # Para HeyGen Avatar IV, añadir campos específicos
        if video_type == 'heygen_avatar_iv':
            # Obtener voice_id (requerido)
            config['voice_id'] = settings.get('voice_id') if 'voice_id' in settings else data.get('voice_id')
            config['video_orientation'] = settings.get('video_orientation') if 'video_orientation' in settings else data.get('video_orientation', 'portrait')
            config['fit'] = settings.get('fit') if 'fit' in settings else data.get('fit', 'cover')
            
            # Validar voice_id requerido ANTES de crear el video
            if not config.get('voice_id'):
                raise ValidationException('El campo Voz es requerido para HeyGen Avatar IV. Por favor selecciona una voz.')
            
            # Manejar imagen de avatar: puede venir como start_image (formulario dinámico) o avatar_image_id (select)
            # start_image se procesará más abajo en el código, aquí solo manejamos avatar_image_id
            avatar_image_id = settings.get('avatar_image_id') if 'avatar_image_id' in settings else data.get('avatar_image_id')
            if avatar_image_id:
                config['existing_image_id'] = avatar_image_id
                config['image_source'] = 'existing'
            # Si viene start_image, se procesará más abajo y se guardará en config['start_image']
        
        # Procesar imágenes de referencia desde request.FILES
        # Nota: Veo solo acepta "asset" o "style" como referenceType
        # start_image y end_image son para otros servicios (Kling, Higgsfield) y se manejan diferente
        reference_images = []
        reference_types = []
        
        logger.info(f"[_create_video] request.FILES keys disponibles: {list(request.FILES.keys())}")
        
        # Para Veo: style_image y asset_image_1/2/3 son imágenes de referencia
        # start_image y end_image se manejan como input_image para image-to-video
        if 'style_image' in request.FILES:
            ref_file = request.FILES['style_image']
            reference_images.append(ref_file)
            reference_types.append('style')
            logger.info(f"✅ Imagen de referencia encontrada: style_image -> style (tamaño: {ref_file.size} bytes)")
        else:
            logger.info(f"❌ style_image no encontrado en request.FILES")
        
        # Múltiples assets (hasta 3)
        for i in range(1, 4):
            asset_key = f'asset_image_{i}'
            if asset_key in request.FILES:
                ref_file = request.FILES[asset_key]
                reference_images.append(ref_file)
                reference_types.append('asset')
                logger.info(f"✅ Imagen de referencia encontrada: {asset_key} -> asset (tamaño: {ref_file.size} bytes)")
        
        # Mantener compatibilidad con el nombre antiguo asset_image (sin número)
        if 'asset_image' in request.FILES and not any(f'asset_image_{i}' in request.FILES for i in range(1, 4)):
            ref_file = request.FILES['asset_image']
            reference_images.append(ref_file)
            reference_types.append('asset')
            logger.info(f"✅ Imagen de referencia encontrada: asset_image (legacy) -> asset (tamaño: {ref_file.size} bytes)")
        
        # Subir imágenes de referencia si hay alguna (solo para Veo)
        if reference_images and video_type == 'gemini_veo':
            # IMPORTANTE: Veo requiere duración de 8s cuando hay imágenes de referencia
            if duration != 8:
                logger.warning(f"Duración ajustada de {duration}s a 8s porque hay imágenes de referencia")
                duration = 8
                config['duration'] = 8
            
            uploaded_refs = video_service.upload_veo_reference_images(
                reference_images, reference_types, project
            )
            config['reference_images'] = uploaded_refs
            logger.info(f"✅ {len(uploaded_refs)} imagen(es) de referencia subida(s) para Veo")
        
        # start_image y end_image se manejan diferente según el servicio
        # Para Veo: start_image es input_image (image-to-video)
        # Para HeyGen Avatar IV: start_image es la imagen de avatar
        # Para otros servicios: pueden ser referencias específicas
        if 'start_image' in request.FILES:
            start_file = request.FILES['start_image']
            if video_type == 'gemini_veo':
                # Para Veo, start_image es input_image para image-to-video
                from .storage.gcs import gcs_storage
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                safe_filename = start_file.name.replace(' ', '_')
                gcs_destination = f"videos/project_{project.id if project else 'standalone'}/{timestamp}_start_{safe_filename}"
                gcs_path = gcs_storage.upload_django_file(start_file, gcs_destination)
                config['input_image_gcs_uri'] = gcs_path
                config['input_image_mime_type'] = start_file.content_type or 'image/jpeg'
                logger.info(f"✅ Imagen inicial subida para image-to-video: {gcs_path}")
            elif video_type == 'heygen_avatar_iv':
                # Para HeyGen Avatar IV, start_image es la imagen de avatar
                from .storage.gcs import gcs_storage
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                safe_filename = start_file.name.replace(' ', '_')
                gcs_destination = f"videos/project_{project.id if project else 'standalone'}/{timestamp}_start_{safe_filename}"
                gcs_path = gcs_storage.upload_django_file(start_file, gcs_destination)
                config['start_image'] = gcs_path
                config['gcs_avatar_path'] = gcs_path  # También guardar en gcs_avatar_path para compatibilidad
                config['image_source'] = 'upload'
                logger.info(f"✅ Imagen de avatar subida para HeyGen Avatar IV: {gcs_path}")
            else:
                # Para otros servicios, guardar en config para procesamiento específico
                from .storage.gcs import gcs_storage
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                safe_filename = start_file.name.replace(' ', '_')
                gcs_destination = f"videos/project_{project.id if project else 'standalone'}/{timestamp}_start_{safe_filename}"
                gcs_path = gcs_storage.upload_django_file(start_file, gcs_destination)
                config['start_image'] = gcs_path
                logger.info(f"✅ Imagen inicial subida: {gcs_path}")
        
        if 'end_image' in request.FILES:
            end_file = request.FILES['end_image']
            from .storage.gcs import gcs_storage
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_filename = end_file.name.replace(' ', '_')
            gcs_destination = f"videos/project_{project.id if project else 'standalone'}/{timestamp}_end_{safe_filename}"
            gcs_path = gcs_storage.upload_django_file(end_file, gcs_destination)
            config['end_image'] = gcs_path
            logger.info(f"✅ Imagen final subida: {gcs_path}")
        
        # Validación adicional para HeyGen Avatar IV: requiere imagen de avatar
        if video_type == 'heygen_avatar_iv':
            has_avatar_image = (
                config.get('start_image') or 
                config.get('gcs_avatar_path') or 
                config.get('existing_image_id')
            )
            if not has_avatar_image:
                raise ValidationException(
                    'HeyGen Avatar IV requiere una imagen de avatar. '
                    'Por favor sube una imagen usando el campo "Start Image" en Referencias, '
                    'o selecciona una imagen existente.'
                )
        
        # Crear video
        video = video_service.create_video(
            created_by=request.user,
            project=project,
            title=title,
            video_type=video_type,
            script=script,
            config=config
        )
        
        # Encolar generación automáticamente
        try:
            task = video_service.generate_video_async(video)
            generate_status = 'started'
            video.refresh_from_db()
            # Mostrar toast de que se encoló la tarea
            toast_message = {
                'type': 'info',
                'title': 'Video encolado',
                'message': f'El video "{video.title}" está en cola y comenzará a generarse pronto',
                'auto_close': 5
            }
        except Exception as e:
            logger.warning(f"Error al encolar generación de video: {e}")
            generate_status = 'error'
            toast_message = {
                'type': 'error',
                'title': 'Error al encolar',
                'message': f'No se pudo encolar la generación: {str(e)[:100]}',
                'auto_close': 10
            }
        
        response_data = {
            'success': True,
            'item': {
                'id': str(video.uuid),
                'type': 'video',
                'title': video.title,
                'status': video.status,
                'detail_url': reverse('core:video_detail', args=[video.uuid]),
            },
            'generate_status': generate_status
        }
        
        # Agregar toast al response si existe
        if toast_message:
            response_data['toast'] = toast_message
        
        return JsonResponse(response_data)
    
    def _create_image(self, request, data, project, settings):
        """Crear imagen"""
        model_id = data.get('model_id')
        title = data.get('title')
        prompt = data.get('prompt', '')
        
        image_service = self.get_image_service()
        
        # Construir configuración
        config = {
            'model_id': model_id,  # Guardar model_id para usar el servicio correcto
            'aspect_ratio': settings.get('aspect_ratio', '1:1'),
            'negative_prompt': settings.get('negative_prompt'),
            'seed': settings.get('seed'),
        }
        
        # Solo agregar prompt_template_id si existe, no está vacío
        # (Las imágenes sí pueden usar prompt templates, a diferencia de HeyGen/Manim)
        prompt_template_id = data.get('prompt_template_id')
        if prompt_template_id and prompt_template_id.strip():
            config['prompt_template_id'] = prompt_template_id.strip()
        
        # Crear imagen
        image = image_service.create_image(
            created_by=request.user,
            project=project,
            title=title,
            image_type='text_to_image',  # Por defecto, se puede ajustar según model_id
            prompt=prompt,
            config=config
        )
        
        # Encolar generación automáticamente
        try:
            task = image_service.generate_image_async(image)
            generate_status = 'started'
            # Refrescar imagen para obtener el estado actualizado (debería ser 'pending')
            image.refresh_from_db()
            # Mostrar toast de que se encoló la tarea
            toast_message = {
                'type': 'info',
                'title': 'Imagen encolada',
                'message': f'La imagen "{image.title}" está en cola y comenzará a generarse pronto',
                'auto_close': 5
            }
        except Exception as e:
            logger.error(f"Error al encolar generación de imagen: {e}", exc_info=True)
            generate_status = 'error'
            # Marcar imagen como error
            image.mark_as_error(str(e)[:500])  # Limitar longitud del mensaje
            # Disparar toast de error
            toast_message = {
                'type': 'error',
                'title': 'Error al encolar',
                'message': f'No se pudo encolar la generación: {str(e)[:100]}',
                'auto_close': 10
            }
        
        # Refrescar imagen desde BD para obtener el estado actualizado
        image.refresh_from_db()
        
        response_data = {
            'success': True,
            'item': {
                'id': str(image.uuid),
                'type': 'image',
                'title': image.title,
                'status': image.status,  # Incluir estado actualizado (puede ser 'error' si falló)
                'error_message': image.error_message if hasattr(image, 'error_message') else None,
                'detail_url': reverse('core:image_detail', args=[image.uuid]),
            },
            'generate_status': generate_status
        }
        
        # Agregar toast al response si existe
        if toast_message:
            response_data['toast'] = toast_message
        
        return JsonResponse(response_data)
    
    def _create_audio(self, request, data, project, settings):
        """Crear audio (TTS o Música)"""
        from decouple import config as get_config
        
        title = data.get('title')
        audio_type = data.get('type', 'tts') or 'tts'  # 'tts' o 'music'
        model_id = data.get('model_id', '')
        
        audio_service = self.get_audio_service()
        
        # Determinar si es música basándose en type o model_id
        is_music = (
            audio_type == 'music' or 
            model_id.startswith('lyria-') or 
            model_id in ['lyria-002']
        )
        
        if is_music:
            # Crear audio de música con Lyria
            prompt = data.get('prompt') or data.get('text', '')
            if not prompt:
                return JsonResponse({
                    'success': False,
                    'error': 'El prompt es requerido para generar música'
                }, status=400)
            
            negative_prompt = data.get('negative_prompt')
            seed = data.get('seed')
            sample_count = data.get('sample_count')
            
            # Convertir seed y sample_count a int si vienen como string
            if seed is not None:
                try:
                    seed = int(seed) if not isinstance(seed, int) else seed
                except (ValueError, TypeError):
                    seed = None
            
            if sample_count is not None:
                try:
                    sample_count = int(sample_count) if not isinstance(sample_count, int) else sample_count
                except (ValueError, TypeError):
                    sample_count = None
            
            audio = audio_service.create_music_audio(
                title=title,
                prompt=prompt,
                created_by=request.user,
                model_id=model_id or 'lyria-002',
                negative_prompt=negative_prompt,
                seed=seed,
                sample_count=sample_count,
                project=project
            )
        else:
            # Crear audio TTS con ElevenLabs
            text = data.get('text') or data.get('prompt', '')
            # voice_id puede venir de settings, data, o usar el default
            voice_id = settings.get('voice_id') or settings.get('voice') or data.get('voice_id') or get_config('ELEVENLABS_DEFAULT_VOICE_ID', default='21m00Tcm4TlvDq8ikWAM')
            
            audio = audio_service.create_audio(
                title=title,
                text=text,
                voice_id=voice_id,
                created_by=request.user,
                project=project
            )
        
        # Encolar generación automáticamente
        try:
            task = audio_service.generate_audio_async(audio)
            generate_status = 'started'
            audio.refresh_from_db()
            # Mostrar toast de que se encoló la tarea
            audio_preview = audio.text[:50] if audio.text else (audio.prompt[:50] if audio.prompt else audio.title)
            toast_message = {
                'type': 'info',
                'title': 'Audio encolado',
                'message': f'El audio "{audio_preview}..." está en cola y comenzará a generarse pronto',
                'auto_close': 5
            }
        except Exception as e:
            logger.warning(f"Error al encolar generación de audio: {e}")
            generate_status = 'error'
            toast_message = {
                'type': 'error',
                'title': 'Error al encolar',
                'message': f'No se pudo encolar la generación: {str(e)[:100]}',
                'auto_close': 10
            }
        
        response_data = {
            'success': True,
            'item': {
                'id': str(audio.uuid),
                'type': 'audio',
                'title': audio.title,
                'status': audio.status,
                'detail_url': reverse('core:audio_detail', args=[audio.uuid]),
            },
            'generate_status': generate_status
        }
        
        # Agregar toast al response si existe
        if toast_message:
            response_data['toast'] = toast_message
        
        return JsonResponse(response_data)


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

class ImageLibraryView(SidebarProjectsMixin, BreadcrumbMixin, ServiceMixin, HeyGenPreloadMixin, View):
    """Vista unificada para creación y biblioteca de imágenes"""
    template_name = 'creation/base_creation.html'
    
    def get_project(self):
        """Obtener proyecto del contexto (opcional)"""
        project_uuid = self.kwargs.get('project_uuid')
        if project_uuid:
            return get_object_or_404(Project, uuid=project_uuid)
        return None
    
    def get(self, request, *args, **kwargs):
        from django.db.models import Q
        
        project = self.get_project()
        user = request.user
        
        # Calcular conteo de imágenes
        if project:
            image_count = Image.objects.filter(project=project).count()
        else:
            user_projects = ProjectService.get_user_projects(user)
            user_project_ids = [p.id for p in user_projects]
            base_filter = Q(project_id__in=user_project_ids) | Q(project__isnull=True, created_by=user)
            image_count = Image.objects.filter(base_filter).count()
        
        # Obtener template "General" por defecto para imágenes
        default_template_id = None
        try:
            default_template = PromptTemplate.objects.filter(
                name='General',
                template_type='image',
                is_public=True,
                is_active=True
            ).order_by('-usage_count').first()
            
            if default_template:
                default_template_id = str(default_template.uuid)
        except Exception as e:
            logger.error(f"Error obteniendo template por defecto para imágenes: {e}")
        
        context = {
            'project': project,
            'active_tab': 'image',
            'breadcrumbs': self.get_breadcrumbs(),
            'projects': ProjectService.get_user_projects(request.user),
            'items_count': image_count,
            'default_template_id': default_template_id,  # Template "General" por defecto
        }
        
        if project:
            context['user_role'] = project.get_user_role(request.user)
            context['project_owner'] = project.owner
            context['project_members'] = project.members.select_related('user').all()
        
        return render(request, self.template_name, context)
    
    def get_breadcrumbs(self):
        project = self.get_project()
        if project:
            return [
                {
                    'label': project.name, 
                    'url': reverse('core:project_overview', args=[project.uuid])
                },
                {'label': 'Imágenes', 'url': None}
            ]
        return [
            {'label': 'Imágenes', 'url': None}
        ]


class ImageDetailView(SidebarProjectsMixin, BreadcrumbMixin, ServiceMixin, DetailView):
    """Detalle de una imagen - usa el layout de creación unificado"""
    model = Image
    template_name = 'creation/base_creation.html'
    context_object_name = 'image'
    
    def get_object(self, queryset=None):
        """Buscar imagen por UUID"""
        if queryset is None:
            queryset = self.get_queryset()
        image_uuid = self.kwargs.get('image_uuid')
        return get_object_or_404(queryset, uuid=image_uuid)
    
    def get_project(self):
        """Obtener proyecto de la URL o del objeto"""
        project_uuid = self.kwargs.get('project_uuid')
        if project_uuid:
            return get_object_or_404(Project, uuid=project_uuid)
        return self.object.project
    
    def get_breadcrumbs(self):
        project = self.get_project()
        breadcrumbs = []
        if project:
            breadcrumbs.append({
                'label': project.name, 
                'url': reverse('core:project_overview', args=[project.uuid])
            })
            breadcrumbs.append({
                'label': 'Imágenes', 
                'url': reverse('core:project_images_library', args=[project.uuid])
            })
        else:
            breadcrumbs.append({'label': 'Imágenes', 'url': reverse('core:image_library')})
        breadcrumbs.append({'label': self.object.title, 'url': None})
        return breadcrumbs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_project()
        context['active_tab'] = 'image'
        context['initial_item_type'] = 'image'
        context['initial_item_id'] = str(self.object.uuid)
        if project:
            context['project'] = project
            context['user_role'] = project.get_user_role(self.request.user)
            context['project_owner'] = project.owner
            context['project_members'] = project.members.select_related('user').all()
        return context


class ImageCreateView(SidebarProjectsMixin, BreadcrumbMixin, ServiceMixin, FormView):
    """Crear nueva imagen"""
    template_name = 'images/create.html'
    form_class = GeminiImageForm
    
    def get_project(self):
        """Obtener proyecto del contexto (opcional)"""
        project_uuid = self.kwargs.get('project_uuid')
        if project_uuid:
            return get_object_or_404(Project, uuid=project_uuid)
        return None
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_project()
        if project:
            context['project'] = project
            context['user_role'] = project.get_user_role(self.request.user)
            context['project_owner'] = project.owner
            context['project_members'] = project.members.select_related('user').all()
            context.setdefault('active_tab', 'images')
        return context
    
    def get_breadcrumbs(self):
        project = self.get_project()
        if project:
            return [
                {
                    'label': project.name, 
                    'url': reverse('core:project_detail', args=[project.uuid])
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
            
            # Encolar generación de imagen automáticamente después de crear
            try:
                task = image_service.generate_image_async(image)
                messages.success(request, f'Imagen "{title}" creada y encolada para generación.')
            except (ValidationException, ImageGenerationException) as e:
                messages.warning(request, f'Imagen "{title}" creada, pero hubo un error al encolar la generación: {str(e)}')
            except Exception as e:
                messages.warning(request, f'Imagen "{title}" creada, pero hubo un error inesperado al generarla: {str(e)}')
            
            return redirect('core:image_detail', image_uuid=image.uuid)
            
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
        project_uuid = self.kwargs['project_uuid']
        return get_object_or_404(Project, uuid=project_uuid)
    
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
            
            # Encolar generación de imagen automáticamente después de crear
            try:
                task = image_service.generate_image_async(image)
                messages.success(request, f'Imagen "{title}" creada y encolada para generación.')
            except (ValidationException, ImageGenerationException) as e:
                messages.warning(request, f'Imagen "{title}" creada, pero hubo un error al encolar la generación: {str(e)}')
            except Exception as e:
                messages.warning(request, f'Imagen "{title}" creada, pero hubo un error inesperado al generarla: {str(e)}')
            
            return redirect('core:image_detail', image_uuid=image.uuid)
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
    
    def get_object(self, queryset=None):
        """Buscar imagen por UUID"""
        if queryset is None:
            queryset = self.get_queryset()
        image_uuid = self.kwargs.get('image_uuid')
        return get_object_or_404(queryset, uuid=image_uuid)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['delete_url'] = reverse('core:image_delete', args=[self.object.pk])
        context['detail_url'] = reverse('core:image_detail', args=[self.object.pk])
        return context
    
    def get_success_url(self):
        if self.object.project:
            return reverse('core:project_detail', kwargs={'project_uuid': self.object.project.uuid})
        return reverse('core:dashboard')
    
    def get_breadcrumbs(self):
        breadcrumbs = []
        if self.object.project:
            breadcrumbs.append({
                'label': self.object.project.name, 
                'url': reverse('core:project_detail', args=[self.object.project.uuid])
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
        """Override para eliminar archivo de GCS y notificaciones relacionadas"""
        self.object = self.get_object()
        success_url = self.get_success_url()
        image_uuid = str(self.object.uuid)
        image_title = self.object.title
        
        # Eliminar notificaciones relacionadas con esta imagen
        try:
            from .models import Notification
            Notification.objects.filter(
                metadata__item_uuid=image_uuid,
                metadata__item_type='image'
            ).delete()
        except Exception as e:
            logger.error(f"Error al eliminar notificaciones: {e}")
        
        # Eliminar de GCS si existe
        if self.object.gcs_path:
            try:
                from .storage.gcs import gcs_storage
                gcs_storage.delete_file(self.object.gcs_path)
            except Exception as e:
                logger.error(f"Error al eliminar archivo: {e}")
        
        self.object.delete()
        
        messages.success(request, f'Imagen "{image_title}" eliminada')
        return redirect(success_url)


# ====================
# IMAGE ACTIONS
# ====================

class ImageGenerateView(ServiceMixin, View):
    """Generar imagen usando Gemini API"""
    
    def post(self, request, image_uuid):
        image = get_object_or_404(Image, uuid=image_uuid)
        image_service = self.get_image_service()
        
        try:
            task = image_service.generate_image_async(image)
            messages.success(
                request, 
                'Imagen encolada para generación.'
            )
        except InsufficientCreditsException as e:
            messages.error(request, str(e))
        except RateLimitExceededException as e:
            messages.error(request, str(e))
        except (ValidationException, ImageGenerationException) as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error inesperado: {str(e)}')
        
        return redirect('core:image_detail', image_uuid=image.uuid)


class ImageRecreateView(ServiceMixin, View):
    """Recrear una imagen con los mismos parámetros"""
    
    def post(self, request, image_uuid):
        from django.db.models import Q
        
        original_image = get_object_or_404(Image, uuid=image_uuid)
        image_service = self.get_image_service()
        
        # Verificar permisos - validación robusta
        if not request.user.is_authenticated:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied('Debes estar autenticado para recrear imágenes')
        
        if original_image.project:
            # Si tiene proyecto, verificar acceso al proyecto
            if not ProjectService.user_has_access(original_image.project, request.user):
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied('No tienes acceso a esta imagen')
        else:
            # Si no tiene proyecto, solo el creador puede recrearlo
            if not original_image.created_by or original_image.created_by != request.user:
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied('No tienes acceso a esta imagen')
        
        try:
            # Calcular número de versión basado en UUID del item original
            # Determinar el UUID del item original (puede ser el mismo si es el primero)
            original_item_uuid = original_image.config.get('original_item_uuid')
            if not original_item_uuid:
                # Si no tiene original_item_uuid, este es el item original
                original_item_uuid = str(original_image.uuid)
            
            # Contar todos los items que pertenecen a la misma "familia" de versiones
            # (todos los que tienen el mismo original_item_uuid, o el original mismo)
            version_filter = (
                Q(config__original_item_uuid=original_item_uuid) |
                Q(uuid=original_item_uuid)
            )
            if original_image.project:
                version_filter &= Q(project=original_image.project)
            else:
                version_filter &= Q(project__isnull=True, created_by=request.user)
            
            # Contar items en la familia de versiones
            version_count = Image.objects.filter(version_filter).count()
            
            # Calcular siguiente versión
            next_version = version_count + 1
            
            # Extraer título base (sin sufijo de versión si existe)
            base_title = original_image.title
            import re
            match = re.match(r'^(.+?)(\s+- v\d+)?$', base_title)
            if match:
                base_title = match.group(1)
            
            new_title = f"{base_title} - v{next_version}"
            
            # Crear nueva imagen copiando la configuración
            new_config = original_image.config.copy() if original_image.config else {}
            # Marcar el UUID del item original para rastrear versiones
            new_config['original_item_uuid'] = original_item_uuid
            
            new_image = image_service.create_image(
                title=new_title,
                image_type=original_image.type,
                prompt=original_image.prompt,
                config=new_config,
                created_by=request.user,
                project=original_image.project
            )
            
            # Generar la imagen automáticamente
            task = image_service.generate_image_async(new_image)
            
            messages.success(
                request,
                f'Imagen "{new_title}" creada y encolada para generación.'
            )
            
            # Redirigir a la nueva imagen
            if new_image.project:
                return redirect('core:project_image_detail', project_uuid=new_image.project.uuid, image_uuid=new_image.uuid)
            else:
                return redirect('core:image_detail', image_uuid=new_image.uuid)
                
        except InsufficientCreditsException as e:
            messages.error(request, str(e))
            return redirect('core:image_detail', image_uuid=original_image.uuid)
        except RateLimitExceededException as e:
            messages.error(request, str(e))
            return redirect('core:image_detail', image_uuid=original_image.uuid)
        except (ValidationException, ServiceException) as e:
            messages.error(request, str(e))
            return redirect('core:image_detail', image_uuid=original_image.uuid)
        except Exception as e:
            logger.error(f'Error al recrear imagen: {e}', exc_info=True)
            messages.error(request, f'Error inesperado: {str(e)}')
            return redirect('core:image_detail', image_uuid=original_image.uuid)


class ImageEditView(LoginRequiredMixin, ServiceMixin, View):
    """Vista para editar una imagen existente con nuevo prompt"""
    
    def get(self, request, image_uuid):
        """Muestra formulario para editar imagen"""
        from django.shortcuts import render
        from core.ai_services.model_config import get_models_by_type
        
        original_image = get_object_or_404(Image, uuid=image_uuid)
        
        # Verificar permisos
        if original_image.project:
            if not ProjectService.user_has_access(original_image.project, request.user):
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied('No tienes acceso a esta imagen')
        else:
            if not original_image.created_by or original_image.created_by != request.user:
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied('No tienes acceso a esta imagen')
        
        # Obtener modelos de imagen disponibles (solo OpenAI Image para edición)
        image_models = [
            model for model in get_models_by_type('image')
            if model.get('service') == 'openai_image'
        ]
        
        # Obtener URL firmada de la imagen original
        from core.storage.gcs import gcs_storage
        original_image_url = None
        if original_image.gcs_path:
            try:
                original_image_url = gcs_storage.get_signed_url(original_image.gcs_path, expiration=3600)
            except Exception as e:
                logger.warning(f"No se pudo obtener URL firmada: {e}")
        
        project = original_image.project
        context = {
            'original_image': original_image,
            'original_image_url': original_image_url,
            'image_models': image_models,
            'project': project,
        }
        
        # Agregar contexto del proyecto si existe
        if project:
            context['user_role'] = project.get_user_role(request.user)
            context['project_owner'] = project.owner
            context['project_members'] = project.members.select_related('user').all()
        
        return render(request, 'images/edit.html', context)
    
    def post(self, request, image_uuid):
        """Procesa la edición de imagen"""
        original_image = get_object_or_404(Image, uuid=image_uuid)
        image_service = self.get_image_service()
        
        # Verificar permisos
        if original_image.project:
            if not ProjectService.user_has_access(original_image.project, request.user):
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied('No tienes acceso a esta imagen')
        else:
            if not original_image.created_by or original_image.created_by != request.user:
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied('No tienes acceso a esta imagen')
        
        try:
            # Obtener datos del formulario
            # Valores por defecto automáticos:
            title = request.POST.get('title', f'{original_image.title} (editada)')
            prompt = request.POST.get('prompt', '')
            model_id = request.POST.get('model_id', 'gpt-image-1.5')
            aspect_ratio = request.POST.get('aspect_ratio', original_image.aspect_ratio or '1:1')
            quality = request.POST.get('quality', 'medium')
            format_type = request.POST.get('format', 'png')  # Siempre PNG por defecto
            background = request.POST.get('background', 'opaque')  # Siempre opaque por defecto
            input_fidelity = request.POST.get('input_fidelity', 'low')
            
            if not prompt:
                messages.error(request, 'El prompt es requerido')
                return redirect('core:image_edit', image_uuid=image_uuid)
            
            # Determinar tipo de edición según archivos subidos
            mask_file = request.FILES.get('mask')
            reference_images = request.FILES.getlist('reference_images')
            
            # Siempre usar image_to_image o multi_image (siempre hay imagen original)
            if reference_images and len(reference_images) > 0:
                # Multi-image: imagen original + imágenes de referencia adicionales
                image_type = 'multi_image'
            else:
                # Image-to-image: imagen original + máscara opcional
                image_type = 'image_to_image'
            
            # Construir configuración
            config = {
                'model_id': model_id,
                'aspect_ratio': aspect_ratio,
                'quality': quality,
                'format': format_type,
                'background': background,
                'input_fidelity': input_fidelity,
            }
            
            # Si es image_to_image o multi_image, necesitamos la imagen original
            if image_type in ['image_to_image', 'multi_image']:
                # Usar la imagen original como primera imagen de entrada
                if original_image.gcs_path:
                    config['input_image_gcs_path'] = original_image.gcs_path
                else:
                    messages.error(request, 'La imagen original no tiene archivo disponible')
                    return redirect('core:image_edit', image_uuid=image_uuid)
            
            # Si hay máscara, subirla
            if mask_file:
                mask_result = image_service.upload_input_image(mask_file, original_image.project)
                config['mask_gcs_path'] = mask_result['gcs_path']
            
            # Si hay imágenes de referencia, subirlas
            if reference_images and len(reference_images) > 0:
                reference_results = image_service.upload_multiple_input_images(
                    reference_images, 
                    original_image.project
                )
                # La primera imagen es la original, luego las referencias
                input_images = [{'gcs_path': config['input_image_gcs_path']}]
                input_images.extend(reference_results)
                config['input_images'] = input_images
            
            # Crear nueva imagen
            new_image = image_service.create_image(
                title=title,
                image_type=image_type,
                prompt=prompt,
                config=config,
                created_by=request.user,
                project=original_image.project
            )
            
            # Generar la imagen automáticamente
            task = image_service.generate_image_async(new_image)
            
            messages.success(
                request,
                f'Imagen "{title}" creada y encolada para generación.'
            )
            
            # Redirigir a la nueva imagen
            if new_image.project:
                return redirect('core:project_image_detail', project_uuid=new_image.project.uuid, image_uuid=new_image.uuid)
            else:
                return redirect('core:image_detail', image_uuid=new_image.uuid)
                
        except InsufficientCreditsException as e:
            messages.error(request, str(e))
            return redirect('core:image_edit', image_uuid=image_uuid)
        except RateLimitExceededException as e:
            messages.error(request, str(e))
            return redirect('core:image_edit', image_uuid=image_uuid)
        except (ValidationException, ServiceException) as e:
            messages.error(request, str(e))
            return redirect('core:image_edit', image_uuid=image_uuid)
        except Exception as e:
            logger.error(f'Error al editar imagen: {e}', exc_info=True)
            messages.error(request, f'Error inesperado: {str(e)}')
            return redirect('core:image_edit', image_uuid=image_uuid)


class ImageToVideoView(LoginRequiredMixin, ServiceMixin, View):
    """Vista para crear un video desde una imagen existente"""
    
    def post(self, request, image_uuid):
        """Crea un video desde una imagen"""
        from django.contrib import messages
        from core.ai_services.model_config import get_model_capabilities, get_video_type_from_model_id
        
        original_image = get_object_or_404(Image, uuid=image_uuid)
        video_service = self.get_video_service()
        
        # Verificar permisos
        if original_image.project:
            if not ProjectService.user_has_access(original_image.project, request.user):
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied('No tienes acceso a esta imagen')
        else:
            if not original_image.created_by or original_image.created_by != request.user:
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied('No tienes acceso a esta imagen')
        
        try:
            # Obtener datos del formulario
            prompt = request.POST.get('prompt', '')
            model_id = request.POST.get('model_id', 'veo-3.1-generate-preview')
            duration = request.POST.get('duration')
            aspect_ratio = request.POST.get('aspect_ratio')
            
            if not prompt:
                messages.error(request, 'El prompt es requerido')
                return redirect('core:image_detail', image_uuid=image_uuid)
            
            # Validar que el modelo soporte image-to-video
            capabilities = get_model_capabilities(model_id)
            if not capabilities:
                messages.error(request, f'Modelo {model_id} no encontrado')
                return redirect('core:image_detail', image_uuid=image_uuid)
            
            supports = capabilities.get('supports', {})
            if not supports.get('image_to_video') and not supports.get('references', {}).get('start_image'):
                messages.error(request, f'El modelo {model_id} no soporta image-to-video')
                return redirect('core:image_detail', image_uuid=image_uuid)
            
            # Obtener tipo de video desde model_id
            video_type = get_video_type_from_model_id(model_id)
            if not video_type:
                messages.error(request, f'No se pudo determinar el tipo de video para el modelo {model_id}')
                return redirect('core:image_detail', image_uuid=image_uuid)
            
            # Determinar aspect ratio final
            final_aspect_ratio = aspect_ratio or original_image.aspect_ratio or '16:9'
            
            # Construir configuración del video
            config = {
                'model_id': model_id,
                'aspect_ratio': final_aspect_ratio,
            }
            
            # Duración del formulario o por defecto según el modelo
            if duration:
                try:
                    config['duration'] = int(duration)
                except (ValueError, TypeError):
                    # Si no se puede convertir, usar valor por defecto del modelo
                    duration_config = supports.get('duration', {})
                    if duration_config.get('fixed'):
                        config['duration'] = duration_config['fixed']
                    elif duration_config.get('options'):
                        config['duration'] = duration_config['options'][0]
                    elif duration_config.get('min'):
                        config['duration'] = duration_config['min']
                    else:
                        config['duration'] = 8
            else:
                # Usar valor por defecto del modelo (fallback si no viene del formulario)
                duration_config = supports.get('duration', {})
                if duration_config.get('fixed'):
                    config['duration'] = duration_config['fixed']
                elif duration_config.get('options'):
                    config['duration'] = duration_config['options'][0]
                elif duration_config.get('min'):
                    config['duration'] = duration_config['min']
                else:
                    config['duration'] = 8
            
            # Configurar imagen de entrada según el tipo de video
            if video_type == 'gemini_veo':
                # Veo usa input_image_gcs_uri
                if original_image.gcs_path:
                    config['input_image_gcs_uri'] = original_image.gcs_path
                    config['input_image_mime_type'] = 'image/png'  # Por defecto PNG
                else:
                    messages.error(request, 'La imagen original no tiene archivo disponible')
                    return redirect('core:image_detail', image_uuid=image_uuid)
            elif video_type == 'sora':
                # Sora usa input_reference_gcs_path
                # Redimensionar y subir la imagen a GCS ANTES de crear el video
                if original_image.gcs_path:
                    from core.storage.gcs import gcs_storage
                    from PIL import Image as PILImage
                    from io import BytesIO
                    try:
                        # Mapear aspect ratio a tamaño de Sora
                        size_map = {
                            '16:9': (1280, 720),
                            '9:16': (720, 1280),
                            '1:1': (1024, 1024),
                        }
                        target_size = size_map.get(final_aspect_ratio, (1280, 720))
                        
                        # Descargar imagen desde GCS
                        blob_name = original_image.gcs_path.replace(f"gs://{settings.GCS_BUCKET_NAME}/", "")
                        blob = gcs_storage.bucket.blob(blob_name)
                        image_data = blob.download_as_bytes()
                        
                        # Redimensionar imagen al tamaño requerido por Sora
                        pil_image = PILImage.open(BytesIO(image_data))
                        original_size = pil_image.size
                        
                        # Redimensionar manteniendo aspect ratio y luego recortar/rellenar si es necesario
                        pil_image = pil_image.resize(target_size, PILImage.Resampling.LANCZOS)
                        
                        # Convertir a RGB si es necesario (Sora requiere RGB)
                        if pil_image.mode in ('RGBA', 'LA', 'P'):
                            rgb_image = PILImage.new('RGB', pil_image.size, (255, 255, 255))
                            if pil_image.mode == 'P':
                                pil_image = pil_image.convert('RGBA')
                            rgb_image.paste(pil_image, mask=pil_image.split()[-1] if pil_image.mode == 'RGBA' else None)
                            pil_image = rgb_image
                        elif pil_image.mode != 'RGB':
                            pil_image = pil_image.convert('RGB')
                        
                        # Guardar imagen redimensionada en bytes
                        output = BytesIO()
                        pil_image.save(output, format='PNG', quality=95)
                        resized_image_data = output.getvalue()
                        
                        logger.info(f"Imagen redimensionada de {original_size} a {target_size} para Sora")
                        
                        # Subir a GCS como input_reference ANTES de crear el video
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        gcs_destination = f"projects/{original_image.project.id if original_image.project else 'none'}/videos/temp_input_reference_{timestamp}.png"
                        gcs_path = gcs_storage.upload_from_bytes(
                            file_content=resized_image_data,
                            destination_path=gcs_destination,
                            content_type='image/png'
                        )
                        
                        # Guardar path en config (no los bytes)
                        config['input_reference_gcs_path'] = gcs_path
                        config['input_reference_mime_type'] = 'image/png'
                        config['use_input_reference'] = True
                    except Exception as e:
                        logger.error(f"Error procesando imagen para Sora: {e}", exc_info=True)
                        messages.error(request, 'Error al procesar la imagen para Sora')
                        return redirect('core:image_detail', image_uuid=image_uuid)
                else:
                    messages.error(request, 'La imagen original no tiene archivo disponible')
                    return redirect('core:image_detail', image_uuid=image_uuid)
            else:
                # Otros servicios (Higgsfield, Kling, etc.)
                if original_image.gcs_path:
                    # Obtener URL firmada para otros servicios
                    from core.storage.gcs import gcs_storage
                    try:
                        image_url = gcs_storage.get_signed_url(original_image.gcs_path, expiration=3600)
                        config['image_url'] = image_url
                    except Exception as e:
                        logger.error(f"Error obteniendo URL firmada: {e}")
                        messages.error(request, 'Error al obtener URL de la imagen')
                        return redirect('core:image_detail', image_uuid=image_uuid)
                else:
                    messages.error(request, 'La imagen original no tiene archivo disponible')
                    return redirect('core:image_detail', image_uuid=image_uuid)
            
            # Duración por defecto según el modelo
            duration_config = supports.get('duration', {})
            if duration_config:
                if duration_config.get('fixed'):
                    config['duration'] = duration_config['fixed']
                elif duration_config.get('options'):
                    config['duration'] = duration_config['options'][0]
                elif duration_config.get('min'):
                    config['duration'] = duration_config['min']
                else:
                    config['duration'] = 8
            else:
                config['duration'] = 8
            
            # Crear video
            video_title = f"Video desde {original_image.title}"
            new_video = video_service.create_video(
                created_by=request.user,
                project=original_image.project,
                title=video_title,
                video_type=video_type,
                script=prompt,
                config=config
            )
            
            # Para Sora, mover el archivo temporal a la ubicación final del video
            if video_type == 'sora' and config.get('input_reference_gcs_path'):
                from core.storage.gcs import gcs_storage
                try:
                    # Mover de temp a la ubicación final del video
                    old_path = config['input_reference_gcs_path']
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    new_gcs_destination = f"projects/{new_video.project.id if new_video.project else 'none'}/videos/{new_video.id}/input_reference_{timestamp}.png"
                    
                    # Copiar el archivo a la nueva ubicación
                    old_blob_name = old_path.replace(f"gs://{settings.GCS_BUCKET_NAME}/", "")
                    new_blob_name = new_gcs_destination.replace(f"gs://{settings.GCS_BUCKET_NAME}/", "")
                    
                    old_blob = gcs_storage.bucket.blob(old_blob_name)
                    new_blob = gcs_storage.bucket.blob(new_blob_name)
                    new_blob.upload_from_string(old_blob.download_as_bytes(), content_type='image/png')
                    
                    # Actualizar config con la nueva ruta
                    new_gcs_path = f"gs://{settings.GCS_BUCKET_NAME}/{new_gcs_destination}"
                    config['input_reference_gcs_path'] = new_gcs_path
                    new_video.config = config
                    new_video.save(update_fields=['config'])
                    
                    # Eliminar archivo temporal
                    try:
                        old_blob.delete()
                    except Exception:
                        pass  # Ignorar si no se puede eliminar
                except Exception as e:
                    logger.error(f"Error moviendo input_reference para Sora: {e}")
                    # Continuar de todas formas, el path temporal también funciona
            
            # Generar el video automáticamente
            task = video_service.generate_video_async(new_video)
            
            messages.success(
                request,
                f'Video "{video_title}" creado y encolado para generación.'
            )
            
            # Redirigir al nuevo video
            if new_video.project:
                return redirect('core:project_video_detail', project_uuid=new_video.project.uuid, video_uuid=new_video.uuid)
            else:
                return redirect('core:video_detail', video_uuid=new_video.uuid)
                
        except InsufficientCreditsException as e:
            messages.error(request, str(e))
            return redirect('core:image_detail', image_uuid=image_uuid)
        except RateLimitExceededException as e:
            messages.error(request, str(e))
            return redirect('core:image_detail', image_uuid=image_uuid)
        except (ValidationException, ServiceException) as e:
            messages.error(request, str(e))
            return redirect('core:image_detail', image_uuid=image_uuid)
        except Exception as e:
            logger.error(f'Error al crear video desde imagen: {e}', exc_info=True)
            messages.error(request, f'Error inesperado: {str(e)}')
            return redirect('core:image_detail', image_uuid=image_uuid)


class ImageUpscaleView(LoginRequiredMixin, ServiceMixin, View):
    """View para escalar imágenes usando Vertex AI Imagen Upscale"""
    
    def post(self, request, image_uuid):
        """
        Escala una imagen usando Vertex AI Imagen Upscale
        
        Args:
            image_uuid: UUID de la imagen a escalar
        """
        from core.models import Image
        from core.services import ImageService
        from django.contrib import messages
        
        try:
            # Obtener imagen
            original_image = Image.objects.get(uuid=image_uuid)
            
            # Verificar permisos
            if original_image.project:
                if not ProjectService.user_has_access(original_image.project, request.user):
                    from django.core.exceptions import PermissionDenied
                    raise PermissionDenied('No tienes acceso a esta imagen')
            else:
                if not original_image.created_by or original_image.created_by != request.user:
                    from django.core.exceptions import PermissionDenied
                    raise PermissionDenied('No tienes acceso a esta imagen')
            
            # Verificar que la imagen tenga archivo
            if not original_image.gcs_path:
                messages.error(request, 'La imagen no tiene archivo disponible para escalar')
                return redirect('core:image_detail', image_uuid=image_uuid)
            
            # Obtener parámetros del formulario
            upscale_factor = request.POST.get('upscale_factor', 'x4')
            output_mime_type = request.POST.get('output_mime_type', 'image/png')
            
            # Validar upscale_factor
            if upscale_factor not in ['x2', 'x3', 'x4']:
                messages.error(request, 'Factor de escalado inválido. Debe ser x2, x3 o x4')
                return redirect('core:image_detail', image_uuid=image_uuid)
            
            # Validar output_mime_type
            valid_mime_types = ['image/png', 'image/jpeg']
            if output_mime_type not in valid_mime_types:
                messages.error(request, f'Formato de salida inválido. Debe ser uno de: {", ".join(valid_mime_types)}')
                return redirect('core:image_detail', image_uuid=image_uuid)
            
            # Encolar upscale de forma asíncrona
            image_service = ImageService()
            task = image_service.upscale_image_async(
                original_image=original_image,
                upscale_factor=upscale_factor,
                output_mime_type=output_mime_type
            )
            
            messages.success(
                request,
                f'Upscale de imagen encolado ({upscale_factor}). La nueva imagen se generará en breve y aparecerá en tu biblioteca.'
            )
            
            return redirect('core:image_detail', image_uuid=image_uuid)
        
        except Image.DoesNotExist:
            messages.error(request, 'Imagen no encontrada')
            return redirect('core:image_list')
        except Exception as e:
            logger.error(f"Error al escalar imagen: {e}", exc_info=True)
            messages.error(request, f'Error al escalar imagen: {str(e)}')
            return redirect('core:image_detail', image_uuid=image_uuid)


class ImageRemoveBackgroundView(LoginRequiredMixin, ServiceMixin, View):
    """Vista para encolar una tarea de remoción de fondo usando rembg + BiRefNet"""
    
    def post(self, request, image_uuid):
        """
        Encola una tarea asíncrona para remover el fondo de una imagen
        Crea la imagen de procesamiento inmediatamente para que aparezca en librería
        
        Args:
            image_uuid: UUID de la imagen a procesar
        
        Returns:
            JsonResponse con { success, task_id, message, new_image_uuid }
        """
        # Obtener imagen original
        image = get_object_or_404(Image, uuid=image_uuid)
        
        # Verificar permisos
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Debes estar autenticado'}, status=401)
        
        if image.project:
            if not ProjectService.user_has_access(image.project, request.user):
                return JsonResponse({'error': 'No tienes acceso a esta imagen'}, status=403)
        else:
            if image.created_by != request.user:
                return JsonResponse({'error': 'No tienes acceso a esta imagen'}, status=403)
        
        # Validar que imagen esté completada y tenga GCS path
        if image.status != 'completed' or not image.gcs_path:
            return JsonResponse({
                'error': 'La imagen debe estar completada y disponible para procesar'
            }, status=400)
        
        try:
            # Crear la nueva imagen con status='processing' INMEDIATAMENTE para que aparezca en la librería
            new_image = Image.objects.create(
                title=f"{image.title} (Sin Fondo)",
                type='text_to_image',
                prompt= image.prompt if image.prompt else "Versión sin fondo",
                created_by=image.created_by,
                project=image.project,
                width=image.width,
                height=image.height,
                status='processing'  # Aparecerá en la librería con animación
            )
            logger.info(f"Imagen de procesamiento creada: {new_image.uuid}")
            
            # Encolar tarea de procesamiento
            logger.info(f"Encolando tarea de remove-bg para imagen {image_uuid} -> {new_image.uuid}")
            remove_bg_task = get_remove_image_background_task()
            task = remove_bg_task.delay(
                str(image_uuid),
                str(new_image.uuid)  # Pasar UUID de imagen destino
            )
            
            logger.info(f"Tarea de remove-bg encolada: task_id={task.id}, image_uuid={image_uuid}, new_image_uuid={new_image.uuid}")
            
            return JsonResponse({
                'success': True,
                'task_id': task.id,
                'message': '✨ Quitando fondo de la imagen...',
                'new_image_uuid': str(new_image.uuid)
            })
            
        except Exception as e:
            logger.error(f'Error encolando remove-bg task: {e}', exc_info=True)
            return JsonResponse({
                'error': f'Error al encolar tarea: {str(e)}'
            }, status=500)


# ====================
# AUDIO VIEWS
# ====================

class AudioLibraryView(SidebarProjectsMixin, BreadcrumbMixin, ServiceMixin, HeyGenPreloadMixin, View):
    """Vista unificada para creación y biblioteca de audios"""
    template_name = 'creation/base_creation.html'
    
    def get_project(self):
        """Obtener proyecto del contexto (opcional)"""
        project_uuid = self.kwargs.get('project_uuid')
        if project_uuid:
            return get_object_or_404(Project, uuid=project_uuid)
        return None
    
    def get(self, request, *args, **kwargs):
        from django.db.models import Q
        
        project = self.get_project()
        user = request.user
        
        # Calcular conteo de audios
        if project:
            audio_count = Audio.objects.filter(project=project).count()
        else:
            user_projects = ProjectService.get_user_projects(user)
            user_project_ids = [p.id for p in user_projects]
            base_filter = Q(project_id__in=user_project_ids) | Q(project__isnull=True, created_by=user)
            audio_count = Audio.objects.filter(base_filter).count()
        
        context = {
            'project': project,
            'active_tab': 'audio',
            'breadcrumbs': self.get_breadcrumbs(),
            'projects': ProjectService.get_user_projects(request.user),
            'items_count': audio_count,
        }
        
        if project:
            context['user_role'] = project.get_user_role(request.user)
            context['project_owner'] = project.owner
            context['project_members'] = project.members.select_related('user').all()
        
        return render(request, self.template_name, context)
    
    def get_breadcrumbs(self):
        project = self.get_project()
        if project:
            return [
                {
                    'label': project.name, 
                    'url': reverse('core:project_overview', args=[project.uuid])
                },
                {'label': 'Audios', 'url': None}
            ]
        return [
            {'label': 'Audios', 'url': None}
        ]


class AudioDetailView(SidebarProjectsMixin, BreadcrumbMixin, ServiceMixin, DetailView):
    """Detalle de un audio - usa el layout de creación unificado"""
    model = Audio
    template_name = 'creation/base_creation.html'
    context_object_name = 'audio'
    
    def get_object(self, queryset=None):
        """Buscar audio por UUID"""
        if queryset is None:
            queryset = self.get_queryset()
        audio_uuid = self.kwargs.get('audio_uuid')
        return get_object_or_404(queryset, uuid=audio_uuid)
    
    def get_project(self):
        """Obtener proyecto de la URL o del objeto"""
        project_uuid = self.kwargs.get('project_uuid')
        if project_uuid:
            return get_object_or_404(Project, uuid=project_uuid)
        return self.object.project
    
    def get_breadcrumbs(self):
        project = self.get_project()
        breadcrumbs = []
        if project:
            breadcrumbs.append({
                'label': project.name, 
                'url': reverse('core:project_overview', args=[project.uuid])
            })
            breadcrumbs.append({
                'label': 'Audios', 
                'url': reverse('core:project_audios_library', args=[project.uuid])
            })
        else:
            breadcrumbs.append({'label': 'Audios', 'url': reverse('core:audio_library')})
        breadcrumbs.append({'label': self.object.title, 'url': None})
        return breadcrumbs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_project()
        context['active_tab'] = 'audio'
        context['initial_item_type'] = 'audio'
        context['initial_item_id'] = str(self.object.uuid)
        
        # Obtener información del modelo usado
        model_id = self.object.model_id or 'elevenlabs'  # Default a elevenlabs si no hay model_id
        model_info = get_model_info_for_item('audio', model_key=model_id)
        context['model_info'] = model_info
        if project:
            context['project'] = project
            context['user_role'] = project.get_user_role(self.request.user)
            context['project_owner'] = project.owner
            context['project_members'] = project.members.select_related('user').all()
        return context


class AudioCreateView(SidebarProjectsMixin, BreadcrumbMixin, ServiceMixin, FormView):
    """Crear nuevo audio"""
    template_name = 'audios/create.html'
    form_class = AudioForm
    
    def get_project(self):
        """Obtener proyecto del contexto (opcional)"""
        project_uuid = self.kwargs.get('project_uuid')
        if project_uuid:
            return get_object_or_404(Project, uuid=project_uuid)
        return None
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_project()
        if project:
            context['project'] = project
            context['user_role'] = project.get_user_role(self.request.user)
            context['project_owner'] = project.owner
            context['project_members'] = project.members.select_related('user').all()
            context.setdefault('active_tab', 'audios')
        
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
                    'url': reverse('core:project_detail', args=[project.uuid])
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
            
            # Encolar generación de audio automáticamente después de crear
            try:
                task = audio_service.generate_audio_async(audio)
                messages.success(request, f'Audio "{title}" creado y encolado para generación.')
            except (ValidationException, ServiceException) as e:
                messages.warning(request, f'Audio "{title}" creado, pero hubo un error al encolar la generación: {str(e)}')
            except Exception as e:
                messages.warning(request, f'Audio "{title}" creado, pero hubo un error inesperado al generarlo: {str(e)}')
            
            return redirect('core:audio_detail', audio_uuid=audio.uuid)
            
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
        project_uuid = self.kwargs['project_uuid']
        return get_object_or_404(Project, uuid=project_uuid)
    
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
            
            # Encolar generación de audio automáticamente después de crear
            try:
                task = audio_service.generate_audio_async(audio)
                messages.success(request, f'Audio "{title}" creado y encolado para generación.')
            except (ValidationException, ServiceException) as e:
                messages.warning(request, f'Audio "{title}" creado, pero hubo un error al encolar la generación: {str(e)}')
            except Exception as e:
                messages.warning(request, f'Audio "{title}" creado, pero hubo un error inesperado al generarlo: {str(e)}')
            
            return redirect('core:audio_detail', audio_uuid=audio.uuid)
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
    
    def get_object(self, queryset=None):
        """Buscar audio por UUID"""
        if queryset is None:
            queryset = self.get_queryset()
        audio_uuid = self.kwargs.get('audio_uuid')
        return get_object_or_404(queryset, uuid=audio_uuid)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['delete_url'] = reverse('core:audio_delete', args=[self.object.pk])
        context['detail_url'] = reverse('core:audio_detail', args=[self.object.pk])
        return context
    
    def get_success_url(self):
        if self.object.project:
            return reverse('core:project_detail', kwargs={'project_uuid': self.object.project.uuid})
        return reverse('core:dashboard')
    
    def get_breadcrumbs(self):
        breadcrumbs = []
        if self.object.project:
            breadcrumbs.append({
                'label': self.object.project.name, 
                'url': reverse('core:project_detail', args=[self.object.project.uuid])
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
        """Override para eliminar archivo de GCS y notificaciones relacionadas"""
        self.object = self.get_object()
        success_url = self.get_success_url()
        audio_uuid = str(self.object.uuid)
        audio_title = self.object.title
        
        # Eliminar notificaciones relacionadas con este audio
        try:
            from .models import Notification
            Notification.objects.filter(
                metadata__item_uuid=audio_uuid,
                metadata__item_type='audio'
            ).delete()
        except Exception as e:
            logger.error(f"Error al eliminar notificaciones: {e}")
        
        # Eliminar de GCS si existe
        if self.object.gcs_path:
            try:
                from .storage.gcs import gcs_storage
                gcs_storage.delete_file(self.object.gcs_path)
            except Exception as e:
                logger.error(f"Error al eliminar archivo: {e}")
        
        self.object.delete()
        
        messages.success(request, f'Audio "{audio_title}" eliminado')
        return redirect(success_url)


# ====================
# AUDIO ACTIONS
# ====================

class AudioGenerateView(ServiceMixin, View):
    """Generar audio usando ElevenLabs API"""
    
    def post(self, request, audio_uuid):
        audio = get_object_or_404(Audio, uuid=audio_uuid)
        audio_service = self.get_audio_service()
        
        try:
            task = audio_service.generate_audio_async(audio)
            messages.success(
                request, 
                'Audio encolado para generación.'
            )
        except InsufficientCreditsException as e:
            messages.error(request, str(e))
        except RateLimitExceededException as e:
            messages.error(request, str(e))
        except (ValidationException, ServiceException) as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error inesperado: {str(e)}')
        
        return redirect('core:audio_detail', audio_uuid=audio.uuid)


# ====================
# VISTAS PARCIALES HTMX
# ====================

class VideoStatusPartialView(View):
    """Vista parcial para actualizar estado de video con HTMX"""
    
    def get(self, request, video_uuid):
        from django.template.loader import render_to_string
        from django.http import HttpResponse
        from .services import VideoService
        
        video = get_object_or_404(Video, uuid=video_uuid)
        
        # Siempre consultar estado si el video está procesando y tiene external_id
        if video.status == 'processing':
            if video.external_id:
                try:
                    video_service = VideoService()
                    
                    # Log del polling ANTES de consultar
                    logger.info(f"=== POLLING VIDEO {video.uuid} ===")
                    logger.info(f"Estado actual ANTES: {video.status}")
                    logger.info(f"External ID: {video.external_id}")
                    logger.info(f"Timestamp: {timezone.now()}")
                    
                    status_data = video_service.check_video_status(video)
                    
                    # Log del polling DESPUÉS de consultar
                    video.refresh_from_db()
                    logger.info(f"Estado actual DESPUÉS: {video.status}")
                    logger.info(f"Estado externo: {status_data.get('status', 'unknown')}")
                    
                    # Refrescar el objeto desde la BD para obtener el estado actualizado
                    video.refresh_from_db()
                    
                    # Si el video está completado pero tiene créditos pendientes, intentar cobrar de nuevo
                    if video.status == 'completed' and video.created_by:
                        if video.metadata.get('credits_charge_pending') and not video.metadata.get('credits_charged'):
                            logger.info(f"Video {video.uuid} tiene créditos pendientes. Intentando cobrar de nuevo.")
                            try:
                                from core.services.credits import CreditService
                                CreditService.deduct_credits_for_video(video.created_by, video)
                                # Si el cobro fue exitoso, limpiar el flag de pendiente
                                video.refresh_from_db()
                                if video.metadata.get('credits_charged'):
                                    video.metadata.pop('credits_charge_pending', None)
                                    video.metadata.pop('credits_charge_error', None)
                                    video.save(update_fields=['metadata'])
                                    logger.info(f"✓ Créditos cobrados exitosamente para video {video.uuid}")
                            except Exception as e:
                                logger.warning(f"No se pudieron cobrar créditos pendientes para video {video.uuid}: {e}")
                    
                except Exception as e:
                    logger.error(f"Error al consultar estado del video {video.uuid}: {e}")
            else:
                # Video procesando pero sin external_id aún - refrescar desde BD por si acaso
                video.refresh_from_db()
        
        # Determinar qué template usar según el contexto
        # Si viene de la lista, usar el badge pequeño, si viene del detalle, usar el completo
        template_name = request.GET.get('template', 'partials/video_status.html')
        if template_name == 'badge':
            template_name = 'partials/video_status_badge.html'
        else:
            template_name = 'partials/video_status.html'
        
        html = render_to_string(template_name, {'video': video})
        
        # Si el video cambió de estado, disparar evento para recargar items en la lista
        if video.status in ['completed', 'error']:
            # Añadir script para recargar items si estamos en la lista
            html += f'''
            <script>
                // Disparar evento para recargar items en la lista
                if (window.dispatchEvent) {{
                    window.dispatchEvent(new CustomEvent('video-status-changed', {{
                        detail: {{ videoId: {video.id}, status: '{video.status}' }}
                    }}));
                }}
            </script>
            '''
        
        return HttpResponse(html)


class ImageStatusPartialView(View):
    """Vista parcial para actualizar estado de imagen con HTMX"""
    
    def get(self, request, image_uuid):
        from django.template.loader import render_to_string
        from django.http import HttpResponse
        image = get_object_or_404(Image, uuid=image_uuid)
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
        breadcrumbs = []
        
        # Solo agregar proyecto si existe
        if self.object.project:
            breadcrumbs.append({
                'label': self.object.project.name, 
                'url': reverse('core:project_detail', args=[self.object.project.uuid])
            })
        
        breadcrumbs.append({'label': self.object.title, 'url': None})
        return breadcrumbs


class ScriptCreateView(SidebarProjectsMixin, BreadcrumbMixin, ServiceMixin, FormView):
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
        project_uuid = self.kwargs.get('project_uuid')
        if project_uuid:
            return get_object_or_404(Project, uuid=project_uuid)
        return None
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_project()
        if project:
            context['project'] = project
            context['user_role'] = project.get_user_role(self.request.user)
            context['project_owner'] = project.owner
            context['project_members'] = project.members.select_related('user').all()
            context.setdefault('active_tab', 'scripts')
        return context
    
    def get_breadcrumbs(self):
        project = self.get_project()
        if project:
            return [
                {
                    'label': project.name, 
                    'url': reverse('core:project_detail', args=[project.uuid])
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
        desired_duration_min = request.POST.get('desired_duration_min', '1')
        desired_duration_sec = request.POST.get('desired_duration_sec', '0')
        
        # Validaciones básicas
        if not all([title, original_script]):
            messages.error(request, 'Todos los campos son requeridos')
            return self.get(request, *args, **kwargs)
        
        try:
            duration_min_int = int(desired_duration_min) if desired_duration_min else 0
            duration_sec_int = int(desired_duration_sec) if desired_duration_sec else 0
            
            # Convertir a minutos decimales (ej: 1 min 30 seg = 1.5 min)
            desired_duration_min_decimal = duration_min_int + (duration_sec_int / 60.0)
            
            # Validar que la duración sea válida
            if desired_duration_min_decimal <= 0:
                messages.error(request, 'La duración debe ser mayor a 0')
                return self.get(request, *args, **kwargs)
            
            # Crear guión
            script = Script.objects.create(
                project=project,
                title=title,
                original_script=original_script,
                desired_duration_min=desired_duration_min_decimal,
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
        project_uuid = self.kwargs['project_uuid']
        return get_object_or_404(Project, uuid=project_uuid)
    
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
                status='pending',
                created_by=request.user  # Asignar usuario para poder cobrar créditos
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
            return reverse('core:project_detail', kwargs={'project_uuid': self.object.project.uuid})
        return reverse('core:dashboard')
    
    def get_breadcrumbs(self):
        breadcrumbs = []
        if self.object.project:
            breadcrumbs.append({
                'label': self.object.project.name, 
                'url': reverse('core:project_detail', args=[self.object.project.uuid])
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

def redirect_to_agent_create(request, project_uuid):
    """Redirigir /projects/<uuid>/agent/ a /projects/<uuid>/agent/create/"""
    return redirect('core:agent_create', project_uuid=project_uuid)

class AgentCreateView(SidebarProjectsMixin, BreadcrumbMixin, View):
    """Paso 1: Crear contenido (script o PDF)"""
    template_name = 'agent/create.html'
    
    def get_project(self):
        project_uuid = self.kwargs['project_uuid']
        return get_object_or_404(Project, uuid=project_uuid)
    
    def get_breadcrumbs(self):
        project = self.get_project()
        return [
            {'label': project.name, 'url': reverse('core:project_detail', args=[project.uuid])},
            {'label': 'Agente de Video', 'url': None}
        ]
    
    def get(self, request, project_uuid):
        project = self.get_project()
        
        context = {
            'project': project,
            'breadcrumbs': self.get_breadcrumbs(),
            'user_role': project.get_user_role(request.user),
            'project_owner': project.owner,
            'project_members': project.members.select_related('user').all()
        }
        context['active_tab'] = 'agent'
        context = self.add_sidebar_projects_to_context(context)
        
        return render(request, self.template_name, context)
    
    def post(self, request, project_uuid):
        """
        Guarda el contenido en sessionStorage (lado cliente) y redirige
        El POST solo valida y redirige a configure
        """
        project = self.get_project()
        
        content_type = request.POST.get('content_type')
        script_content = request.POST.get('script_content')
        
        if not content_type or not script_content:
            messages.error(request, 'Debes proporcionar el contenido del script')
            return redirect('core:agent_create', project_uuid=project.uuid)
        
        # El script se guarda en sessionStorage en el cliente
        # Aquí solo redirigimos a configure
        return redirect('core:agent_configure', project_uuid=project.uuid)


class AgentConfigureView(BreadcrumbMixin, ServiceMixin, View):
    """Paso 2: Procesar con IA y configurar escenas"""
    template_name = 'agent/configure.html'
    
    def get_project(self):
        project_uuid = self.kwargs['project_uuid']
        return get_object_or_404(Project, uuid=project_uuid)
    
    def get_breadcrumbs(self):
        project = self.get_project()
        return [
            {'label': project.name, 'url': reverse('core:project_detail', args=[project.uuid])},
            {'label': 'Configurar Escenas', 'url': None}
        ]
    
    def get(self, request, project_uuid):
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
                
                # Serializar model_preferences para el template
                script_model_preferences_json = json.dumps(script.model_preferences or {})
                
                context = {
                    'project': project,
                    'script': script,
                    'scenes': scenes,
                    'scenes_with_urls': scenes_with_urls,
                    'video_type': script.video_type or 'general',
                    'video_orientation': script.video_orientation or '16:9',
                    'script_model_preferences_json': script_model_preferences_json,
                    'breadcrumbs': self.get_breadcrumbs()
                }
                
                return render(request, self.template_name, context)
                
            except Script.DoesNotExist:
                messages.error(request, 'Script no encontrado')
                return redirect('core:agent_create', project_uuid=project.uuid)
        
        # Si no hay script_id, mostrar pantalla inicial
        context = {
            'project': project,
            'breadcrumbs': self.get_breadcrumbs()
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, project_uuid):
        """
        Recibe el script desde el cliente y lo envía a n8n
        """
        project = self.get_project()
        
        # Obtener datos del POST
        script_title = request.POST.get('title', 'Video con Agente')
        script_content = request.POST.get('script_content')
        desired_duration_min = request.POST.get('desired_duration_min', 5)
        video_type = request.POST.get('video_type', 'general')
        video_format = request.POST.get('video_format', 'educational')
        video_orientation = request.POST.get('video_orientation', '16:9')
        generate_previews = request.POST.get('generate_previews', 'true').lower() == 'true'
        enable_audio = request.POST.get('enable_audio', 'true').lower() == 'true'
        default_voice_id = request.POST.get('default_voice_id', 'pFZP5JQG7iQjIQuC4Bku')
        default_voice_name = request.POST.get('default_voice_name', 'Aria')
        
        # HeyGen defaults
        default_heygen_avatar_id = request.POST.get('default_heygen_avatar_id', '')
        default_heygen_avatar_name = request.POST.get('default_heygen_avatar_name', '')
        default_heygen_voice_id = request.POST.get('default_heygen_voice_id', '')
        default_heygen_voice_name = request.POST.get('default_heygen_voice_name', '')
        
        # Obtener preferencias de modelos (asegurar que sea un diccionario serializable)
        model_preferences = {}
        model_pref_veo = request.POST.get('model_pref_veo')
        model_pref_sora = request.POST.get('model_pref_sora')
        model_pref_heygen = request.POST.get('model_pref_heygen')
        
        if model_pref_veo:
            model_preferences['gemini_veo'] = str(model_pref_veo)  # Asegurar que sea string
        if model_pref_sora:
            model_preferences['sora'] = str(model_pref_sora)  # Asegurar que sea string
        if model_pref_heygen:
            model_preferences['heygen'] = str(model_pref_heygen)  # Asegurar que sea string
        
        # Si hay preferencias, también incluir voz por defecto si está habilitada
        if enable_audio and default_voice_id:
            model_preferences['default_voice_id'] = str(default_voice_id)  # Asegurar que sea string
            model_preferences['default_voice_name'] = str(default_voice_name)  # Asegurar que sea string
        
        # Guardar defaults de HeyGen si están presentes
        if default_heygen_avatar_id:
            model_preferences['default_heygen_avatar_id'] = str(default_heygen_avatar_id)
            model_preferences['default_heygen_avatar_name'] = str(default_heygen_avatar_name)
        if default_heygen_voice_id:
            model_preferences['default_heygen_voice_id'] = str(default_heygen_voice_id)
            model_preferences['default_heygen_voice_name'] = str(default_heygen_voice_name)
        
        if not script_content:
            messages.error(request, 'El contenido del script es requerido')
            return redirect('core:agent_create', project_uuid=project.uuid)
        
        try:
            # Crear Script con agent_flow=True
            script = Script.objects.create(
                project=project,
                title=script_title,
                original_script=script_content,
                desired_duration_min=int(desired_duration_min),
                agent_flow=True,  # Marcar como flujo del agente
                video_type=video_type,
                video_format=video_format,  # Guardar formato de video
                video_orientation=video_orientation,
                generate_previews=generate_previews,
                enable_audio=enable_audio,
                default_voice_id=default_voice_id if enable_audio else None,
                default_voice_name=default_voice_name if enable_audio else None,
                model_preferences=model_preferences if model_preferences else {},  # Guardar preferencias
                status='pending',
                created_by=request.user  # Asignar usuario para poder cobrar créditos
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
        project_uuid = self.kwargs['project_uuid']
        return get_object_or_404(Project, uuid=project_uuid)
    
    def get_breadcrumbs(self):
        project = self.get_project()
        return [
            {'label': project.name, 'url': reverse('core:project_detail', args=[project.uuid])},
            {'label': 'Generar Escenas', 'url': None}
        ]
    
    def get(self, request, project_uuid):
        project = self.get_project()
        
        script_id = request.GET.get('script_id')
        
        if not script_id:
            messages.error(request, 'Script ID requerido')
            return redirect('core:agent_create', project_uuid=project.uuid)
        
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
            return redirect('core:agent_create', project_uuid=project.uuid)


class AgentFinalView(BreadcrumbMixin, ServiceMixin, View):
    """Paso 4: Combinar videos y crear video final"""
    template_name = 'agent/final.html'
    
    def get_project(self):
        project_uuid = self.kwargs['project_uuid']
        return get_object_or_404(Project, uuid=project_uuid)
    
    def get_breadcrumbs(self):
        project = self.get_project()
        return [
            {'label': project.name, 'url': reverse('core:project_detail', args=[project.uuid])},
            {'label': 'Video Final', 'url': None}
        ]
    
    def get(self, request, project_uuid):
        project = self.get_project()
        
        script_id = request.GET.get('script_id')
        
        if not script_id:
            messages.error(request, 'Script ID requerido')
            return redirect('core:agent_create', project_uuid=project.uuid)
        
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
            return redirect('core:agent_create', project_uuid=project.uuid)
    
    def post(self, request, project_uuid):
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

            # Detectar qué servicios se usaron en las escenas
            unique_services = set(scene.ai_service for scene in scenes)

            # Determinar el tipo de video final dinámicamente
            if len(unique_services) > 1:
                # Si hay más de un servicio distinto (ej: Veo + Sora), es mixto
                final_video_type = 'mixed'
            elif len(unique_services) == 1:
                # Si todas las escenas usan el mismo servicio, intentamos heredar el tipo
                service = list(unique_services)[0]
                
                # Mapeo de ai_service (Scene) a type (Video)
                if service == 'gemini_veo':
                    final_video_type = 'gemini_veo'
                elif service == 'sora':
                    final_video_type = 'sora'
                elif service in ['heygen_v2', 'heygen_avatar_iv', 'heygen']:
                    final_video_type = 'heygen_avatar_v2'
                else:
                    final_video_type = 'general'
            else:
                final_video_type = 'general'
            
            # Crear objeto Video final
            video = Video.objects.create(
                project=project,
                title=video_title,
                type=final_video_type,  # Tipo genérico, podría ser mixto
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
            
            logger.info(f"✓ Video final creado: {video.id} (UUID: {video.uuid}) para script {script.id}")
            
            return JsonResponse({
                'status': 'success',
                'message': 'Video combinado exitosamente',
                'video_id': video.id,
                'video_uuid': str(video.uuid)  # Añadir UUID para redirección correcta
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
# AGENT STANDALONE VIEWS (sin proyecto)
# ====================

class AgentCreateStandaloneView(SidebarProjectsMixin, BreadcrumbMixin, View):
    """Paso 1: Crear contenido sin proyecto"""
    template_name = 'agent/create.html'
    
    def get_breadcrumbs(self):
        return [
            {'label': 'Agente de Video', 'url': None}
        ]
    
    def get(self, request):
        context = {
            'project': None,  # Sin proyecto
            'breadcrumbs': self.get_breadcrumbs(),
            'user_role': None,
            'project_owner': None,
            'project_members': []
        }
        context = self.add_sidebar_projects_to_context(context)
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        """
        Guarda el contenido en sessionStorage (lado cliente) y redirige
        El POST solo valida y redirige a configure
        """
        content_type = request.POST.get('content_type')
        script_content = request.POST.get('script_content')
        
        if not content_type or not script_content:
            messages.error(request, 'Debes proporcionar el contenido del script')
            return redirect('core:agent_create_standalone')
        
        # El script se guarda en sessionStorage en el cliente
        # Aquí solo redirigimos a configure
        return redirect('core:agent_configure_standalone')


class AgentConfigureStandaloneView(BreadcrumbMixin, ServiceMixin, View):
    """Paso 2: Procesar con IA y configurar escenas (sin proyecto)"""
    template_name = 'agent/configure.html'
    
    def get_breadcrumbs(self):
        return [
            {'label': 'Configurar Escenas', 'url': None}
        ]
    
    def get(self, request):
        """
        Muestra pantalla de "Processing..." 
        Si hay un script_id en la URL, muestra las escenas
        """
        script_id = request.GET.get('script_id')
        
        # Si hay script_id, cargar escenas
        if script_id:
            try:
                # Buscar script sin proyecto (project__isnull=True)
                script = Script.objects.get(
                    id=script_id, 
                    project__isnull=True, 
                    agent_flow=True,
                    created_by=request.user  # Solo scripts del usuario actual
                )
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
                
                # Serializar model_preferences para el template
                script_model_preferences_json = json.dumps(script.model_preferences or {})
                
                context = {
                    'project': None,  # Sin proyecto
                    'script': script,
                    'scenes': scenes,
                    'scenes_with_urls': scenes_with_urls,
                    'video_type': script.video_type or 'general',
                    'video_orientation': script.video_orientation or '16:9',
                    'script_model_preferences_json': script_model_preferences_json,
                    'breadcrumbs': self.get_breadcrumbs()
                }
                
                return render(request, self.template_name, context)
                
            except Script.DoesNotExist:
                messages.error(request, 'Script no encontrado')
                return redirect('core:agent_create_standalone')
        
        # Si no hay script_id, mostrar pantalla inicial
        context = {
            'project': None,  # Sin proyecto
            'breadcrumbs': self.get_breadcrumbs()
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        """
        Recibe el script desde el cliente y lo procesa (sin proyecto)
        """
        # Obtener datos del POST
        script_title = request.POST.get('title', 'Video con Agente')
        script_content = request.POST.get('script_content')
        desired_duration_min = request.POST.get('desired_duration_min', 5)
        video_type = request.POST.get('video_type', 'general')
        video_format = request.POST.get('video_format', 'educational')
        video_orientation = request.POST.get('video_orientation', '16:9')
        generate_previews = request.POST.get('generate_previews', 'true').lower() == 'true'
        enable_audio = request.POST.get('enable_audio', 'true').lower() == 'true'
        default_voice_id = request.POST.get('default_voice_id', 'pFZP5JQG7iQjIQuC4Bku')
        default_voice_name = request.POST.get('default_voice_name', 'Aria')
        
        # HeyGen defaults
        default_heygen_avatar_id = request.POST.get('default_heygen_avatar_id', '')
        default_heygen_avatar_name = request.POST.get('default_heygen_avatar_name', '')
        default_heygen_voice_id = request.POST.get('default_heygen_voice_id', '')
        default_heygen_voice_name = request.POST.get('default_heygen_voice_name', '')
        
        # Obtener preferencias de modelos (asegurar que sea un diccionario serializable)
        model_preferences = {}
        model_pref_veo = request.POST.get('model_pref_veo')
        model_pref_sora = request.POST.get('model_pref_sora')
        model_pref_heygen = request.POST.get('model_pref_heygen')
        
        if model_pref_veo:
            model_preferences['gemini_veo'] = str(model_pref_veo)
        if model_pref_sora:
            model_preferences['sora'] = str(model_pref_sora)
        if model_pref_heygen:
            model_preferences['heygen'] = str(model_pref_heygen)
        
        # Si hay preferencias, también incluir voz por defecto si está habilitada
        if enable_audio and default_voice_id:
            model_preferences['default_voice_id'] = str(default_voice_id)
            model_preferences['default_voice_name'] = str(default_voice_name)
        
        # Guardar defaults de HeyGen si están presentes
        if default_heygen_avatar_id:
            model_preferences['default_heygen_avatar_id'] = str(default_heygen_avatar_id)
            model_preferences['default_heygen_avatar_name'] = str(default_heygen_avatar_name)
        if default_heygen_voice_id:
            model_preferences['default_heygen_voice_id'] = str(default_heygen_voice_id)
            model_preferences['default_heygen_voice_name'] = str(default_heygen_voice_name)
        
        if not script_content:
            messages.error(request, 'El contenido del script es requerido')
            return redirect('core:agent_create_standalone')
        
        try:
            # Crear Script sin proyecto (project=None)
            script = Script.objects.create(
                project=None,  # Sin proyecto
                title=script_title,
                original_script=script_content,
                desired_duration_min=float(desired_duration_min),
                agent_flow=True,
                video_type=video_type,
                video_format=video_format,
                video_orientation=video_orientation,
                generate_previews=generate_previews,
                enable_audio=enable_audio,
                default_voice_id=default_voice_id if enable_audio else None,
                default_voice_name=default_voice_name if enable_audio else None,
                model_preferences=model_preferences if model_preferences else {},
                status='pending',
                created_by=request.user
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
                    # n8n: procesamiento asíncrono
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


class AgentScenesStandaloneView(BreadcrumbMixin, ServiceMixin, View):
    """Paso 3: Generar videos de las escenas (sin proyecto)"""
    template_name = 'agent/scenes.html'
    
    def get_breadcrumbs(self):
        return [
            {'label': 'Generar Escenas', 'url': None}
        ]
    
    def get(self, request):
        script_id = request.GET.get('script_id')
        
        if not script_id:
            messages.error(request, 'Script ID requerido')
            return redirect('core:agent_create_standalone')
        
        try:
            script = Script.objects.get(
                id=script_id, 
                project__isnull=True, 
                agent_flow=True,
                created_by=request.user
            )
            scenes = script.db_scenes.filter(is_included=True).order_by('order')
            
            # Generar URLs firmadas para cada escena
            scenes_with_urls = []
            for scene in scenes:
                scene_data = SceneService().get_scene_with_signed_urls(scene)
                if 'scene' in scene_data and scene_data['scene'].ai_config:
                    scene_data['ai_config_json'] = json.dumps(scene_data['scene'].ai_config)
                else:
                    scene_data['ai_config_json'] = '{}'
                scenes_with_urls.append(scene_data)
            
            context = {
                'project': None,  # Sin proyecto
                'script': script,
                'scenes': scenes,
                'scenes_with_urls': scenes_with_urls,
                'breadcrumbs': self.get_breadcrumbs()
            }
            
            return render(request, self.template_name, context)
            
        except Script.DoesNotExist:
            messages.error(request, 'Script no encontrado')
            return redirect('core:agent_create_standalone')


class AgentFinalStandaloneView(BreadcrumbMixin, ServiceMixin, View):
    """Paso 4: Combinar videos y crear video final (sin proyecto)"""
    template_name = 'agent/final.html'
    
    def get_breadcrumbs(self):
        return [
            {'label': 'Video Final', 'url': None}
        ]
    
    def get(self, request):
        script_id = request.GET.get('script_id')
        
        if not script_id:
            messages.error(request, 'Script ID requerido')
            return redirect('core:agent_create_standalone')
        
        try:
            script = Script.objects.get(
                id=script_id, 
                project__isnull=True, 
                agent_flow=True,
                created_by=request.user
            )
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
                'project': None,  # Sin proyecto
                'script': script,
                'scenes': scenes,
                'scenes_with_urls': scenes_with_urls,
                'breadcrumbs': self.get_breadcrumbs()
            }
            
            return render(request, self.template_name, context)
            
        except Script.DoesNotExist:
            messages.error(request, 'Script no encontrado')
            return redirect('core:agent_create_standalone')
    
    def post(self, request):
        """Combinar videos de escenas con FFmpeg (sin proyecto)"""
        from .services import VideoCompositionService
        from datetime import datetime
        
        script_id = request.POST.get('script_id')
        video_title = request.POST.get('video_title')
        
        if not script_id or not video_title:
            return JsonResponse({
                'status': 'error',
                'message': 'Script ID y título son requeridos'
            }, status=400)
        
        try:
            script = Script.objects.get(
                id=script_id, 
                project__isnull=True, 
                agent_flow=True,
                created_by=request.user
            )
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

            
            # Detectar qué servicios se usaron en las escenas
            unique_services = set(scene.ai_service for scene in scenes)

            # Determinar el tipo de video final dinámicamente
            if len(unique_services) > 1:
                # Si hay más de un servicio distinto (ej: Veo + Sora), es mixto
                final_video_type = 'mixed'
            elif len(unique_services) == 1:
                # Si todas las escenas usan el mismo servicio, intentamos heredar el tipo
                service = list(unique_services)[0]
                
                # Mapeo de ai_service (Scene) a type (Video)
                if service == 'gemini_veo':
                    final_video_type = 'gemini_veo'
                elif service == 'sora':
                    final_video_type = 'sora'
                elif service in ['heygen_v2', 'heygen_avatar_iv', 'heygen']:
                    final_video_type = 'heygen_avatar_v2'
                else:
                    final_video_type = 'general'
            else:
                final_video_type = 'general'
            
            # Crear objeto Video final sin proyecto
            video = Video.objects.create(
                project=None,  # Sin proyecto
                created_by=request.user,
                title=video_title,
                type=final_video_type,
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
            
            logger.info(f"✓ Video final creado: {video.id} (UUID: {video.uuid}) para script {script.id}")
            
            return JsonResponse({
                'status': 'success',
                'message': 'Video combinado exitosamente',
                'video_id': video.id,
                'video_uuid': str(video.uuid)
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
        project_uuid = self.kwargs['project_uuid']
        return get_object_or_404(Project, uuid=project_uuid)
    
    def get_breadcrumbs(self):
        project = self.get_project()
        return [
            {'label': project.name, 'url': reverse('core:project_detail', args=[project.uuid])},
            {'label': 'Asistente IA', 'url': None}
        ]
    
    def get(self, request, project_uuid):
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
    
    def post(self, request, project_uuid):
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
    
    def post(self, request, project_uuid):
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
            
            # Si está completada pero no se han cobrado créditos, cobrarlos ahora
            elif scene.video_status == 'completed' and scene.script.created_by:
                try:
                    from core.services.credits import CreditService
                    # Verificar si ya se cobraron créditos
                    if not scene.metadata.get('credits_charged'):
                        logger.info(f"Escena {scene.scene_id} completada pero sin créditos cobrados. Cobrando ahora...")
                        CreditService.deduct_credits_for_scene_video(scene.script.created_by, scene)
                        scene.refresh_from_db()  # Refrescar después del cobro
                except Exception as e:
                    logger.error(f"Error al verificar/cobrar créditos para escena {scene_id}: {e}")
            
            # Verificar también el audio completado
            if scene.audio_status == 'completed' and scene.script.created_by:
                try:
                    from core.services.credits import CreditService
                    # Verificar si ya se cobraron créditos del audio
                    if not scene.metadata.get('audio_credits_charged'):
                        logger.info(f"Audio de escena {scene.scene_id} completado pero sin créditos cobrados. Cobrando ahora...")
                        # Calcular y cobrar créditos del audio
                        cost = CreditService.estimate_audio_cost(scene.script_text)
                        if cost > 0:
                            CreditService.deduct_credits(
                                user=scene.script.created_by,
                                amount=cost,
                                service_name='elevenlabs',
                                operation_type='audio_generation',
                                resource=scene,
                                metadata={
                                    'character_count': len(scene.script_text),
                                    'duration': scene.audio_duration,
                                    'voice_id': scene.audio_voice_id,
                                }
                            )
                            # Marcar como cobrado en metadata
                            if not scene.metadata:
                                scene.metadata = {}
                            scene.metadata['audio_credits_charged'] = True
                            scene.save(update_fields=['metadata'])
                            scene.refresh_from_db()
                except Exception as e:
                    logger.error(f"Error al verificar/cobrar créditos de audio para escena {scene_id}: {e}")
            
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
            
            # Calcular scene_id único
            base_count = script.db_scenes.count() + 1
            scene_id = f"Escena {base_count}"
            counter = 0
            
            # Verificar si existe y buscar el siguiente libre
            while Scene.objects.filter(script=script, scene_id=scene_id).exists():
                counter += 1
                scene_id = f"Escena {base_count + counter}"
            
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
            
            # Marcar escena como completada usando el método para cobrar créditos
            scene.mark_video_as_completed(gcs_path=gcs_path)
            
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
            
            # Validaciones de tipo y tamaño...
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
            file_ext = os.path.splitext(image_file.name)[1].lower()
            if file_ext not in allowed_extensions:
                return JsonResponse({'status': 'error', 'message': 'Formato no soportado'}, status=400)
            
            if image_file.size > 10 * 1024 * 1024:
                return JsonResponse({'status': 'error', 'message': 'Imagen demasiado grande'}, status=400)
            
            # Subir a GCS
            from .storage.gcs import gcs_storage
            from datetime import datetime
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_filename = os.path.basename(image_file.name)
            
            # Manejo de Standalone vs Proyecto
            project_id_str = scene.project.id if scene.project else 'standalone'
            gcs_destination = f"projects/{project_id_str}/scenes/{scene.id}/custom_preview_{timestamp}_{safe_filename}"
            
            logger.info(f"Subiendo imagen personalizada a GCS: {safe_filename}")
            gcs_path = gcs_storage.upload_django_file(image_file, gcs_destination)
            
            # --- CORRECCIÓN AQUÍ ---
            # 1. Guardar la ruta en el campo correcto (asegúrate que tu modelo usa preview_image_gcs_path)
            scene.preview_image_gcs_path = gcs_path
            
            # 2. IMPORTANTE: Marcar el estado como completado para que el HTML lo muestre
            scene.preview_image_status = 'completed'
            
            # 3. Opcional: Marcar la fuente para mostrar el badge "Subida"
            scene.image_source = 'user_upload'
            
            scene.save()
            # -----------------------
            
            logger.info(f"✓ Imagen personalizada subida y activada para escena {scene.id}")
            
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
            
            # Actualizar is_included si viene (para selección de escenas)
            if 'is_included' in data:
                scene.is_included = bool(data['is_included'])
                logger.info(f"  is_included actualizado a: {scene.is_included}")
            
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
                project_id_str = scene.project.id if scene.project else 'standalone'
                gcs_path = f"projects/{project_id_str}/scenes/{scene.id}/preview_freepik.jpg"   
                             
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
        has_credits_access = request.user.has_perm('core.view_credittransaction')

        # Superuser shortcut
        if request.user.is_superuser:
            has_admin_access = True
            has_create_access = True
            has_credits_access = True
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
        if not (has_admin_access or has_create_access or has_credits_access):
            messages.error(request, 'No tienes permiso para acceder a esta página.')
            return redirect(self.login_url)

        # Set access flags for template and data loading
        request.has_credits_access = has_credits_access
        request.has_admin_access = has_admin_access
        request.has_create_access = has_create_access
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        # Determine access flags for template and data loading (same logic as dispatch)
        has_change = request.user.has_perm('auth.change_user')
        has_delete = request.user.has_perm('auth.delete_user')
        has_view = request.user.has_perm('auth.view_user')
        has_add = request.user.has_perm('auth.add_user')
        has_credits_access = request.user.has_perm('core.view_credittransaction')

        if request.user.is_superuser:
            has_admin_access = True
            has_create_access = True
            has_credits_access = True
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
        users = User.objects.prefetch_related('groups').all() if has_admin_access else []
        
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
            'has_credits_access': has_credits_access,
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
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-\[\]\\;/+=]', password):
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

                # =========================
                # Créditos iniciales
                # =========================
                initial_credits = request.POST.get('initial_credits', 0)
                monthly_limit = request.POST.get('monthly_limit', 0)

                credits = CreditService.get_or_create_user_credits(user)

                try:
                    initial_credits = int(initial_credits)
                    if initial_credits > 0:
                        credits.credits = initial_credits
                except (TypeError, ValueError):
                    initial_credits = 0

                try:
                    monthly_limit = int(monthly_limit)
                    if monthly_limit >= 0:
                        credits.monthly_limit = monthly_limit
                except (TypeError, ValueError):
                    monthly_limit = 0

                credits.save()

                # Registrar transacción de créditos iniciales
                if initial_credits > 0:
                    CreditTransaction.objects.create(
                        user=user,
                        transaction_type='add',
                        amount=initial_credits,
                        balance_before=0,
                        balance_after=initial_credits,
                        description='Créditos iniciales al crear usuario'
                    )

                # Registrar límite mensual inicial
                if monthly_limit > 0:
                    CreditTransaction.objects.create(
                        user=user,
                        transaction_type='limit_change',
                        amount=0,
                        balance_before=credits.credits,
                        balance_after=credits.credits,
                        description=f'Límite mensual inicial: {monthly_limit}'
                    )

                # Send activation email
                try:
                    from django.core.mail import EmailMultiAlternatives
                    context = {'user': user, 'activation_url': activation_url}
                    subject = 'Activa tu cuenta en Atenea'
                    text_content = render_to_string('users/activation_email.txt', context)
                    html_content = render_to_string('users/activation_email.html', context)
                    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
                    
                    email = EmailMultiAlternatives(
                        subject,
                        text_content,
                        from_email,
                        [user.email]
                    )
                    email.attach_alternative(html_content, "text/html")
                    email.send(fail_silently=False)
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


class ActivateAccountView(View):
    """
    Vista de activación de cuenta: el usuario sigue el enlace del correo,
    establece su contraseña y se activa la cuenta.
    Soporta extra_context para ocultar sidebar/header.
    """
    template_name = 'users/activate_account.html'
    invalid_template_name = 'users/activation_invalid.html'
    extra_context = None

    def get_user(self, uidb64):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            return User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return None

    def get_context_data(self, **kwargs):
        context = {}
        if hasattr(self, 'extra_context') and self.extra_context:
            context.update(self.extra_context)
        context.update(kwargs)
        return context



    def get(self, request, uidb64, token):
        user = self.get_user(uidb64)

        if user is None or not default_token_generator.check_token(user, token):
            return render(request, self.invalid_template_name, {
                'user_obj': None,
                'message': 'El enlace de activación no es válido o ha expirado.'
            })

        if user.is_active:
            messages.info(request, 'Tu cuenta ya está activa. Puedes iniciar sesión.')
            return redirect('core:login')

        if request.user.is_authenticated and request.user.pk != user.pk:
            logout(request)
            messages.info(request, 'La sesión anterior se ha cerrado para continuar con la activación de la cuenta.')

        logger.info(f"Activation GET for uid={uidb64} user_id={getattr(user, 'pk', None)}")
        form = ActivationSetPasswordForm(user=user)
        
        context = self.get_context_data(form=form, user=user)
        return render(request, self.template_name, context)

    def post(self, request, uidb64, token):
        user = self.get_user(uidb64)

        if user is None or not default_token_generator.check_token(user, token):
            return render(request, self.invalid_template_name, {
                'user_obj': None,
                'message': 'El enlace de activación no es válido o ha expirado.'
            })

        if user.is_active:
            messages.info(request, 'Tu cuenta ya está activa. Puedes iniciar sesión.')
            return redirect('core:login')

        logger.info(f"Activation POST received for uid={uidb64} user_id={getattr(user, 'pk', None)}")
        form = ActivationSetPasswordForm(user=user, data=request.POST)

        if form.is_valid():
            try:
                form.save()
                user.is_active = True
                user.save(update_fields=["is_active"])
                user.refresh_from_db()

                if user.is_active:
                    messages.success(request, "Tu cuenta ha sido activada. Ahora puedes iniciar sesión.")
                else:
                    messages.warning(request, "Tu contraseña se guardó pero no se pudo activar la cuenta automáticamente. Contacta con el administrador.")

                return redirect("core:login")

            except Exception as e:
                logger.exception(f"Exception during account activation for user {getattr(user, 'pk', None)}: {e}")
                messages.error(request, "Ocurrió un error al activar la cuenta. Por favor intenta de nuevo o contacta con el administrador.")
        else:
            for field, errors in form.errors.items():
                messages.error(request, errors)
                break
        
        context = self.get_context_data(form=form, user=user)
        return render(request, self.template_name, context)

class AddCreditsView(View):
    def post(self, request):
        user_id = request.POST.get("user_id")
        amount = request.POST.get("amount")
        description = request.POST.get("description") or ""

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({"error": "Usuario no encontrado"}, status=404)

        try:
            amount = float(amount)
        except:
            return JsonResponse({"error": "Cantidad inválida"}, status=400)

        if amount == 0:
            return JsonResponse({"error": "La cantidad no puede ser 0"}, status=400)

        description = description or f"Ajuste de créditos: {amount}"

        try:
            credits_before = CreditService.get_or_create_user_credits(user).credits

            credits = CreditService.add_credits(
                user=user,
                amount=amount,
                description=description,
                transaction_type="adjustment"
            )

            return JsonResponse({
                "success": True,
                "saldo_anterior": credits_before,
                "saldo_actual": credits.credits
            })

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

class SetMonthlyLimitView(View):
    """
    View para actualizar el límite mensual de créditos de un usuario.
    Espera POST con:
        - username
        - limit
        - description (opcional)
    """

    @method_decorator(csrf_exempt)  # si usas AJAX desde JS
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        username = request.POST.get('username')
        limit = request.POST.get('limit')
        description = request.POST.get('description', '')

        # Validaciones básicas
        if not username or limit is None:
            return JsonResponse({'success': False, 'error': 'Faltan parámetros'}, status=400)

        try:
            limit = int(limit)
            if limit < 0:
                return JsonResponse({'success': False, 'error': 'El límite debe ser >= 0'}, status=400)
        except ValueError:
            return JsonResponse({'success': False, 'error': 'El límite debe ser un número entero'}, status=400)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': f'Usuario "{username}" no encontrado'}, status=404)

        try:
            credits = CreditService.get_or_create_user_credits(user)
            old_limit = credits.monthly_limit

            credits.monthly_limit = limit
            credits.save(update_fields=['monthly_limit', 'updated_at'])

            # ============================
            # Registrar en el historial
            # ============================
            CreditTransaction.objects.create(
                user=user,
                transaction_type='limit_change',  # Debe estar definido en choices
                amount=0,  # No afecta saldo
                balance_before=credits.credits,
                balance_after=credits.credits,
                description=f"Límite mensual cambiado: {old_limit} → {limit}. {description}",
            )

            response = {
                'success': True,
                'username': username,
                'old_limit': old_limit,
                'new_limit': limit,
                'current_usage': credits.current_month_usage,
                'remaining': credits.credits_remaining
            }
            if description:
                response['description'] = description

            return JsonResponse(response)

        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Error al actualizar límite mensual: {str(e)}'}, status=500)
# ====================
# MUSIC VIEWS - ELIMINADAS (usar Audio con type='music')
# ====================


# ====================
# PROJECT INVITATIONS
# ====================

class ProjectInviteView(BreadcrumbMixin, ServiceMixin, View):
    """Vista para invitar usuarios a un proyecto"""
    template_name = 'projects/invite.html'
    
    def get_project(self):
        """Obtener proyecto y verificar permisos"""
        project_uuid = self.kwargs['project_uuid']
        project = ProjectService.get_project_with_videos_by_uuid(project_uuid)
        
        if not ProjectService.user_can_edit(project, self.request.user):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied('No tienes permisos para invitar usuarios a este proyecto')
        
        return project
    
    def get_breadcrumbs(self):
        project = self.get_project()
        return [
            {'label': project.name, 'url': reverse('core:project_detail', args=[project.uuid])},
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
                return redirect('core:project_invitations_partial', project_uuid=project.uuid)
            return redirect('core:project_invitations', project_uuid=project.uuid)
            
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
        project_uuid = self.kwargs['project_uuid']
        project = ProjectService.get_project_with_videos_by_uuid(project_uuid)
        
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
            return redirect('core:project_invitations_partial', project_uuid=project.uuid)
            
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
        project_uuid = self.kwargs['project_uuid']
        project = ProjectService.get_project_with_videos_by_uuid(project_uuid)
        
        if not ProjectService.user_can_edit(project, self.request.user):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied('No tienes permisos para ver las invitaciones de este proyecto')
        
        return project
    
    def get_breadcrumbs(self):
        project = self.get_project()
        return [
            {'label': project.name, 'url': reverse('core:project_detail', args=[project.uuid])},
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
        project_uuid = self.kwargs['project_uuid']
        project = ProjectService.get_project_with_videos_by_uuid(project_uuid)
        
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
            return redirect('core:project_detail', project_uuid=invitation.project.uuid)
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
            return redirect('core:project_invitations', project_uuid=invitation.project.uuid)
        except ProjectInvitation.DoesNotExist:
            return redirect('core:dashboard')


# ====================
# MOVE TO PROJECT VIEWS
# ====================

class MoveToProjectView(View):
    """Vista para mover items sin proyecto a un proyecto"""
    
    def get(self, request, item_type, item_id):
        """Mostrar modal con lista de proyectos"""
        import uuid as uuid_module
        
        # Mapeo de tipos a modelos
        model_map = {
            'video': Video,
            'image': Image,
            'audio': Audio,
            'script': Script
        }
        
        # Tipos que usan UUID
        uuid_types = {'video', 'image', 'audio'}
        
        if item_type not in model_map:
            messages.error(request, 'Tipo de item no válido')
            return redirect('core:dashboard')
        
        # Obtener el item
        try:
            if item_type in uuid_types:
                item_uuid = uuid_module.UUID(item_id)
                item = model_map[item_type].objects.get(uuid=item_uuid, created_by=request.user)
            else:
                item = model_map[item_type].objects.get(id=item_id, created_by=request.user)
        except (ValueError, model_map[item_type].DoesNotExist):
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
        import uuid as uuid_module
        
        # Mapeo de tipos a modelos
        model_map = {
            'video': Video,
            'image': Image,
            'audio': Audio,
            'script': Script
        }
        
        # Tipos que usan UUID
        uuid_types = {'video', 'image', 'audio'}
        
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
            if item_type in uuid_types:
                item_uuid = uuid_module.UUID(item_id)
                item = model_map[item_type].objects.get(uuid=item_uuid, created_by=request.user)
            else:
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
            
            # Usar uuid para video, image, audio; id para el resto
            if item_type in uuid_types:
                return redirect(redirect_map[item_type], **{f'{item_type}_uuid': item.uuid})
            else:
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
            messages.success(request, 'Documentación re-indexada exitosamente desde docs/public/api')
        except Exception as e:
            logger.error(f"Error al re-indexar: {e}", exc_info=True)
            messages.error(request, f'Error al re-indexar: {str(e)}')
        
        return redirect('core:dashboard')


# ====================
# CREATION AGENT (Chat de Creación)
# ====================

class CreationAgentView(LoginRequiredMixin, SidebarProjectsMixin, View):
    """Vista principal del chat de creación"""
    template_name = 'chat/creation_agent.html'
    
    def get(self, request):
        context = {
            'breadcrumbs': [
                {'label': 'Chat de Creación', 'url': None}
            ],
            'projects': ProjectService.get_user_projects(request.user),
        }
        return render(request, self.template_name, context)


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
# CREDITS HISTORIAL
# ====================
class UserCreditsHistoryAPI(View):
    """Devuelve todas las transacciones de un usuario en JSON, incluyendo cambios de límite mensual"""
    
    def get(self, request, user_id):
        # Obtener todas las transacciones del usuario, ordenadas de más reciente a más antigua
        transactions = CreditTransaction.objects.filter(user_id=user_id).order_by('-created_at')

        # Preparar lista de transacciones para JSON
        data = []
        for t in transactions:
            data.append({
                'id': t.id,
                'type': t.get_transaction_type_display(),   # muestra "Créditos sumados", "Créditos restados", "Cambio de límite mensual", etc.
                'amount': float(t.amount),
                'service_name': t.service_name or '',
                'description': t.description or '',
                'created_at': timezone.localtime(t.created_at).strftime("%d/%m/%Y %H:%M"),  # hora local
            })

        return JsonResponse({'transactions': data})

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

        query = request.GET.get('query', '').strip()
        if not query:
            # Si no hay query, usar defaults según el tipo de contenido
            defaults = {
                'image': 'nature',
                'video': 'nature',
                'audio': 'ambient'
            }
            query = defaults.get(content_type, 'nature')
        
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
            
            # Guardar en caché (siempre, para actualizar datos frescos)
            if results:
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
        
        # Eliminar duplicados por UUID usando values() para evitar duplicados en la consulta
        # y luego convertir a lista de diccionarios únicos
        projects_dict = {}
        for p in user_projects.only('id', 'uuid', 'name'):
            if str(p.uuid) not in projects_dict:
                projects_dict[str(p.uuid)] = {'id': p.id, 'uuid': str(p.uuid), 'name': p.name}
        
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
            - resource_id: (opcional) ID del recurso de Freepik para obtener URL oficial
            - source: (opcional) Fuente del video ('freepik', 'pexels', etc.)
        """
        import requests
        from urllib.parse import unquote
        from django.conf import settings
        
        video_url = request.GET.get('url')
        resource_id = request.GET.get('resource_id')
        source = request.GET.get('source', '').lower()
        
        # Si es Freepik y tenemos resource_id, obtener URL oficial de descarga
        if source == 'freepik' and resource_id:
            try:
                from .ai_services.freepik import FreepikClient
                from requests.exceptions import HTTPError
                
                if settings.FREEPIK_API_KEY:
                    client = FreepikClient(api_key=settings.FREEPIK_API_KEY)
                    try:
                        download_info = client.get_download_url(resource_id=resource_id)
                    except HTTPError as e:
                        # Manejar errores específicos de Freepik
                        if e.response.status_code == 403:
                            logger.warning(f"Freepik recurso {resource_id} requiere cuenta Premium")
                            return HttpResponse('Este video requiere cuenta Premium de Freepik', status=403)
                        elif e.response.status_code == 404:
                            logger.warning(f"Freepik recurso {resource_id} no encontrado")
                            return HttpResponse('Video no encontrado en Freepik', status=404)
                        elif e.response.status_code == 429:
                            logger.warning(f"Límite de API de Freepik alcanzado")
                            return HttpResponse('Límite de API de Freepik alcanzado', status=429)
                        else:
                            raise
                    
                    # Extraer URL de video de la respuesta
                    video_url = None
                    if 'data' in download_info:
                        data = download_info['data']
                        video_url = (
                            data.get('url') or 
                            data.get('download_url') or 
                            data.get('video_url') or
                            data.get('link') or
                            data.get('href')
                        )
                        if isinstance(data, str):
                            video_url = data
                    
                    if not video_url:
                        video_url = (
                            download_info.get('url') or 
                            download_info.get('download_url') or 
                            download_info.get('video_url') or
                            download_info.get('link')
                        )
                    
                    if video_url:
                        # Verificar que la URL obtenida sea realmente un video, no una imagen
                        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg']
                        if any(video_url.lower().endswith(ext) for ext in image_extensions):
                            logger.warning(f"Freepik devolvió URL de imagen en lugar de video: {video_url[:100]}")
                            return HttpResponse('Freepik devolvió una imagen en lugar de un video', status=400)
                        logger.info(f"URL de video de Freepik obtenida: {video_url[:100]}...")
                    else:
                        logger.warning(f"No se encontró URL de video en respuesta de Freepik: {download_info}")
                        return HttpResponse('No se pudo obtener la URL del video de Freepik', status=404)
            except HTTPError:
                # Ya manejado arriba
                raise
            except Exception as e:
                logger.error(f"Error obteniendo URL de video de Freepik: {e}", exc_info=True)
                return HttpResponse(f'Error al obtener URL de video: {str(e)}', status=500)
        
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
        # Pero solo rechazar si NO es Pexels (Pexels puede tener URLs sin extensión)
        if any(video_url.lower().endswith(ext) for ext in image_extensions):
            if source != 'pexels':  # Pexels puede tener URLs sin extensión clara
                return HttpResponse('Esta URL parece ser una imagen, no un video', status=400)
        
        # Verificar si tiene extensión de video o contiene indicadores de video
        has_video_ext = any(video_url.lower().endswith(ext) for ext in video_extensions)
        has_video_indicator = '/videos/' in video_url.lower() or '/video/' in video_url.lower() or 'pexels.com' in video_url.lower()
        
        # Para Pexels, confiar en la URL aunque no tenga extensión clara
        if source == 'pexels':
            # Pexels URLs son confiables
            pass
        elif not has_video_ext and not has_video_indicator:
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
                # Para Pexels, confiar en la URL aunque el Content-Type no sea claro
                if source == 'pexels':
                    logger.info(f"Pexels video con Content-Type no estándar: {content_type}, continuando...")
                else:
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


class ItemDownloadView(LoginRequiredMixin, ServiceMixin, View):
    """View para descargar archivos de items (video, image, audio) forzando descarga"""
    
    def get(self, request, item_type, item_id):
        """
        Descarga un archivo desde GCS forzando la descarga (no abrir en navegador)
        
        Args:
            item_type: 'video', 'image', 'audio'
            item_id: UUID del item
        """
        from django.http import HttpResponse, Http404
        from django.db.models import Q
        import uuid as uuid_module
        
        # Validar y convertir item_id a UUID
        try:
            item_uuid = uuid_module.UUID(item_id)
        except (ValueError, TypeError):
            raise Http404('ID de item inválido')
        
        user = request.user
        user_projects = ProjectService.get_user_projects(user)
        user_project_ids = [p.id for p in user_projects]
        
        # Obtener el item según el tipo
        if item_type == 'video':
            from core.models import Video
            item = get_object_or_404(Video, uuid=item_uuid)
            gcs_path = item.gcs_path
            
            # Verificar acceso
            has_project_access = item.project_id in user_project_ids if item.project_id else False
            has_direct_access = item.project is None and item.created_by_id and item.created_by_id == user.id
            if not (has_project_access or has_direct_access):
                raise Http404('No tienes acceso a este video')
                
        elif item_type == 'image':
            from core.models import Image
            item = get_object_or_404(Image, uuid=item_uuid)
            gcs_path = item.gcs_path
            
            # Verificar acceso
            has_project_access = item.project_id in user_project_ids if item.project_id else False
            has_direct_access = item.project is None and item.created_by_id and item.created_by_id == user.id
            if not (has_project_access or has_direct_access):
                raise Http404('No tienes acceso a esta imagen')
                
        elif item_type == 'audio':
            from core.models import Audio
            item = get_object_or_404(Audio, uuid=item_uuid)
            gcs_path = item.gcs_path
            
            # Verificar acceso
            has_project_access = item.project_id in user_project_ids if item.project_id else False
            has_direct_access = item.project is None and item.created_by_id and item.created_by_id == user.id
            if not (has_project_access or has_direct_access):
                raise Http404('No tienes acceso a este audio')
        else:
            raise Http404('Tipo de item inválido')
        
        # Verificar que el item tenga archivo
        if not gcs_path:
            raise Http404('El item no tiene archivo disponible')
        
        # Verificar que el archivo esté completado
        if item.status != 'completed':
            raise Http404('El archivo aún no está disponible para descarga')
        
        try:
            # Descargar archivo desde GCS
            from core.storage.gcs import gcs_storage
            
            blob_name = gcs_path.replace(f"gs://{settings.GCS_BUCKET_NAME}/", "")
            blob = gcs_storage.bucket.blob(blob_name)
            
            if not blob.exists():
                raise Http404('El archivo no existe en GCS')
            
            # Descargar contenido
            file_content = blob.download_as_bytes()
            
            # Obtener content type del blob
            content_type = blob.content_type or 'application/octet-stream'
            
            # Determinar extensión y nombre de archivo
            import os
            filename = item.title or 'download'
            # Limpiar nombre de archivo
            safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_filename = safe_filename.replace(' ', '_')[:50]  # Limitar longitud
            
            # Determinar extensión según content type o tipo de item
            extension_map = {
                'image/png': '.png',
                'image/jpeg': '.jpg',
                'image/jpg': '.jpg',
                'image/webp': '.webp',
                'image/gif': '.gif',
                'video/mp4': '.mp4',
                'video/webm': '.webm',
                'video/quicktime': '.mov',
                'audio/mpeg': '.mp3',
                'audio/wav': '.wav',
                'audio/ogg': '.ogg',
                'audio/mp4': '.m4a',
            }
            
            extension = extension_map.get(content_type, '')
            if not extension:
                # Fallback según tipo de item
                if item_type == 'image':
                    extension = '.png'
                elif item_type == 'video':
                    extension = '.mp4'
                elif item_type == 'audio':
                    extension = '.mp3'
            
            # Asegurar que el nombre tenga extensión
            if not safe_filename.endswith(extension):
                safe_filename += extension
            
            # Crear respuesta con headers de descarga
            response = HttpResponse(file_content, content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
            response['Content-Length'] = len(file_content)
            
            logger.info(f"Descarga de {item_type} {item_uuid}: {safe_filename} ({len(file_content)} bytes)")
            
            return response
            
        except Exception as e:
            logger.error(f"Error al descargar {item_type} {item_uuid}: {e}", exc_info=True)
            raise Http404('Error al descargar el archivo')


class StockDownloadView(LoginRequiredMixin, View):
    """Vista para descargar contenido stock y guardarlo en BD"""
    
    def post(self, request):
        """
        Descarga contenido stock y lo guarda en BD como Audio/Image/Video
        
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
            
            # Estrategia de extracción de URL mejorada
            # 1. Preferir 'download_url' explícita
            download_url = item.get('download_url')
            
            # 2. Si no, usar 'preview' (común en imágenes/videos de stock para visualización)
            if not download_url:
                download_url = item.get('preview')
            
            # 3. Si no, usar 'original_url'
            if not download_url:
                download_url = item.get('original_url')

            # 4. Si no, intentar 'url' si parece un archivo válido
            if not download_url:
                url_candidate = item.get('url')
                if url_candidate and isinstance(url_candidate, str):
                    # Relajar chequeo: aceptar si tiene extensión de archivo conocida o si no termina en html/htm
                    is_html = url_candidate.endswith(('.htm', '.html')) or '/view/' in url_candidate or '/photo/' in url_candidate or '/video/' in url_candidate
                    if not is_html:
                        download_url = url_candidate
            
            # 5. Fallback final: thumbnail (mejor algo que nada)
            if not download_url:
                download_url = item.get('thumbnail')
            
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
                    # Intentar buscar por UUID primero (formato 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx')
                    try:
                        project = Project.objects.get(uuid=project_id)
                    except (Project.DoesNotExist, ValueError, TypeError) as e:
                        # Fallback a ID numérico si no es UUID válido o no se encuentra
                        if isinstance(project_id, int) or (isinstance(project_id, str) and project_id.isdigit()):
                            project = Project.objects.get(id=project_id)
                        else:
                            raise Project.DoesNotExist from e
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
                
                # --- MIME GUARD ---
                # Verificar que el MIME detectado (si existe) coincida con el tipo esperado
                expected_type_guard = item.get('content_type') or content_type
                if detected_mime and expected_type_guard:
                    allowed_prefixes = []
                    if expected_type_guard == 'image':
                        allowed_prefixes = ['image/']
                    elif expected_type_guard == 'video':
                        allowed_prefixes = ['video/']
                    elif expected_type_guard == 'audio':
                        allowed_prefixes = ['audio/']
                    
                    # Si tenemos prefixes definidos, verificamos. Si no (tipo desconocido), permitimos pasar (fallback)
                    if allowed_prefixes:
                        is_valid_mime = any(detected_mime.startswith(prefix) for prefix in allowed_prefixes)
                        if not is_valid_mime:
                            err_msg = f"MIME guard failed: Expected '{expected_type_guard}' but detected '{detected_mime}'"
                            logger.error(f"StockDownloadView Error: {err_msg}. Item ID: {item.get('id')}")
                            return JsonResponse({
                                'success': False,
                                'error': f"Tipo de archivo incorrecto. Se esperaba {expected_type_guard} pero se recibió {detected_mime}."
                            }, status=400)
                # ------------------
                
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
                from core.storage.gcs import gcs_storage
                
                # Crear Audio (unificado - puede ser música o voz)
                audio = Audio.objects.create(
                    title=item.get('title', 'Audio de stock'),
                    type=audio_type,  # 'music' o 'voice'
                    prompt=item.get('description', '') if audio_type == 'music' else None,
                    text=item.get('description', '') if audio_type != 'music' else None,
                    duration_ms=item.get('duration', 0) * 1000 if item.get('duration') else None,
                    created_by=request.user,
                    project=project,
                    status='completed'
                )
                
                # Subir a GCS
                if project:
                    gcs_path = f"projects/{project.uuid}/audios/{audio.uuid}/audio.{file_extension}"
                else:
                    gcs_path = f"audios/no_project/{audio.uuid}/audio.{file_extension}"
                
                file_content.seek(0)
                gcs_full_path = gcs_storage.upload_from_bytes(
                    file_content.read(),
                    gcs_path,
                    content_type=final_content_type or 'audio/mpeg'
                )
                
                audio.gcs_path = gcs_full_path
                audio.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Audio guardado correctamente',
                    'item': {
                        'id': str(audio.uuid),
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
                    gcs_path = f"projects/{project.id}/images/{image.uuid}/image.{file_extension}"
                else:
                    gcs_path = f"images/{image.uuid}/image.{file_extension}"
                
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
                        'id': str(image.uuid),
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
                    gcs_path = f"projects/{project.id}/videos/{video.uuid}/video.{file_extension}"
                else:
                    gcs_path = f"videos/{video.uuid}/video.{file_extension}"
                
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
                        'id': str(video.uuid),
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


# ====================
# NOTIFICATIONS
# ====================

class NotificationsPanelView(LoginRequiredMixin, View):
    """Vista para el panel de notificaciones (HTMX partial)"""
    
    def get(self, request):
        notifications = Notification.objects.filter(
            user=request.user
        ).order_by('-created_at')[:50]
        
        return render(request, 'partials/notifications_panel.html', {
            'notifications': notifications,
            'unread_count': Notification.objects.filter(user=request.user, read=False).count()
        })


class NotificationsCountView(LoginRequiredMixin, View):
    """API para obtener el contador de notificaciones no leídas"""
    
    def get(self, request):
        count = Notification.objects.filter(user=request.user, read=False).count()
        return JsonResponse({'count': count})


class MarkNotificationReadView(LoginRequiredMixin, View):
    """Marcar una notificación como leída"""
    
    def post(self, request, notification_uuid):
        try:
            notification = Notification.objects.get(
                uuid=notification_uuid,
                user=request.user
            )
            notification.mark_as_read()
            
            # Si es HTMX request, devolver el HTML actualizado (sin botón de marcar como leída)
            if request.headers.get('HX-Request'):
                return render(request, 'partials/notification_item.html', {
                    'notification': notification
                })
            
            return JsonResponse({'success': True})
        except Notification.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Notificación no encontrada'}, status=404)


class MarkAllNotificationsReadView(LoginRequiredMixin, View):
    """Marcar todas las notificaciones como leídas"""
    
    def post(self, request):
        Notification.objects.filter(user=request.user, read=False).update(
            read=True,
            read_at=timezone.now()
        )
        return JsonResponse({'success': True})


# ====================
# QUEUES (TAREAS DE GENERACIÓN)
# ====================

class QueuesPanelView(LoginRequiredMixin, View):
    """Vista para el panel de colas de generación (mantenida para compatibilidad, pero no accesible desde sidebar)"""
    
    def get(self, request):
        # Filtrar por estado si se proporciona
        status_filter = request.GET.get('status', 'all')
        
        # Obtener todas las tareas del usuario
        tasks = GenerationTask.objects.filter(user=request.user)
        
        # Filtrar por estado si no es 'all'
        if status_filter != 'all':
            tasks = tasks.filter(status=status_filter)
        
        # Ordenar por fecha de creación (más recientes primero)
        tasks = tasks.order_by('-created_at')[:100]  # Limitar a las últimas 100
        
        # Estadísticas
        stats = {
            'total': GenerationTask.objects.filter(user=request.user).count(),
            'queued': GenerationTask.objects.filter(user=request.user, status='queued').count(),
            'processing': GenerationTask.objects.filter(user=request.user, status='processing').count(),
            'completed': GenerationTask.objects.filter(user=request.user, status='completed').count(),
            'failed': GenerationTask.objects.filter(user=request.user, status='failed').count(),
            'cancelled': GenerationTask.objects.filter(user=request.user, status='cancelled').count(),
        }
        
        return render(request, 'queues/panel.html', {
            'tasks': tasks,
            'stats': stats,
            'status_filter': status_filter,
        })


class ActiveQueuesDropdownView(LoginRequiredMixin, View):
    """Vista parcial para el dropdown de colas activas (solo queued y processing)"""
    
    def get(self, request):
        # Solo obtener tareas activas (en cola o procesando)
        active_tasks = GenerationTask.objects.filter(
            user=request.user,
            status__in=['queued', 'processing']
        ).order_by('-created_at')[:20]  # Limitar a las últimas 20
        
        # Contador total
        active_count = GenerationTask.objects.filter(
            user=request.user,
            status__in=['queued', 'processing']
        ).count()
        
        return render(request, 'partials/active_queues_dropdown.html', {
            'active_tasks': active_tasks,
            'active_count': active_count,
        })


class QueueTaskDetailView(LoginRequiredMixin, View):
    """Vista para ver detalles de una tarea específica"""
    
    def get(self, request, task_uuid):
        try:
            task = GenerationTask.objects.get(uuid=task_uuid, user=request.user)
            
            # Obtener el item relacionado si es posible
            item = None
            item_url = None
            if task.task_type == 'video':
                try:
                    item = Video.objects.get(uuid=task.item_uuid)
                    item_url = reverse('core:video_detail', args=[item.uuid])
                except Video.DoesNotExist:
                    pass
            elif task.task_type == 'image':
                try:
                    # Intentar buscar por uuid primero, luego por id (compatibilidad)
                    if task.item_uuid:
                        item = Image.objects.get(uuid=task.item_uuid)
                    else:
                        item_id = task.metadata.get('item_id')
                        if item_id:
                            item = Image.objects.get(id=item_id)
                    if item:
                        item_url = reverse('core:image_detail', args=[item.uuid])
                except Image.DoesNotExist:
                    pass
            elif task.task_type == 'audio':
                try:
                    item = Audio.objects.get(uuid=task.item_uuid)
                    item_url = reverse('core:audio_detail', args=[item.uuid])
                except Audio.DoesNotExist:
                    pass
            
            return render(request, 'queues/task_detail.html', {
                'task': task,
                'item': item,
                'item_url': item_url,
            })
        except GenerationTask.DoesNotExist:
            raise Http404("Tarea no encontrada")


class CancelTaskView(LoginRequiredMixin, View):
    """Cancelar una tarea pendiente o en proceso"""
    
    def post(self, request, task_uuid):
        try:
            task = GenerationTask.objects.get(uuid=task_uuid, user=request.user)
            
            # Solo se pueden cancelar tareas en cola o procesando
            if task.status not in ['queued', 'processing']:
                return JsonResponse({
                    'success': False,
                    'error': f'No se puede cancelar una tarea con estado "{task.status}"'
                }, status=400)
            
            # Cancelar la tarea en Celery si tiene task_id
            if task.task_id:

                # Intentar usar SIGKILL primero (más efectivo en Linux/WSL)
                try:
                    logger.info(f"Cancelando tarea Celery: {task.task_id} (force kill - SIGKILL)")
                    current_app.control.revoke(task.task_id, terminate=True, signal='SIGKILL')
                except AttributeError:
                    # Fallback para Windows (no tiene SIGKILL)
                    logger.info(f"SIGKILL no soportado, usando SIGTERM para tarea: {task.task_id}")
                    current_app.control.revoke(task.task_id, terminate=True, signal='SIGTERM')
                except Exception as e:
                    logger.error(f"Error al revocar tarea {task.task_id}: {e}")
                    # Último intento con SIGTERM
                    current_app.control.revoke(task.task_id, terminate=True, signal='SIGTERM')

                # Actualizar estado del item asociado a 'cancelled'
                try:
                    item = None
                    if task.task_type == 'video':
                        item = Video.objects.filter(uuid=task.item_uuid).first()
                    elif task.task_type == 'image':
                        item = Image.objects.filter(uuid=task.item_uuid).first()
                    elif task.task_type == 'audio':
                        item = Audio.objects.filter(uuid=task.item_uuid).first()
                    
                    if item:
                        # Usar update para ser más eficiente y evitar señales si no es necesario
                        item_class = item.__class__
                        item_class.objects.filter(pk=item.pk).update(status='cancelled')
                        logger.info(f"Item {task.item_uuid} ({task.task_type}) marcado como cancelado")
                except Exception as e:
                    logger.error(f"Error al actualizar estado del item: {e}")

            else:
                logger.warning(f"Tarea {task.uuid} no tiene task_id de Celery para revocar")
            
            # Marcar como cancelada
            task.mark_as_cancelled(reason='Cancelada por el usuario (Force killed)')
            
            # Obtener lista actualizada para refrescar el dropdown
            active_tasks = GenerationTask.objects.filter(
                user=request.user,
                status__in=['queued', 'processing']
            ).order_by('-created_at')[:20]
            
            active_count = GenerationTask.objects.filter(
                user=request.user,
                status__in=['queued', 'processing']
            ).count()
            
            return render(request, 'partials/active_queues_dropdown.html', {
                'active_tasks': active_tasks,
                'active_count': active_count,
            })
            
        except GenerationTask.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Tarea no encontrada'}, status=404)


# ====================
# PROMPT TEMPLATES API
# ====================

class PromptTemplatesAPIView(LoginRequiredMixin, View):
    """API endpoint para listar templates de prompts"""
    
    def get(self, request):
        """
        Lista templates de prompts con filtros
        
        Query params:
            type: Filtrar por tipo ('video', 'image', 'agent')
            service: Filtrar por servicio recomendado ('sora', 'gemini_veo', etc.)
            tab: 'my' (mis templates), 'public' (públicos), 'favorites' (favoritos)
            search: Buscar por nombre
        """
        from .models import PromptTemplate, UserPromptFavorite
        
        template_type = request.GET.get('type')
        recommended_service = request.GET.get('service')
        tab = request.GET.get('tab', 'public')  # my, public, favorites
        search = request.GET.get('search', '').strip()
        
        try:
            # Base queryset
            if tab == 'my':
                # Mis templates
                queryset = PromptTemplate.objects.filter(
                    created_by=request.user,
                    is_active=True
                )
            elif tab == 'favorites':
                # Templates favoritos del usuario
                favorite_ids = UserPromptFavorite.objects.filter(
                    user=request.user
                ).values_list('template_id', flat=True)
                queryset = PromptTemplate.objects.filter(
                    uuid__in=favorite_ids,
                    is_active=True
                )
            else:
                # Templates públicos
                queryset = PromptTemplate.objects.filter(
                    is_public=True,
                    is_active=True
                )
            
            # Aplicar filtros
            if template_type:
                queryset = queryset.filter(template_type=template_type)
            
            if recommended_service:
                queryset = queryset.filter(recommended_service=recommended_service)
            
            if search:
                queryset = queryset.filter(name__icontains=search)
            
            # Ordenar por popularidad
            templates = queryset.order_by('-usage_count', '-upvotes', '-created_at')[:50]
            
            # Serializar templates
            templates_data = []
            user_favorites = set()
            user_votes = {}
            
            if request.user.is_authenticated:
                # Obtener favoritos del usuario
                user_favorites = set(
                    UserPromptFavorite.objects.filter(
                        user=request.user,
                        template__in=templates
                    ).values_list('template_id', flat=True)
                )
                
                # Obtener votos del usuario
                from .models import UserPromptVote
                votes = UserPromptVote.objects.filter(
                    user=request.user,
                    template__in=templates
                ).select_related('template')
                
                for vote in votes:
                    user_votes[str(vote.template.uuid)] = vote.vote_type
            
            for template in templates:
                # Generar URL firmada si es un gcs_path
                preview_url = template.preview_url
                if preview_url and preview_url.startswith('gs://'):
                    try:
                        from core.storage.gcs import gcs_storage
                        preview_url = gcs_storage.get_signed_url(preview_url, expiration=3600)
                    except Exception as e:
                        logger.warning(f"Error al generar URL firmada para template {template.uuid}: {e}")
                        preview_url = None
                
                template_dict = {
                    'uuid': str(template.uuid),
                    'name': template.name,
                    'description': template.description,
                    'template_type': template.template_type,
                    'recommended_service': template.recommended_service,
                    'preview_url': preview_url,
                    'is_public': template.is_public,
                    'usage_count': template.usage_count,
                    'upvotes': template.upvotes,
                    'downvotes': template.downvotes,
                    'rating': template.get_rating(),
                    'created_at': template.created_at.isoformat(),
                    'is_favorite': str(template.uuid) in user_favorites,
                    'user_vote': user_votes.get(str(template.uuid)),
                    'created_by': template.created_by.username if template.created_by else None,
                }
                templates_data.append(template_dict)
            
            return JsonResponse({
                'templates': templates_data,
                'count': len(templates_data),
                'tab': tab
            })
        
        except Exception as e:
            logger.error(f"Error al obtener templates: {e}", exc_info=True)
            return JsonResponse({
                'error': 'Error al cargar templates',
                'error_detail': str(e)
            }, status=500)


class PromptTemplateDetailAPIView(LoginRequiredMixin, View):
    """API endpoint para obtener detalles de un template"""
    
    def get(self, request, template_uuid):
        """Obtiene detalles de un template específico"""
        from .models import PromptTemplate
        
        try:
            template = PromptTemplate.objects.get(uuid=template_uuid, is_active=True)
            
            # Verificar acceso
            if not template.is_public and template.created_by != request.user:
                return JsonResponse({
                    'error': 'No tienes acceso a este template'
                }, status=403)
            
            # Verificar si es favorito
            is_favorite = False
            user_vote = None
            
            if request.user.is_authenticated:
                from .models import UserPromptFavorite, UserPromptVote
                is_favorite = UserPromptFavorite.objects.filter(
                    user=request.user,
                    template=template
                ).exists()
                
                try:
                    vote = UserPromptVote.objects.get(user=request.user, template=template)
                    user_vote = vote.vote_type
                except UserPromptVote.DoesNotExist:
                    pass
            
            # Generar URL firmada si es un gcs_path
            preview_url = template.preview_url
            if preview_url and preview_url.startswith('gs://'):
                try:
                    from core.storage.gcs import gcs_storage
                    preview_url = gcs_storage.get_signed_url(preview_url, expiration=3600)
                except Exception as e:
                    logger.warning(f"Error al generar URL firmada para template {template.uuid}: {e}")
                    preview_url = None
            
            return JsonResponse({
                'uuid': str(template.uuid),
                'name': template.name,
                'description': template.description,
                'template_type': template.template_type,
                'recommended_service': template.recommended_service,
                'preview_url': preview_url,
                'is_public': template.is_public,
                'usage_count': template.usage_count,
                'upvotes': template.upvotes,
                'downvotes': template.downvotes,
                'rating': template.get_rating(),
                'created_at': template.created_at.isoformat(),
                'is_favorite': is_favorite,
                'user_vote': user_vote,
                'created_by': template.created_by.username if template.created_by else None,
                # NO incluir prompt_text por seguridad (el usuario no debe verlo)
            })
        
        except PromptTemplate.DoesNotExist:
            return JsonResponse({
                'error': 'Template no encontrado'
            }, status=404)
        except Exception as e:
            logger.error(f"Error al obtener template: {e}", exc_info=True)
            return JsonResponse({
                'error': 'Error al cargar template',
                'error_detail': str(e)
            }, status=500)


class PromptTemplateVoteAPIView(LoginRequiredMixin, View):
    """API endpoint para votar templates"""
    
    def post(self, request, template_uuid):
        """
        Vota un template (upvote o downvote)
        
        Body JSON:
        {
            "vote_type": "upvote" | "downvote" | null (para quitar voto)
        }
        """
        from .models import PromptTemplate, UserPromptVote
        import json
        
        try:
            data = json.loads(request.body)
            vote_type = data.get('vote_type')  # 'upvote', 'downvote', o null
            
            template = PromptTemplate.objects.get(uuid=template_uuid, is_active=True)
            
            # Verificar acceso
            if not template.is_public and template.created_by != request.user:
                return JsonResponse({
                    'error': 'No tienes acceso a este template'
                }, status=403)
            
            # Obtener o crear voto
            vote, created = UserPromptVote.objects.get_or_create(
                user=request.user,
                template=template,
                defaults={'vote_type': vote_type} if vote_type else {}
            )
            
            if vote_type:
                # Actualizar o crear voto
                old_vote_type = vote.vote_type
                vote.vote_type = vote_type
                vote.save()
                
                # Actualizar contadores del template
                if old_vote_type == 'upvote':
                    template.upvotes = max(0, template.upvotes - 1)
                elif old_vote_type == 'downvote':
                    template.downvotes = max(0, template.downvotes - 1)
                
                if vote_type == 'upvote':
                    template.upvotes += 1
                elif vote_type == 'downvote':
                    template.downvotes += 1
                
                template.save(update_fields=['upvotes', 'downvotes'])
            else:
                # Eliminar voto
                old_vote_type = vote.vote_type
                vote.delete()
                
                # Actualizar contadores
                if old_vote_type == 'upvote':
                    template.upvotes = max(0, template.upvotes - 1)
                elif old_vote_type == 'downvote':
                    template.downvotes = max(0, template.downvotes - 1)
                
                template.save(update_fields=['upvotes', 'downvotes'])
            
            return JsonResponse({
                'success': True,
                'upvotes': template.upvotes,
                'downvotes': template.downvotes,
                'rating': template.get_rating(),
                'user_vote': vote_type if vote_type else None
            })
        
        except PromptTemplate.DoesNotExist:
            return JsonResponse({
                'error': 'Template no encontrado'
            }, status=404)
        except Exception as e:
            logger.error(f"Error al votar template: {e}", exc_info=True)
            return JsonResponse({
                'error': 'Error al votar template',
                'error_detail': str(e)
            }, status=500)


class PromptTemplateFavoriteAPIView(LoginRequiredMixin, View):
    """API endpoint para marcar/desmarcar templates como favoritos"""
    
    def post(self, request, template_uuid):
        """
        Marca o desmarca un template como favorito
        
        Body JSON:
        {
            "is_favorite": true | false
        }
        """
        from .models import PromptTemplate, UserPromptFavorite
        import json
        
        try:
            data = json.loads(request.body)
            is_favorite = data.get('is_favorite', True)
            
            template = PromptTemplate.objects.get(uuid=template_uuid, is_active=True)
            
            # Verificar acceso
            if not template.is_public and template.created_by != request.user:
                return JsonResponse({
                    'error': 'No tienes acceso a este template'
                }, status=403)
            
            if is_favorite:
                # Marcar como favorito
                UserPromptFavorite.objects.get_or_create(
                    user=request.user,
                    template=template
                )
            else:
                # Desmarcar favorito
                UserPromptFavorite.objects.filter(
                    user=request.user,
                    template=template
                ).delete()
            
            return JsonResponse({
                'success': True,
                'is_favorite': is_favorite
            })
        
        except PromptTemplate.DoesNotExist:
            return JsonResponse({
                'error': 'Template no encontrado'
            }, status=404)
        except Exception as e:
            logger.error(f"Error al marcar favorito: {e}", exc_info=True)
            return JsonResponse({
                'error': 'Error al marcar favorito',
                'error_detail': str(e)
            }, status=500)


class UploadItemView(LoginRequiredMixin, ServiceMixin, View):
    """Vista para subir archivos desde el dispositivo a la biblioteca"""

    def get(self, request):
        """Muestra el formulario de subida"""
        return render(request, 'library/upload.html')

    def post(self, request):
        """Procesa la subida del archivo"""
        from core.storage.gcs import gcs_storage
        from django.utils.crypto import get_random_string
        import mimetypes

        try:
            # Obtener el archivo del request
            uploaded_file = request.FILES.get('file')
            if not uploaded_file:
                messages.error(request, 'No se seleccionó ningún archivo')
                return redirect('core:library')

            # Validar tamaño del archivo (máximo 500MB)
            max_size = 500 * 1024 * 1024  # 500MB
            if uploaded_file.size > max_size:
                messages.error(request, f'El archivo es demasiado grande. Máximo permitido: 500MB. Archivo actual: {uploaded_file.size / (1024*1024):.1f}MB')
                return redirect('core:library')

            # Validar nombre de archivo (seguridad básica)
            if not uploaded_file.name or len(uploaded_file.name) > 255:
                messages.error(request, 'Nombre de archivo inválido')
                return redirect('core:library')

            # Determinar el tipo de archivo basado en content_type
            content_type = uploaded_file.content_type.lower() if uploaded_file.content_type else ''
            
            # Mapeo explícito de tipos MIME permitidos para seguridad
            ALLOWED_VIDEO_TYPES = {
                'video/mp4': 'mp4',
                'video/webm': 'webm',
                'video/quicktime': 'mov',
                'video/x-msvideo': 'avi',
                'video/x-matroska': 'mkv',
            }
            
            ALLOWED_IMAGE_TYPES = {
                'image/jpeg': 'jpg',
                'image/png': 'png',
                'image/gif': 'gif',
                'image/webp': 'webp',
            }
            
            ALLOWED_AUDIO_TYPES = {
                'audio/mpeg': 'mp3',
                'audio/wav': 'wav',
                'audio/ogg': 'ogg',
                'audio/mp4': 'm4a',
                'audio/x-m4a': 'm4a',
            }
            
            file_type = None
            model_class = None
            file_extension = None

            # Validar contra listas blancas explícitas
            if content_type in ALLOWED_VIDEO_TYPES:
                file_type = 'video'
                model_class = Video
                file_extension = ALLOWED_VIDEO_TYPES[content_type]
            elif content_type in ALLOWED_IMAGE_TYPES:
                file_type = 'image'
                model_class = Image
                file_extension = ALLOWED_IMAGE_TYPES[content_type]
            elif content_type in ALLOWED_AUDIO_TYPES:
                file_type = 'audio'
                model_class = Audio
                file_extension = ALLOWED_AUDIO_TYPES[content_type]

            if not file_type:
                messages.error(request, f'Tipo de archivo no soportado: {content_type}. Solo se permiten videos (MP4, WebM, MOV, AVI), imágenes (JPG, PNG, GIF, WebP) y audios (MP3, WAV, OGG, M4A).')
                return redirect('core:library')

            # Generar nombre único para el archivo
            random_suffix = get_random_string(8)
            filename = f"{file_type}s/{request.user.id}/{timezone.now().strftime('%Y%m%d_%H%M%S')}_{random_suffix}.{file_extension}"
            
            # Subir a GCS con manejo de errores específico
            try:
                gcs_path = gcs_storage.upload_django_file(uploaded_file, filename)
                logger.info(f"Archivo subido a GCS: {gcs_path} por usuario {request.user.id}")
            except Exception as gcs_error:
                logger.error(f"Error al subir a GCS: {gcs_error}", exc_info=True)
                messages.error(request, 'Error al subir el archivo al almacenamiento. Por favor, intenta de nuevo.')
                return redirect('core:library')

            # Crear el registro en la base de datos
            item_data = {
                'created_by': request.user,
                'title': uploaded_file.name[:255],  # Truncar a longitud máxima
                'status': 'completed',
                'gcs_path': gcs_path,
                'completed_at': timezone.now(),
            }

            # Campos específicos por tipo con validación
            if file_type == 'video':
                item_data.update({
                    'type': 'uploaded_video',
                    'script': '',  # Campo requerido, vacío para uploads
                    'duration': None,
                    'config': {},  # Asegurar que config existe
                })
            elif file_type == 'image':
                item_data.update({
                    'type': 'uploaded_image',
                    'prompt': '',  # Campo requerido, vacío para uploads
                    'width': None,
                    'height': None,
                    'config': {},
                })
            elif file_type == 'audio':
                item_data.update({
                    'type': 'uploaded_audio',
                    'duration': None,
                })

            # Crear el objeto con manejo de errores
            try:
                item = model_class.objects.create(**item_data)
                logger.info(f"{file_type.title()} creado: ID={item.id}, usuario={request.user.id}")
                messages.success(request, f'{file_type.title()} "{uploaded_file.name}" subido correctamente a tu biblioteca.')
                return redirect('core:library')
            except Exception as db_error:
                logger.error(f"Error al crear registro en BD: {db_error}", exc_info=True)
                # Intentar eliminar archivo de GCS si falla la creación en BD
                try:
                    gcs_storage.delete_file(gcs_path)
                    logger.info(f"Archivo eliminado de GCS tras error en BD: {gcs_path}")
                except:
                    pass
                messages.error(request, 'Error al guardar el archivo en la base de datos.')
                return redirect('core:library')

        except Exception as e:
            logger.error(f"Error inesperado al subir archivo: {e}", exc_info=True)
            messages.error(request, 'Error inesperado al subir el archivo. Por favor, contacta al soporte.')
            return redirect('core:library')


class PasswordResetRequestView(View):
    def get(self, request):
        return render(request, 'login/password_reset_form.html', {'hide_header': True})

    def post(self, request):
        
        username = request.POST.get('username')
        email = request.POST.get('email')

        # Siempre mostrar mensaje de éxito para no enumerar usuarios
        success_message = 'Si los datos son correctos, recibirás un correo con las instrucciones.'
        
        if not username or not email:
            messages.error(request, 'Por favor completa todos los campos.')
            return render(request, 'login/password_reset_form.html', {'hide_header': True})

        try:
            user = User.objects.get(username=username, email=email)
            if user.is_active:
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                
                try:
                    reset_url = request.build_absolute_uri(
                        reverse('core:password_reset_confirm', args=[uid, token])
                    )
                    
                    subject = 'Restablecer contraseña - Atenea'
                    html_message = render_to_string('login/password_reset_email.html', {
                        'user': user,
                        'reset_url': reset_url,
                    })
                    plain_message = strip_tags(html_message)
                    
                    send_mail(
                        subject, 
                        plain_message, 
                        settings.DEFAULT_FROM_EMAIL, 
                        [email], 
                        html_message=html_message
                    )
                    logger.info("Password reset email sent for user_id=%s", user.pk)
                except Exception as e:
                    logger.error(f"Error sending password reset email: {e}")
        except User.DoesNotExist:
            # Simular tiempo de espera para evitar timing attacks
            import time
            import random
            time.sleep(random.uniform(0.1, 0.3))
            pass
            
        messages.success(request, success_message)
        return render(request, 'login/password_reset_form.html', {'hide_header': True})

class SceneDeleteView(View):
    """Vista para eliminar una escena"""
    
    def post(self, request, scene_id):
        if not request.user.is_authenticated:
            return JsonResponse({'status': 'error', 'message': 'No autenticado'}, status=401)
            
        try:
            scene = Scene.objects.get(id=scene_id)
            
            # Verificar permisos (propietario del proyecto o miembro)
            # Asumimos que si tiene acceso al script/proyecto, puede borrar
            # TODO: Refinar permisos si es necesario
            if scene.script.created_by != request.user:
                 # Check project membership if needed, simpler check for now
                 if not scene.project.has_access(request.user):
                     return JsonResponse({'status': 'error', 'message': 'No tienes permisos'}, status=403)

            # Eliminar archivos asociados en GCS si es necesario?
            # Por ahora, confiamos en que Django elimine la entrada de DB
            # Podríamos disparar una tarea de limpieza de GCS en segundo plano
            
            scene.delete()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Escena eliminada correctamente',
                'scene_id': scene_id
            })
            
        except Scene.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Escena no encontrada'}, status=404)
        except Exception as e:
            logger.error(f"Error al eliminar escena {scene_id}: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
