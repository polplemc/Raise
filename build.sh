#!/usr/bin/env bash
set -e

# Upgrade pip, setuptools, wheel
pip install --upgrade pip setuptools wheel

# Install dependencies
pip install -r requirements.txt

# Collect static files
python myproject/manage.py collectstatic --noinput

# Apply migrations
python myproject/manage.py migrate --noinput
