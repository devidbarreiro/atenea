#!/usr/bin/env python
"""
Script para limpiar completamente Celery y Redis.
Uso: python scripts/clean_celery.py

Limpia:
- Todas las keys de Celery/Kombu en Redis
- Todas las tareas en django_celery_results
- Todas las tareas periódicas en django_celery_beat
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'atenea.settings')
django.setup()

import redis
from django_celery_results.models import TaskResult
from django_celery_beat.models import PeriodicTask

def clean_redis():
    """Limpiar todas las keys de Celery/Kombu en Redis"""
    print("🔴 Limpiando Redis...")
    r = redis.Redis(host='localhost', port=6379)
    
    try:
        # Ping para verificar conexión
        r.ping()
    except redis.ConnectionError:
        print("❌ Error: No se puede conectar a Redis en localhost:6379")
        print("   Asegúrate de que Redis está corriendo.")
        return False
    
    count = 0
    for key in r.scan_iter('*'):
        if b'celery' in key or b'kombu' in key:
            r.delete(key)
            count += 1
    
    print(f"  ✅ Eliminadas {count} keys de Celery/Kombu")
    return True

def clean_django_db():
    """Limpiar tareas en django_celery_results y django_celery_beat"""
    print("\n💾 Limpiando BD de Django...")
    
    # Limpiar TaskResult
    count_tasks = TaskResult.objects.all().count()
    TaskResult.objects.all().delete()
    print(f"  ✅ Eliminadas {count_tasks} tareas de django_celery_results")
    
    # Limpiar PeriodicTask
    count_periodic = PeriodicTask.objects.all().count()
    PeriodicTask.objects.all().delete()
    print(f"  ✅ Eliminadas {count_periodic} tareas periódicas de django_celery_beat")

def verify_clean():
    """Verificar que todo está limpio"""
    print("\n✓ Verificando limpieza...")
    
    r = redis.Redis(host='localhost', port=6379)
    remaining = len(list(r.scan_iter('celery*')))
    print(f"  Keys de celery en Redis: {remaining}")
    
    task_count = TaskResult.objects.count()
    print(f"  Tareas en django_celery_results: {task_count}")
    
    periodic_count = PeriodicTask.objects.count()
    print(f"  Tareas periódicas en django_celery_beat: {periodic_count}")
    
    if remaining == 0 and task_count == 0 and periodic_count == 0:
        print("\n✅ Celery está completamente limpio")
        return True
    else:
        print("\n⚠️  Todavía hay datos residuales")
        return False

if __name__ == '__main__':
    print("=" * 50)
    print("🧹 Limpiador de Celery")
    print("=" * 50)
    
    try:
        redis_ok = clean_redis()
        if not redis_ok:
            sys.exit(1)
        
        clean_django_db()
        
        verify_clean()
        
        print("\n" + "=" * 50)
        print("✨ ¡Listo! Celery ha sido completamente limpiado")
        print("=" * 50)
        print("\n💡 Próximos pasos:")
        print("   1. Reinicia tu worker de Celery:")
        print("      celery -A atenea worker --loglevel=info")
        print("   2. Reinicia tu servidor Django:")
        print("      python manage.py runserver")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
