"""
EJEMPLO: Tests - Mejores Prácticas
===================================

Estructura completa de tests para el proyecto
"""

from django.test import TestCase, Client, TransactionTestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, Mock, MagicMock
import json

from core.models import Project, Video
from core.services import ProjectService, VideoService
from core.ai_services.heygen import HeyGenClient

User = get_user_model()


# ====================
# MODEL TESTS
# ====================

class ProjectModelTest(TestCase):
    """Tests para el modelo Project"""
    
    def setUp(self):
        """Setup ejecutado antes de cada test"""
        self.project = Project.objects.create(name='Test Project')
    
    def test_create_project(self):
        """Test crear proyecto"""
        project = Project.objects.create(name='New Project')
        self.assertEqual(project.name, 'New Project')
        self.assertIsNotNone(project.created_at)
        self.assertIsNotNone(project.updated_at)
    
    def test_project_str(self):
        """Test representación string"""
        self.assertEqual(str(self.project), 'Test Project')
    
    def test_video_count_property(self):
        """Test propiedad video_count"""
        self.assertEqual(self.project.video_count, 0)
        
        # Crear video
        Video.objects.create(
            project=self.project,
            title='Test Video',
            type='heygen_avatar_v2',
            script='Test script'
        )
        
        self.assertEqual(self.project.video_count, 1)
    
    def test_completed_videos_property(self):
        """Test propiedad completed_videos"""
        # Crear videos con diferentes estados
        Video.objects.create(
            project=self.project,
            title='Video 1',
            type='gemini_veo',
            script='Script 1',
            status='completed'
        )
        Video.objects.create(
            project=self.project,
            title='Video 2',
            type='gemini_veo',
            script='Script 2',
            status='processing'
        )
        Video.objects.create(
            project=self.project,
            title='Video 3',
            type='gemini_veo',
            script='Script 3',
            status='completed'
        )
        
        self.assertEqual(self.project.completed_videos, 2)


class VideoModelTest(TestCase):
    """Tests para el modelo Video"""
    
    def setUp(self):
        self.project = Project.objects.create(name='Test Project')
        self.video = Video.objects.create(
            project=self.project,
            title='Test Video',
            type='heygen_avatar_v2',
            script='This is a test script',
            config={'avatar_id': 'test123', 'voice_id': 'voice123'}
        )
    
    def test_create_video(self):
        """Test crear video"""
        self.assertEqual(self.video.title, 'Test Video')
        self.assertEqual(self.video.status, 'pending')
        self.assertEqual(self.video.type, 'heygen_avatar_v2')
    
    def test_video_str(self):
        """Test representación string"""
        self.assertEqual(str(self.video), 'Test Video (HeyGen Avatar V2)')
    
    def test_mark_as_processing(self):
        """Test marcar como procesando"""
        self.video.mark_as_processing()
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, 'processing')
    
    def test_mark_as_completed(self):
        """Test marcar como completado"""
        gcs_path = 'gs://bucket/video.mp4'
        metadata = {'duration': 30}
        
        self.video.mark_as_completed(gcs_path=gcs_path, metadata=metadata)
        self.video.refresh_from_db()
        
        self.assertEqual(self.video.status, 'completed')
        self.assertEqual(self.video.gcs_path, gcs_path)
        self.assertEqual(self.video.metadata, metadata)
        self.assertIsNotNone(self.video.completed_at)
    
    def test_mark_as_error(self):
        """Test marcar con error"""
        error_msg = 'API Error'
        
        self.video.mark_as_error(error_msg)
        self.video.refresh_from_db()
        
        self.assertEqual(self.video.status, 'error')
        self.assertEqual(self.video.error_message, error_msg)


# ====================
# SERVICE TESTS
# ====================

class ProjectServiceTest(TestCase):
    """Tests para ProjectService"""
    
    def test_create_project(self):
        """Test crear proyecto vía servicio"""
        project = ProjectService.create_project(name='New Project')
        
        self.assertIsInstance(project, Project)
        self.assertEqual(project.name, 'New Project')
    
    def test_create_project_strips_whitespace(self):
        """Test que el servicio elimina espacios"""
        project = ProjectService.create_project(name='  Spaced Project  ')
        self.assertEqual(project.name, 'Spaced Project')
    
    def test_create_project_validates_name_length(self):
        """Test validación de longitud mínima"""
        from core.services import ValidationException
        
        with self.assertRaises(ValidationException):
            ProjectService.create_project(name='AB')
    
    @patch('core.storage.gcs.gcs_storage.delete_file')
    def test_delete_project_deletes_gcs_files(self, mock_delete):
        """Test que al eliminar proyecto se eliminan archivos GCS"""
        project = Project.objects.create(name='Test')
        video = Video.objects.create(
            project=project,
            title='Video',
            type='gemini_veo',
            script='Script',
            gcs_path='gs://bucket/video.mp4'
        )
        
        ProjectService.delete_project(project)
        
        # Verificar que se llamó delete_file
        mock_delete.assert_called_once_with('gs://bucket/video.mp4')
        
        # Verificar que el proyecto fue eliminado
        self.assertFalse(Project.objects.filter(id=project.id).exists())


