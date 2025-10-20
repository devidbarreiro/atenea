from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.conf import settings
from django.views.decorators.http import require_http_methods
from .models import Project, Video
from .ai_services.heygen import HeyGenClient
from .ai_services.gemini_veo import GeminiVeoClient
from .storage.gcs import gcs_storage
import logging

logger = logging.getLogger(__name__)


def dashboard(request):
    """Dashboard principal con lista de proyectos"""
    projects = Project.objects.all()
    
    context = {
        'projects': projects,
        'total_videos': Video.objects.count(),
        'completed_videos': Video.objects.filter(status='completed').count(),
        'processing_videos': Video.objects.filter(status='processing').count(),
    }
    
    return render(request, 'dashboard/index.html', context)


def project_create(request):
    """Crear nuevo proyecto"""
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            project = Project.objects.create(name=name)
            messages.success(request, f'Proyecto "{name}" creado exitosamente')
            return redirect('core:project_detail', project_id=project.id)
        else:
            messages.error(request, 'El nombre del proyecto es requerido')
    
    context = {
        'breadcrumbs': [
            {'label': 'Nuevo Proyecto', 'url': None}
        ]
    }
    return render(request, 'projects/create.html', context)


def project_detail(request, project_id):
    """Detalle de un proyecto con sus videos"""
    project = get_object_or_404(Project, id=project_id)
    videos = project.videos.all().order_by('-created_at')
    
    # Generar URLs firmadas para videos completados
    videos_with_urls = []
    for video in videos:
        video_data = {
            'video': video,
            'signed_url': None
        }
        if video.status == 'completed' and video.gcs_path:
            try:
                video_data['signed_url'] = gcs_storage.get_signed_url(video.gcs_path, expiration=3600)
            except Exception as e:
                logger.error(f"Error al generar URL firmada para video {video.id}: {str(e)}")
        videos_with_urls.append(video_data)
    
    context = {
        'project': project,
        'videos': videos,
        'videos_with_urls': videos_with_urls,
        'breadcrumbs': [
            {'label': project.name, 'url': None}
        ]
    }
    
    return render(request, 'projects/detail.html', context)


