#!/usr/bin/env bash
set -e

pip install --upgrade pip setuptools wheel

# Install dependencies (Render also does this automatically, but explicit is safer)
pip install -r requirements.txt

# Collect static files for production
python manage.py collectstatic --noinput

# Apply database migrations
python manage.py migrate --noinput