class VideoServiceTest(TestCase):
    """Tests para VideoService"""
    
    def setUp(self):
        self.project = Project.objects.create(name='Test Project')
        self.service = VideoService()
    
    def test_create_video(self):
        """Test crear video vía servicio"""
        video = self.service.create_video(
            project=self.project,
            title='Test Video',
            video_type='gemini_veo',
            script='Test script',
            config={'duration': 8}
        )
        
        self.assertIsInstance(video, Video)
        self.assertEqual(video.title, 'Test Video')
        self.assertEqual(video.status, 'pending')
    
    @patch('core.storage.gcs.gcs_storage.upload_django_file')
    def test_upload_avatar_image(self, mock_upload):
        """Test subir imagen de avatar"""
        mock_upload.return_value = 'gs://bucket/avatar.jpg'
        
        # Simular archivo
        image = SimpleUploadedFile(
            "test.jpg",
            b"file_content",
            content_type="image/jpeg"
        )
        
        result = self.service.upload_avatar_image(image, self.project)
        
        self.assertEqual(result['gcs_path'], 'gs://bucket/avatar.jpg')
        self.assertEqual(result['filename'], 'test.jpg')
        mock_upload.assert_called_once()
    
    @patch('core.ai_services.heygen.HeyGenClient.generate_video')
    @patch('django.conf.settings.HEYGEN_API_KEY', 'test_key')
    def test_generate_heygen_video(self, mock_generate):
        """Test generar video HeyGen"""
        mock_generate.return_value = {
            'data': {'video_id': 'heygen123'}
        }
        
        video = Video.objects.create(
            project=self.project,
            title='Test',
            type='heygen_avatar_v2',
            script='Script',
            config={'avatar_id': 'av1', 'voice_id': 'v1'}
        )
        
        external_id = self.service.generate_video(video)
        
        self.assertEqual(external_id, 'heygen123')
        video.refresh_from_db()
        self.assertEqual(video.status, 'processing')
        self.assertEqual(video.external_id, 'heygen123')
    
    def test_generate_video_validates_status(self):
        """Test que no se puede generar video ya procesando"""
        from core.services import ValidationException
        
        video = Video.objects.create(
            project=self.project,
            title='Test',
            type='gemini_veo',
            script='Script',
            status='processing'
        )
        
        with self.assertRaises(ValidationException):
            self.service.generate_video(video)


# ====================
# VIEW TESTS
# ====================

