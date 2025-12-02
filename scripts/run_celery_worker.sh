#!/bin/bash
# Script para ejecutar Celery Worker con todas las colas necesarias

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Ejecutar worker con todas las colas
celery -A atenea worker --loglevel=info \
    --queues=video_generation,image_generation,audio_generation,scene_processing,default,polling_tasks,maintenance \
    --concurrency=4




