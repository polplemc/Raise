from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User


class EmailBackend(ModelBackend):
    """
    Custom authentication backend that allows users to login with email instead of username.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Try to find user by email
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            # Try to find user by username (for superusers created with createsuperuser)
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return None
        
        # Check password
        if user.check_password(password):
            return user
        return None
