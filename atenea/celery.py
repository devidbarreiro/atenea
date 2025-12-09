"""
Celery configuration for Atenea
"""
import os
from celery import Celery

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'atenea.settings')

app = Celery('atenea')

# Load config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    """Task de debug para verificar que Celery funciona"""
    print(f'Request: {self.request!r}')







