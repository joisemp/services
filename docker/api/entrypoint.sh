#!/bin/sh
set -e

echo "==> Waiting for database..."
i=0
until python -c "
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '${DJANGO_SETTINGS_MODULE:-config.settings}')
django.setup()
from django.db import connection
connection.ensure_connection()
print('Database is ready.')
"; do
  i=$((i + 1))
  if [ "$i" -ge 30 ]; then
    echo "==> Gave up waiting for the database after ${i} attempts."
    exit 1
  fi
  echo "Database not ready — retrying in 2s... (attempt ${i}/30)"
  sleep 2
done

echo "==> Running migrations..."
python manage.py migrate --noinput

if [ "${ENVIRONMENT:-development}" = "development" ]; then
  echo "==> Skipping collectstatic (dev: WhiteNoise finders + autorefresh)"
else
  echo "==> Collecting static files..."
  python manage.py collectstatic --noinput --clear
fi

echo "==> Starting server..."
exec "$@"
