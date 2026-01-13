#!/usr/bin/env bash
# Script de inicialización para Docker que ejecuta migraciones antes de iniciar Daphne
# Exit on error
set -o errexit

# Función para esperar a que la base de datos esté lista
# Usamos una verificación simple de conexión a través de Django
wait_for_db() {
    echo "⏳ Esperando a que la base de datos esté lista..."
    timeout=60
    elapsed=0
    while [ $elapsed -lt $timeout ]; do
        # Intentar una conexión simple a la base de datos
        if python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'atenea.settings')
django.setup()
from django.db import connection
connection.ensure_connection()
" > /dev/null 2>&1; then
            echo "✅ Base de datos lista"
            return 0
        fi
        echo "⏳ Esperando base de datos... ($elapsed/$timeout segundos)"
        sleep 2
        elapsed=$((elapsed + 2))
    done
    echo "❌ Error: La base de datos no está lista después de $timeout segundos"
    return 1
}

# Esperar a que la base de datos esté lista
if ! wait_for_db; then
    exit 1
fi

echo "🔄 Ejecutando migraciones de Django..."
# Ejecutar migraciones con manejo de errores mejorado
# Usar --run-syncdb para asegurar que todas las tablas estén creadas
if python manage.py migrate --noinput --run-syncdb; then
    echo "✅ Migraciones completadas exitosamente"
else
    echo "❌ Error: Falló la ejecución de migraciones"
    # En producción, es mejor fallar que continuar con migraciones incompletas
    exit 1
fi

echo "✅ Migraciones completadas. Iniciando servidor Daphne..."
# Ejecutar el comando pasado como argumentos
exec "$@"
