# core/apps.py
from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.contrib.auth import get_user_model
import os

class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        def create_superuser(sender, **kwargs):
            User = get_user_model()
            username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
            email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
            password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

            if username and password and not User.objects.filter(username=username).exists():
                print("Creating superuser...")  # debug
                User.objects.create_superuser(username=username, email=email, password=password)

        post_migrate.connect(create_superuser, sender=self)
