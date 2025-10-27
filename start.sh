#!/usr/bin/env bash
# Exit on error
set -o errexit

# Run migrations
python manage.py migrate

# Start the application
gunicorn atenea.wsgi:application --bind 0.0.0.0:$PORT
