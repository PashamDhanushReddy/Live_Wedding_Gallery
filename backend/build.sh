#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

echo "=== [Render Build] Upgrading Pip & Installing Dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== [Render Build] Running Database Migrations on NeonDB ==="
python manage.py migrate --no-input

echo "=== [Render Build] Collecting Static Files for WhiteNoise ==="
python manage.py collectstatic --no-input --clear

echo "=== [Render Build] Running Django Deployment Verification ==="
python manage.py check

echo "=== [Render Build] Build Completed Successfully ==="
