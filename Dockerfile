# Usar Python 3.11 slim como base
FROM python:3.11-slim

# Variables de entorno para Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    ffmpeg \
    postgresql-client \
    libpq-dev \
    pkg-config \
    python3-dev \
    libcairo2-dev \
    libpango1.0-dev \
    libpangocairo-1.0-0 \
    libgirepository1.0-dev \
    gir1.2-pango-1.0 \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements y instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar gunicorn y daphne para producción
# Gunicorn se mantiene para compatibilidad, pero Daphne es necesario para WebSockets y ASGI
RUN pip install gunicorn==21.2.0
# Daphne ya está en requirements.txt, pero lo mencionamos aquí para claridad

# Copiar el proyecto
COPY . .

# Crear directorios necesarios
RUN mkdir -p logs static media temp_uploads && \
    chmod -R 755 logs static media temp_uploads

# Dar permisos de ejecución a los scripts
RUN chmod +x scripts/*.sh start.sh 2>/dev/null || true

# Crear usuario no-root
RUN useradd -m -u 1000 django && \
    chown -R django:django /app

USER django

# Exponer puerto
EXPOSE 8000

# Comando de inicio (puede ser sobrescrito en docker-compose)
CMD ["gunicorn", "atenea.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]

