#!/bin/bash
# Script para ejecutar el servidor de desarrollo con soporte WebSocket usando Daphne

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Ejecutar con Daphne (soporta HTTP y WebSocket)
daphne -b 0.0.0.0 -p 8000 atenea.asgi:application