def project_delete(request, project_id):
    """Eliminar un proyecto"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        project_name = project.name
        project.delete()
        messages.success(request, f'Proyecto "{project_name}" eliminado')
        return redirect('core:dashboard')
    
    context = {
        'project': project,
        'breadcrumbs': [
            {'label': project.name, 'url': f'/projects/{project.id}/'},
            {'label': 'Eliminar', 'url': None}
        ]
    }
    return render(request, 'projects/delete.html', context)


def video_create(request, project_id):
    """Crear nuevo video en un proyecto"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        video_type = request.POST.get('type')
        script = request.POST.get('script')
        
        # Configuración según el tipo de video
        config = {}
        
        if video_type == 'heygen_avatar_v2':
            avatar_id = request.POST.get('avatar_id')
            voice_id = request.POST.get('voice_id')
            
            # Validar campos requeridos
            if not avatar_id or not voice_id:
                messages.error(request, 'Avatar y Voice son campos requeridos para HeyGen Avatar V2')
                return redirect('core:video_create', project_id=project_id)
            
            config = {
                'avatar_id': avatar_id,
                'voice_id': voice_id,
                'has_background': request.POST.get('has_background') == 'on',
                'background_url': request.POST.get('background_url', ''),
                'voice_speed': float(request.POST.get('voice_speed', 1.0)),
                'voice_pitch': int(request.POST.get('voice_pitch', 50)),
                'voice_emotion': request.POST.get('voice_emotion', 'Excited'),
            }
            logger.info(f"Video V2 creado con avatar_id={avatar_id}, voice_id={voice_id}")
        elif video_type == 'heygen_avatar_iv':
            voice_id = request.POST.get('voice_id')
            image_source = request.POST.get('image_source', 'upload')
            
            # Validar voice_id requerido
            if not voice_id:
                messages.error(request, 'Voice es requerido para HeyGen Avatar IV')
                return redirect('core:video_create', project_id=project_id)
            
            config = {
                'voice_id': voice_id,
                'video_orientation': request.POST.get('video_orientation', 'portrait'),
                'fit': request.POST.get('fit', 'cover'),
            }
            
            if image_source == 'upload':
                # Usuario sube nueva imagen
                avatar_image = request.FILES.get('avatar_image')
                
                if not avatar_image:
                    messages.error(request, 'Debes subir una imagen')
                    return redirect('core:video_create', project_id=project_id)
                
                # Subir imagen a GCS inmediatamente
                import os
                from datetime import datetime
                
                # Generar path en GCS: avatar_images/project_id/timestamp_filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                safe_filename = avatar_image.name.replace(' ', '_')
                gcs_destination = f"avatar_images/project_{project.id}/{timestamp}_{safe_filename}"
                
                try:
                    logger.info(f"Subiendo nueva imagen de avatar a GCS: {safe_filename}")
                    gcs_path = gcs_storage.upload_django_file(avatar_image, gcs_destination)
                    logger.info(f"Imagen subida exitosamente a GCS: {gcs_path}")
                    
                    config['gcs_avatar_path'] = gcs_path
                    config['image_filename'] = avatar_image.name
                    config['image_source'] = 'upload'
                    
                    logger.info(f"Video IV creado con nueva imagen={avatar_image.name}, voice_id={voice_id}")
                except Exception as e:
                    logger.error(f"Error al subir imagen a GCS: {str(e)}")
                    messages.error(request, f'Error al subir imagen: {str(e)}')
                    return redirect('core:video_create', project_id=project_id)
            else:
                # Usuario usa imagen existente de HeyGen
                existing_image_key = request.POST.get('existing_image_key')
                
                if not existing_image_key:
                    messages.error(request, 'Debes seleccionar una imagen existente')
                    return redirect('core:video_create', project_id=project_id)
                
                # Guardar el image_key directamente (no necesita subir)
                # Nota: HeyGen API list_assets retorna 'id', no 'image_key' directamente
                # Así que guardamos el id y luego lo buscaremos
                config['existing_image_id'] = existing_image_key
                config['image_source'] = 'existing'
                
                logger.info(f"Video IV creado con imagen existente (ID: {existing_image_key}), voice_id={voice_id}")
        elif video_type == 'gemini_veo':
            # Capturar todos los parámetros de Veo 2
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
            
            # Seed es opcional
            seed_value = request.POST.get('seed', '')
            if seed_value and seed_value.isdigit():
                config['seed'] = int(seed_value)
            
            # Limpiar negative_prompt vacío
            if not config['negative_prompt']:
                config.pop('negative_prompt')
            
            # FASE 2: Imagen inicial (imagen-a-video)
            input_image = request.FILES.get('input_image')
            if input_image:
                import os
                from datetime import datetime
                
                # Subir imagen inicial a GCS
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                safe_filename = input_image.name.replace(' ', '_')
                gcs_destination = f"veo_input_images/project_{project.id}/{timestamp}_{safe_filename}"
                
                try:
                    logger.info(f"Subiendo imagen inicial para Veo 2: {safe_filename}")
                    gcs_path = gcs_storage.upload_django_file(input_image, gcs_destination)
                    config['input_image_gcs_uri'] = gcs_path
                    config['input_image_mime_type'] = input_image.content_type or 'image/jpeg'
                    logger.info(f"✅ Imagen inicial subida: {gcs_path}")
                except Exception as e:
                    logger.error(f"Error al subir imagen inicial: {str(e)}")
                    messages.error(request, f'Error al subir imagen: {str(e)}')
                    return redirect('core:video_create', project_id=project_id)
            
            # FASE 2: Imágenes de referencia (máximo 3 asset o 1 style)
            reference_images = []
            for i in range(1, 4):  # Máximo 3 imágenes de referencia
                ref_image = request.FILES.get(f'reference_image_{i}')
                ref_type = request.POST.get(f'reference_type_{i}', 'asset')
                
                if ref_image:
                    import os
                    from datetime import datetime
                    
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    safe_filename = ref_image.name.replace(' ', '_')
                    gcs_destination = f"veo_reference_images/project_{project.id}/{timestamp}_{i}_{safe_filename}"
                    
                    try:
                        logger.info(f"Subiendo imagen de referencia {i} ({ref_type}): {safe_filename}")
                        gcs_path = gcs_storage.upload_django_file(ref_image, gcs_destination)
                        reference_images.append({
                            'gcs_uri': gcs_path,
                            'reference_type': ref_type,
                            'mime_type': ref_image.content_type or 'image/jpeg'
                        })
                        logger.info(f"✅ Imagen de referencia {i} subida: {gcs_path}")
                    except Exception as e:
                        logger.error(f"Error al subir imagen de referencia {i}: {str(e)}")
                        # No bloqueamos la creación si falla una imagen de referencia
            
            if reference_images:
                config['reference_images'] = reference_images
                logger.info(f"🎭 {len(reference_images)} imagen(es) de referencia configuradas")
            
            logger.info(f"Video Veo 2 creado con config: {config}")
        
        video = Video.objects.create(
            project=project,
            title=title,
            type=video_type,
            script=script,
            config=config
        )
        
        messages.success(request, f'Video "{title}" creado. Ahora puedes generarlo.')
        return redirect('core:video_detail', video_id=video.id)
    
    context = {
        'project': project,
        'breadcrumbs': [
            {'label': project.name, 'url': f'/projects/{project.id}/'},
            {'label': 'Nuevo Video', 'url': None}
        ]
    }
    
    return render(request, 'videos/create.html', context)


