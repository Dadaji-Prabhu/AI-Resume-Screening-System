#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python -m spacy download en_core_web_sm
python manage.py collectstatic --no-input
python manage.py migrate
