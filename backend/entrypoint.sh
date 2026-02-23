#!/bin/sh
set -e

cd /app/backend

python manage.py migrate --noinput
python manage.py seed_data

exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