def video_detail(request, video_id):
    """Detalle de un video"""
    video = get_object_or_404(Video, id=video_id)
    
    # Generar URL firmada si el video está completado
    signed_url = None
    if video.status == 'completed' and video.gcs_path:
        try:
            signed_url = gcs_storage.get_signed_url(video.gcs_path)
        except Exception as e:
            logger.error(f"Error al generar URL firmada: {str(e)}")
    
    # Generar URLs firmadas para TODOS los videos si existen en metadata
    all_videos_with_urls = []
    if video.status == 'completed' and video.metadata.get('all_videos'):
        try:
            for video_data in video.metadata['all_videos']:
                gcs_path = video_data.get('gcs_path')
                if gcs_path:
                    signed = gcs_storage.get_signed_url(gcs_path, expiration=3600)
                    all_videos_with_urls.append({
                        'index': video_data.get('index', 0),
                        'gcs_path': gcs_path,
                        'signed_url': signed,
                        'mime_type': video_data.get('mime_type', 'video/mp4')
                    })
        except Exception as e:
            logger.error(f"Error al generar URLs firmadas para múltiples videos: {str(e)}")
    
    # Generar URLs firmadas para imágenes de referencia si existen
    reference_images_with_urls = []
    if video.config.get('reference_images'):
        try:
            for idx, ref_img in enumerate(video.config['reference_images']):
                gcs_uri = ref_img.get('gcs_uri')
                if gcs_uri:
                    signed = gcs_storage.get_signed_url(gcs_uri, expiration=3600)
                    reference_images_with_urls.append({
                        'index': idx,
                        'gcs_uri': gcs_uri,
                        'signed_url': signed,
                        'reference_type': ref_img.get('reference_type', 'asset'),
                        'mime_type': ref_img.get('mime_type', 'image/jpeg')
                    })
            logger.info(f"Generadas {len(reference_images_with_urls)} URLs firmadas para imágenes de referencia")
        except Exception as e:
            logger.error(f"Error al generar URLs firmadas para imágenes de referencia: {str(e)}")
    
    # Generar URL firmada para imagen inicial si existe
    input_image_url = None
    if video.config.get('input_image_gcs_uri'):
        try:
            input_image_url = gcs_storage.get_signed_url(video.config['input_image_gcs_uri'], expiration=3600)
        except Exception as e:
            logger.error(f"Error al generar URL firmada para imagen inicial: {str(e)}")
    
    context = {
        'video': video,
        'signed_url': signed_url,
        'all_videos': all_videos_with_urls,
        'reference_images': reference_images_with_urls,
        'input_image_url': input_image_url,
        'breadcrumbs': [
            {'label': video.project.name, 'url': f'/projects/{video.project.id}/'},
            {'label': video.title, 'url': None}
        ]
    }
    
    return render(request, 'videos/detail.html', context)


