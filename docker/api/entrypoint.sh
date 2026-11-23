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

echo "==> Relabeling issue_management → ticket_management if needed..."
python manage.py relabel_issue_to_ticket_app

echo "==> Repairing Issue→Ticket table names if needed..."
python manage.py repair_ticket_table_names

echo "==> Running migrations..."
python manage.py migrate --noinput

if [ "${ENVIRONMENT:-development}" = "development" ]; then
  echo "==> Skipping collectstatic (dev: WhiteNoise finders + autorefresh)"
else
  echo "==> Checking production object-storage settings..."
  python -c "
import os, sys
required = {
    'AWS_ACCESS_KEY_ID': os.environ.get('AWS_ACCESS_KEY_ID', ''),
    'AWS_SECRET_ACCESS_KEY': os.environ.get('AWS_SECRET_ACCESS_KEY', ''),
    'AWS_STORAGE_BUCKET_NAME': os.environ.get('AWS_STORAGE_BUCKET_NAME', ''),
    'AWS_S3_ENDPOINT_URL': os.environ.get('AWS_S3_ENDPOINT_URL', ''),
    'AWS_S3_CUSTOM_DOMAIN': os.environ.get('AWS_S3_CUSTOM_DOMAIN', ''),
}
placeholders = {
    'AWS_ACCESS_KEY_ID': 'aws_access_key',
    'AWS_SECRET_ACCESS_KEY': 'aws_secret_access_key',
    'AWS_STORAGE_BUCKET_NAME': 'aws_storage_bucket_name',
    'AWS_S3_ENDPOINT_URL': 'aws_s3_endpoint_url',
    'AWS_S3_CUSTOM_DOMAIN': 'aws_s3_custom_domain',
}
missing = []
for key, value in required.items():
    if not value or value == placeholders.get(key):
        missing.append(key)
if missing:
    print('FATAL: Production Spaces/S3 settings are missing or still placeholders:', ', '.join(missing), file=sys.stderr)
    print('Set real AWS_* variables on the Railway service before collectstatic can succeed.', file=sys.stderr)
    sys.exit(1)
print('Object-storage settings look set (endpoint host will be used by collectstatic).')
"

  echo "==> Collecting static files..."
  python manage.py collectstatic --noinput --clear
fi

echo "==> Starting server..."
exec "$@"
