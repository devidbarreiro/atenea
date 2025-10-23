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
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements y instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar gunicorn para producción
RUN pip install gunicorn==21.2.0

# Copiar el proyecto
COPY . .

# Crear directorios necesarios
RUN mkdir -p logs static media temp_uploads && \
    chmod -R 755 logs static media temp_uploads

# Crear usuario no-root
RUN useradd -m -u 1000 django && \
    chown -R django:django /app

USER django

# Exponer puerto
EXPOSE 8000

# Comando de inicio (puede ser sobrescrito en docker-compose)
CMD ["gunicorn", "atenea.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]