def video_delete(request, video_id):
    """Eliminar un video"""
    video = get_object_or_404(Video, id=video_id)
    project_id = video.project.id
    
    if request.method == 'POST':
        # Eliminar archivo de GCS si existe
        if video.gcs_path:
            try:
                gcs_storage.delete_file(video.gcs_path)
            except Exception as e:
                logger.error(f"Error al eliminar archivo de GCS: {str(e)}")
        
        video_title = video.title
        video.delete()
        messages.success(request, f'Video "{video_title}" eliminado')
        return redirect('core:project_detail', project_id=project_id)
    
    context = {
        'video': video,
        'breadcrumbs': [
            {'label': video.project.name, 'url': f'/projects/{video.project.id}/'},
            {'label': video.title, 'url': f'/videos/{video.id}/'},
            {'label': 'Eliminar', 'url': None}
        ]
    }
    return render(request, 'videos/delete.html', context)


@require_http_methods(["POST"])
def video_generate(request, video_id):
    """Genera el video usando la API correspondiente"""
    video = get_object_or_404(Video, id=video_id)
    
    # Validar que no esté ya procesando o completado
    if video.status in ['processing', 'completed']:
        messages.warning(request, f'El video ya está en estado: {video.get_status_display()}')
        return redirect('core:video_detail', video_id=video.id)
    
    try:
        video.mark_as_processing()
        
        if video.type in ['heygen_avatar_v2', 'heygen_avatar_iv']:
            # Validar API key
            if not settings.HEYGEN_API_KEY:
                raise ValueError('HEYGEN_API_KEY no está configurada')
            
            client = HeyGenClient(api_key=settings.HEYGEN_API_KEY)
            
            if video.type == 'heygen_avatar_v2':
                # Validar configuración requerida V2
                if not video.config.get('avatar_id'):
                    raise ValueError('Avatar ID es requerido')
                if not video.config.get('voice_id'):
                    raise ValueError('Voice ID es requerido')
                
                response = client.generate_video(
                    script=video.script,
                    title=video.title,
                    avatar_id=video.config.get('avatar_id'),
                    voice_id=video.config.get('voice_id'),
                    has_background=video.config.get('has_background', False),
                    background_url=video.config.get('background_url'),
                    voice_speed=video.config.get('voice_speed', 1.0),
                    voice_pitch=video.config.get('voice_pitch', 50),
                    voice_emotion=video.config.get('voice_emotion', 'Excited'),
                )
            else:  # heygen_avatar_iv
                # Validar configuración requerida IV
                if not video.config.get('voice_id'):
                    raise ValueError('Voice ID es requerido')
                
                image_source = video.config.get('image_source', 'upload')
                
                if image_source == 'upload':
                    # Usuario subió nueva imagen, obtener desde GCS
                    if not video.config.get('gcs_avatar_path'):
                        raise ValueError('Imagen de avatar es requerida')
                    
                    gcs_avatar_path = video.config.get('gcs_avatar_path')
                    
                    # Obtener URL firmada del avatar desde GCS
                    logger.info(f"Obteniendo URL firmada de GCS: {gcs_avatar_path}")
                    avatar_url = gcs_storage.get_signed_url(gcs_avatar_path, expiration=600)  # 10 minutos
                    logger.info(f"URL firmada obtenida")
                    
                    # Subir imagen desde GCS a HeyGen (detecta tipo automáticamente)
                    logger.info(f"Subiendo imagen a HeyGen desde GCS (detección automática de tipo)")
                    image_key = client.upload_asset_from_url(avatar_url)
                    logger.info(f"Imagen subida exitosamente a HeyGen. Image key: {image_key}")
                    
                    # Guardar el image_key en la configuración
                    video.config['image_key'] = image_key
                    video.save()
                else:
                    # Usuario usa imagen existente, obtener image_key de la lista
                    if not video.config.get('existing_image_id'):
                        raise ValueError('ID de imagen existente es requerido')
                    
                    existing_image_id = video.config.get('existing_image_id')
                    logger.info(f"Buscando image_key para asset ID: {existing_image_id}")
                    
                    # Listar assets para encontrar el image_key
                    assets = client.list_image_assets()
                    image_key = None
                    
                    for asset in assets:
                        if asset.get('id') == existing_image_id:
                            image_key = asset.get('image_key') or asset.get('id')
                            logger.info(f"Image key encontrado: {image_key}")
                            break
                    
                    if not image_key:
                        raise ValueError(f'No se encontró el asset con ID: {existing_image_id}')
                    
                    # Guardar el image_key en la configuración
                    video.config['image_key'] = image_key
                    video.save()
                
                # Generar video con el image_key
                response = client.generate_avatar_iv_video(
                    script=video.script,
                    image_key=image_key,
                    voice_id=video.config.get('voice_id'),
                    title=video.title,
                    video_orientation=video.config.get('video_orientation', 'portrait'),
                    fit=video.config.get('fit', 'cover'),
                )
            
            # Guardar el external_id
            video.external_id = response.get('data', {}).get('video_id')
            video.save()
            
            messages.success(request, 'Video enviado a HeyGen. El proceso puede tardar varios minutos.')
            
        elif video.type == 'gemini_veo':
            if not settings.GEMINI_API_KEY:
                raise ValueError('GEMINI_API_KEY no está configurada')
            
            # Usar el modelo especificado en la configuración
            model_name = video.config.get('veo_model', 'veo-2.0-generate-001')
            logger.info(f"🎬 Usando modelo: {model_name}")
            
            client = GeminiVeoClient(api_key=settings.GEMINI_API_KEY, model_name=model_name)
            
            # Preparar storageUri para que Veo guarde directamente en nuestro bucket
            storage_uri = f"gs://{settings.GCS_BUCKET_NAME}/projects/{video.project.id}/videos/{video.id}/"
            
            # Preparar parámetros avanzados (Fase 2)
            generate_params = {
                'prompt': video.script,
                'title': video.title,
                'duration': video.config.get('duration', 8),
                'aspect_ratio': video.config.get('aspect_ratio', '16:9'),
                'sample_count': video.config.get('sample_count', 1),
                'negative_prompt': video.config.get('negative_prompt'),
                'enhance_prompt': video.config.get('enhance_prompt', True),
                'person_generation': video.config.get('person_generation', 'allow_adult'),
                'compression_quality': video.config.get('compression_quality', 'optimized'),
                'seed': video.config.get('seed'),
                'storage_uri': storage_uri,
            }
            
            # Fase 2: Imagen inicial (imagen-a-video)
            if video.config.get('input_image_gcs_uri'):
                generate_params['input_image_gcs_uri'] = video.config['input_image_gcs_uri']
                generate_params['input_image_mime_type'] = video.config.get('input_image_mime_type', 'image/jpeg')
                logger.info(f"🎨 Generando video desde imagen: {video.config['input_image_gcs_uri']}")
            
            # Fase 2: Imágenes de referencia
            if video.config.get('reference_images'):
                generate_params['reference_images'] = video.config['reference_images']
                logger.info(f"🎭 Usando {len(video.config['reference_images'])} imagen(es) de referencia")
            
            response = client.generate_video(**generate_params)
            
            video.external_id = response.get('video_id')
            video.save()
            
            logger.info(f"Video Veo 2 configurado para guardarse en: {storage_uri}")
            messages.success(request, 'Video enviado a Gemini Veo para procesamiento')
        
        logger.info(f"Video {video.id} enviado. External ID: {video.external_id}")
        
    except ValueError as e:
        logger.error(f"Error de validación: {str(e)}")
        video.mark_as_error(str(e))
        messages.error(request, f'Error de configuración: {str(e)}')
    except Exception as e:
        logger.error(f"Error al generar video: {str(e)}")
        video.mark_as_error(str(e))
        messages.error(request, f'Error al generar video: {str(e)}')
    
    return redirect('core:video_detail', video_id=video.id)


