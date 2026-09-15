#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# If we are using neon db directly, we don't need a render postgres db, 
# but the render.yaml includes one just in case. 
# Either way, run migrations:
python manage.py migrate

python manage.py collectstatic --no-input
