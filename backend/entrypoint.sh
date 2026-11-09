#!/bin/bash
set -e

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files into shared volume
python manage.py collectstatic --noinput 2>/dev/null || true

echo "Starting Django ASGI server on port 8000..."
exec daphne -b 0.0.0.0 -p 8000 "${DJANGO_ASGI_APP:-config.asgi:application}"