@require_http_methods(["GET"])
def video_status(request, video_id):
    """Consulta el estado de un video en la API externa"""
    video = get_object_or_404(Video, id=video_id)
    
    logger.info(f"[POLLING] Recibida consulta de estado para video ID: {video.id} (external_id: {video.external_id})")
    
    if not video.external_id:
        logger.warning(f"[POLLING] Video {video.id} no tiene external_id")
        return JsonResponse({
            'error': 'Video no tiene external_id',
            'status': video.status
        }, status=400)
    
    # Si ya está completado o con error, no consultar de nuevo
    if video.status in ['completed', 'error']:
        logger.info(f"[POLLING] Video {video.id} ya está en estado final: {video.status}")
        return JsonResponse({
            'status': video.status,
            'message': 'Video ya procesado',
            'updated_at': video.updated_at.isoformat()
        })
    
    try:
        if video.type in ['heygen_avatar_v2', 'heygen_avatar_iv']:
            if not settings.HEYGEN_API_KEY:
                logger.error("[POLLING] HEYGEN_API_KEY no configurada")
                return JsonResponse({'error': 'HEYGEN_API_KEY no configurada'}, status=400)
            
            client = HeyGenClient(api_key=settings.HEYGEN_API_KEY)
            status_data = client.get_video_status(video.external_id)
            
            api_status = status_data.get('status')
            logger.info(f"[POLLING] HeyGen responde - Video {video.id}: status={api_status}")
            
            # Actualizar estado si está completado
            if api_status == 'completed':
                video_url = status_data.get('video_url')
                logger.info(f"[POLLING] Video {video.id} completado! URL: {video_url}")
                
                if video_url:
                    try:
                        logger.info(f"[POLLING] Descargando video {video.id} desde HeyGen...")
                        gcs_path = f"projects/{video.project.id}/videos/{video.id}/final_video.mp4"
                        gcs_full_path = gcs_storage.upload_from_url(video_url, gcs_path)
                        
                        # Extraer metadata adicional
                        metadata = {
                            'duration': status_data.get('duration'),
                            'video_url_original': video_url,
                            'thumbnail': status_data.get('thumbnail'),
                            'caption_url': status_data.get('caption_url'),
                        }
                        
                        video.mark_as_completed(
                            gcs_path=gcs_full_path,
                            metadata=metadata
                        )
                        logger.info(f"[POLLING] ✅ Video {video.id} completado y guardado en GCS: {gcs_full_path}")
                    except Exception as e:
                        logger.error(f"[POLLING] ❌ Error al subir video {video.id} a GCS: {str(e)}")
                        video.mark_as_error(f"Error al subir a storage: {str(e)}")
                else:
                    logger.warning(f"[POLLING] Video {video.id} completado pero sin video_url")
            
            elif api_status == 'failed' or status_data.get('error'):
                error_msg = status_data.get('error', 'Video generation failed')
                logger.error(f"[POLLING] ❌ Video {video.id} falló: {error_msg}")
                video.mark_as_error(error_msg)
            
            elif api_status == 'processing':
                logger.info(f"[POLLING] ⏳ Video {video.id} aún procesando...")
            
        elif video.type == 'gemini_veo':
            if not settings.GEMINI_API_KEY:
                logger.error("[POLLING] GEMINI_API_KEY no configurada")
                return JsonResponse({'error': 'GEMINI_API_KEY no configurada'}, status=400)
            
            logger.info(f"[POLLING] Consultando Gemini Veo para video {video.id}")
            client = GeminiVeoClient(api_key=settings.GEMINI_API_KEY)
            status_data = client.get_video_status(video.external_id)
            
            api_status = status_data.get('status')
            logger.info(f"[POLLING] Gemini Veo responde - Video {video.id}: status={api_status}")
            
            # Actualizar estado si está completado
            if api_status == 'completed':
                video_url = status_data.get('video_url')
                all_video_urls = status_data.get('all_video_urls', [])
                num_videos = len(all_video_urls)
                
                logger.info(f"[POLLING] Video {video.id} completado! {num_videos} video(s) generado(s)")
                
                if video_url and all_video_urls:
                    try:
                        # Procesar TODOS los videos generados
                        all_gcs_paths = []
                        
                        for idx, video_data in enumerate(all_video_urls):
                            url = video_data['url']
                            logger.info(f"[POLLING] Procesando video {idx + 1}/{num_videos}...")
                            
                            # Determinar el nombre del archivo
                            if num_videos == 1:
                                filename = "video.mp4"
                            else:
                                filename = f"video_{idx + 1}.mp4"
                            
                            # Procesar según el tipo de URL
                            if url.startswith('gs://'):
                                # Verificar si ya está en nuestro bucket
                                if url.startswith(f"gs://{settings.GCS_BUCKET_NAME}/"):
                                    gcs_full_path = url
                                    logger.info(f"[POLLING]    ✅ Ya en nuestro bucket: {gcs_full_path}")
                                else:
                                    # Copiar desde bucket externo
                                    gcs_path = f"projects/{video.project.id}/videos/{video.id}/{filename}"
                                    gcs_full_path = gcs_storage.copy_from_gcs(url, gcs_path)
                                    logger.info(f"[POLLING]    ✅ Copiado: {gcs_full_path}")
                            elif url.startswith('http'):
                                gcs_path = f"projects/{video.project.id}/videos/{video.id}/{filename}"
                                gcs_full_path = gcs_storage.upload_from_url(url, gcs_path)
                                logger.info(f"[POLLING]    ✅ Descargado: {gcs_full_path}")
                            else:
                                # Base64
                                gcs_path = f"projects/{video.project.id}/videos/{video.id}/{filename}"
                                gcs_full_path = gcs_storage.upload_base64(url, gcs_path)
                                logger.info(f"[POLLING]    ✅ Guardado desde base64: {gcs_full_path}")
                            
                            all_gcs_paths.append({
                                'index': idx,
                                'gcs_path': gcs_full_path,
                                'original_url': url,
                                'mime_type': video_data.get('mime_type', 'video/mp4')
                            })
                        
                        # Metadata completa
                        metadata = {
                            'sample_count': num_videos,
                            'all_videos': all_gcs_paths,  # TODOS los videos con sus paths
                            'rai_filtered_count': status_data.get('rai_filtered_count', 0),
                            'videos_raw': status_data.get('videos', []),
                            'operation_data': status_data.get('operation_data', {}),
                        }
                        
                        # Guardar el primer video en gcs_path (compatibilidad)
                        primary_gcs_path = all_gcs_paths[0]['gcs_path']
                        
                        video.mark_as_completed(
                            gcs_path=primary_gcs_path,
                            metadata=metadata
                        )
                        
                        if num_videos > 1:
                            logger.info(f"[POLLING] ✅ {num_videos} videos completados y guardados!")
                            logger.info(f"[POLLING]    Principal: {primary_gcs_path}")
                            for i, vp in enumerate(all_gcs_paths[1:], 1):
                                logger.info(f"[POLLING]    Video {i + 1}: {vp['gcs_path']}")
                        else:
                            logger.info(f"[POLLING] ✅ Video completado: {primary_gcs_path}")
                            
                    except Exception as e:
                        logger.error(f"[POLLING] ❌ Error al procesar videos: {str(e)}")
                        video.mark_as_error(f"Error al procesar videos: {str(e)}")
                else:
                    logger.warning(f"[POLLING] Video {video.id} completado pero sin datos de video")
                    video.mark_as_error("Video completado pero sin datos de video")
            
            elif api_status == 'failed' or api_status == 'error':
                error_msg = status_data.get('error', 'Video generation failed')
                logger.error(f"[POLLING] ❌ Video {video.id} falló: {error_msg}")
                video.mark_as_error(error_msg)
            
            elif api_status == 'processing':
                logger.info(f"[POLLING] ⏳ Video {video.id} aún procesando...")
        
        return JsonResponse({
            'status': video.status,
            'external_status': status_data,
            'updated_at': video.updated_at.isoformat()
        })
        
    except Exception as e:
        logger.error(f"[POLLING] ❌ Error al consultar estado de video {video.id}: {str(e)}")
        return JsonResponse({
            'error': str(e),
            'status': video.status
        }, status=500)


# API Endpoints para AJAX

@require_http_methods(["GET"])
def api_list_avatars(request):
    """Lista avatares disponibles de HeyGen"""
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
        logger.error(f"Error al listar avatares: {str(e)}")
        return JsonResponse({
            'error': str(e),
            'avatars': []
        }, status=500)


@require_http_methods(["GET"])
def api_list_voices(request):
    """Lista voces disponibles de HeyGen"""
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
        logger.error(f"Error al listar voces: {str(e)}")
        return JsonResponse({
            'error': str(e),
            'voices': []
        }, status=500)


@require_http_methods(["GET"])
def api_list_image_assets(request):
    """Lista imágenes (assets) disponibles en HeyGen"""
    if not settings.HEYGEN_API_KEY:
        return JsonResponse({
            'error': 'HEYGEN_API_KEY no configurada',
            'assets': []
        }, status=400)
    
    try:
        client = HeyGenClient(api_key=settings.HEYGEN_API_KEY)
        assets = client.list_image_assets()
        return JsonResponse({'assets': assets})
    except Exception as e:
        logger.error(f"Error al listar image assets: {str(e)}")
        return JsonResponse({
            'error': str(e),
            'assets': []
        }, status=500)
