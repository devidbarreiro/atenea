"""
URL configuration for atenea project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from pathlib import Path


def serve_favicon(request):
    """Sirve el favicon directamente (funciona con Daphne y runserver)"""
    favicon_path = Path(settings.BASE_DIR) / 'static' / 'img' / 'logos' / 'favicon.ico'
    if favicon_path.exists():
        # Leer el archivo en memoria para evitar file descriptor leak
        from django.http import HttpResponse
        with open(favicon_path, 'rb') as f:
            return HttpResponse(f.read(), content_type='image/x-icon')
    from django.http import HttpResponseNotFound
    return HttpResponseNotFound()


urlpatterns = [
    # Favicon en raíz (navegadores lo piden en /favicon.ico)
    path('favicon.ico', serve_favicon),
    path('', include('core.urls')),
    path('admin/', admin.site.urls),
]

# Hot reload en desarrollo (opcional)
if settings.DEBUG:
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]
    # Servir archivos estáticos en desarrollo
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()
