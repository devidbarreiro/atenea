# Script para ejecutar Celery Worker en Windows con thread pool
# Evita problemas de billiard multiprocessing en Windows

# Activar entorno virtual si existe
if (Test-Path "venv\Scripts\Activate.ps1") {
    & "venv\Scripts\Activate.ps1"
}

# Ejecutar worker con thread pool (Windows-compatible)
# --pool=threads: Usa threading pool en lugar de multiprocessing
celery -A atenea worker `
    --loglevel=info `
    --queues=video_generation,image_generation,audio_generation,scene_processing,default,polling_tasks,maintenance `
    --concurrency=4 `
    --pool=threads
