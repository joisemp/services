#!/bin/sh
set -e

echo "==> Waiting for database..."
until python -c "
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '${DJANGO_SETTINGS_MODULE:-config.settings}')
django.setup()
from django.db import connection
connection.ensure_connection()
print('Database is ready.')
" 2>/dev/null; do
  echo "Database not ready — retrying in 2s..."
  sleep 2
done

echo "==> Running migrations..."
python manage.py migrate --noinput

echo "==> Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "==> Starting server..."
exec "$@"