class DashboardViewTest(TestCase):
    """Tests para la vista del dashboard"""
    
    def setUp(self):
        self.client = Client()
        self.url = reverse('core:dashboard')
    
    def test_dashboard_loads(self):
        """Test que el dashboard carga correctamente"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/index.html')
    
    def test_dashboard_shows_projects(self):
        """Test que muestra proyectos"""
        Project.objects.create(name='Project 1')
        Project.objects.create(name='Project 2')
        
        response = self.client.get(self.url)
        
        self.assertContains(response, 'Project 1')
        self.assertContains(response, 'Project 2')
    
    def test_dashboard_shows_statistics(self):
        """Test que muestra estadísticas"""
        project = Project.objects.create(name='Project')
        Video.objects.create(
            project=project,
            title='Video 1',
            type='gemini_veo',
            script='Script',
            status='completed'
        )
        Video.objects.create(
            project=project,
            title='Video 2',
            type='gemini_veo',
            script='Script',
            status='processing'
        )
        
        response = self.client.get(self.url)
        
        # Verificar contexto
        self.assertEqual(response.context['total_videos'], 2)
        self.assertEqual(response.context['completed_videos'], 1)
        self.assertEqual(response.context['processing_videos'], 1)


class ProjectViewsTest(TestCase):
    """Tests para vistas de proyectos"""
    
    def setUp(self):
        self.client = Client()
        self.project = Project.objects.create(name='Test Project')
    
    def test_project_detail_view(self):
        """Test vista detalle de proyecto"""
        url = reverse('core:project_detail', kwargs={'project_id': self.project.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Project')
    
    def test_project_create_get(self):
        """Test GET en crear proyecto"""
        url = reverse('core:project_create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/create.html')
    
    def test_project_create_post(self):
        """Test POST crear proyecto"""
        url = reverse('core:project_create')
        data = {'name': 'New Project'}
        
        response = self.client.post(url, data)
        
        # Debe redirigir al detalle
        self.assertEqual(response.status_code, 302)
        
        # Verificar que se creó
        project = Project.objects.get(name='New Project')
        self.assertIsNotNone(project)
    
    def test_project_delete(self):
        """Test eliminar proyecto"""
        url = reverse('core:project_delete', kwargs={'project_id': self.project.id})
        response = self.client.post(url)
        
        # Debe redirigir al dashboard
        self.assertEqual(response.status_code, 302)
        
        # Verificar que se eliminó
        self.assertFalse(Project.objects.filter(id=self.project.id).exists())


class VideoViewsTest(TestCase):
    """Tests para vistas de videos"""
    
    def setUp(self):
        self.client = Client()
        self.project = Project.objects.create(name='Test Project')
        self.video = Video.objects.create(
            project=self.project,
            title='Test Video',
            type='gemini_veo',
            script='Test script'
        )
    
    def test_video_detail_view(self):
        """Test vista detalle de video"""
        url = reverse('core:video_detail', kwargs={'video_id': self.video.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Video')
    
    def test_video_create_get(self):
        """Test GET crear video"""
        url = reverse('core:video_create', kwargs={'project_id': self.project.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'videos/create.html')
    
    @patch('core.ai_services.heygen.HeyGenClient.generate_video')
    @patch('django.conf.settings.HEYGEN_API_KEY', 'test_key')
    def test_video_generate(self, mock_generate):
        """Test generar video"""
        mock_generate.return_value = {'data': {'video_id': 'test123'}}
        
        self.video.config = {'avatar_id': 'av1', 'voice_id': 'v1'}
        self.video.type = 'heygen_avatar_v2'
        self.video.save()
        
        url = reverse('core:video_generate', kwargs={'video_id': self.video.id})
        response = self.client.post(url)
        
        # Debe redirigir
        self.assertEqual(response.status_code, 302)
        
        # Verificar que cambió el estado
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, 'processing')


# ====================
# API TESTS
# ====================

class APIViewsTest(TestCase):
    """Tests para endpoints API"""
    
    def setUp(self):
        self.client = Client()
    
    @patch('core.ai_services.heygen.HeyGenClient.list_avatars')
    @patch('django.conf.settings.HEYGEN_API_KEY', 'test_key')
    def test_api_list_avatars(self, mock_list):
        """Test endpoint listar avatares"""
        mock_list.return_value = [
            {'id': 'av1', 'name': 'Avatar 1'},
            {'id': 'av2', 'name': 'Avatar 2'},
        ]
        
        url = reverse('core:api_list_avatars')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['avatars']), 2)
    
    @patch('core.ai_services.heygen.HeyGenClient.list_voices')
    @patch('django.conf.settings.HEYGEN_API_KEY', 'test_key')
    def test_api_list_voices(self, mock_list):
        """Test endpoint listar voces"""
        mock_list.return_value = [
            {'id': 'v1', 'name': 'Voice 1'},
        ]
        
        url = reverse('core:api_list_voices')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['voices']), 1)


# ====================
# INTEGRATION TESTS
# ====================

class VideoGenerationFlowTest(TransactionTestCase):
    """Test completo del flujo de generación de video"""
    
    @patch('core.ai_services.heygen.HeyGenClient.generate_video')
    @patch('core.ai_services.heygen.HeyGenClient.get_video_status')
    @patch('core.storage.gcs.gcs_storage.upload_from_url')
    @patch('django.conf.settings.HEYGEN_API_KEY', 'test_key')
    def test_complete_video_generation_flow(
        self,
        mock_upload,
        mock_status,
        mock_generate
    ):
        """Test flujo completo: crear -> generar -> completar"""
        
        # Setup
        mock_generate.return_value = {'data': {'video_id': 'heygen123'}}
        mock_status.return_value = {
            'status': 'completed',
            'video_url': 'https://example.com/video.mp4'
        }
        mock_upload.return_value = 'gs://bucket/final_video.mp4'
        
        # 1. Crear proyecto
        project = Project.objects.create(name='Integration Test')
        
        # 2. Crear video
        video = Video.objects.create(
            project=project,
            title='Test Video',
            type='heygen_avatar_v2',
            script='Test script',
            config={'avatar_id': 'av1', 'voice_id': 'v1'}
        )
        
        # 3. Generar video
        service = VideoService()
        external_id = service.generate_video(video)
        
        self.assertEqual(external_id, 'heygen123')
        video.refresh_from_db()
        self.assertEqual(video.status, 'processing')
        
        # 4. Consultar estado (simular completado)
        status_data = service.check_video_status(video)
        
        # 5. Verificar resultado final
        video.refresh_from_db()
        self.assertEqual(video.status, 'completed')
        self.assertEqual(video.gcs_path, 'gs://bucket/final_video.mp4')


# ====================
# CÓMO EJECUTAR
# ====================

"""
1. Ejecutar todos los tests:
   python manage.py test

2. Ejecutar tests de una app:
   python manage.py test core

3. Ejecutar un test específico:
   python manage.py test core.tests.ProjectModelTest

4. Con coverage:
   pip install coverage
   coverage run --source='.' manage.py test
   coverage report
   coverage html  # Genera reporte HTML

5. Con pytest (recomendado):
   pip install pytest pytest-django pytest-cov
   pytest
   pytest --cov=core --cov-report=html
"""

