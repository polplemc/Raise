import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")  # <-- change myproject

django.setup()

from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError

User = get_user_model()

username = "adminapple"
email = "raiseadmin@gmail.com"
password = "123451113"

try:
    User.objects.create_superuser(username=username, email=email, password=password)
    print("Superuser created successfully")
except IntegrityError:
    print("Superuser already exists")
