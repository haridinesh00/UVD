#!/usr/bin/env bash
# Exit on error
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate

# Create the superuser automatically using the environment variables
python manage.py createsuperuser --noinput || true