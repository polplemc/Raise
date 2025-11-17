#!/usr/bin/env bash
set -e

# Upgrade pip and install dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Collect static files and migrate DB
python myproject/manage.py collectstatic --noinput
python myproject/manage.py migrate --noinput
