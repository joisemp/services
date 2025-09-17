from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


class DualAuthBackend(BaseBackend):
    """
    Custom authentication backend that supports both:
    1. Phone-only authentication for general users (passwordless)
    2. Email + password authentication for other user types
    """
    
    def authenticate(self, request, username=None, password=None, phone_number=None, **kwargs):
        """
        Authenticate user based on their auth_method
        """
        try:
            if phone_number:
                # Phone authentication for general users (passwordless)
                user = User.objects.get(
                    phone_number=phone_number,
                    auth_method='phone',
                    user_type='general_user',
                    is_active=True
                )
                # For phone authentication, no password check needed
                return user
                
            elif username and password:
                # Email + password authentication for other user types
                user = User.objects.get(
                    email=username,
                    auth_method='email',
                    is_active=True
                )
                # Check if user has a usable password and it matches
                if user.check_password(password) and user.has_usable_password():
                    return user
                    
        except User.DoesNotExist:
            # No user found with given credentials
            return None
        except User.MultipleObjectsReturned:
            # Multiple users found (shouldn't happen with unique constraints)
            return None
            
        return None
    
    def get_user(self, user_id):
        """
        Get user by ID for session authentication
        """
        try:
            return User.objects.get(pk=user_id, is_active=True)
        except User.DoesNotExist:
            return None


class PhoneAuthBackend(BaseBackend):
    """
    Simplified phone-only authentication backend for general users
    """
    
    def authenticate(self, request, phone_number=None, **kwargs):
        """
        Authenticate general users with phone number only
        """
        if not phone_number:
            return None
            
        try:
            user = User.objects.get(
                phone_number=phone_number,
                auth_method='phone',
                user_type='general_user',
                is_active=True
            )
            return user
        except User.DoesNotExist:
            return None
    
    def get_user(self, user_id):
        """
        Get user by ID for session authentication
        """
        try:
            return User.objects.get(pk=user_id, is_active=True)
        except User.DoesNotExist:
            return None


class EmailAuthBackend(BaseBackend):
    """
    Email + password authentication backend for non-general users
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate non-general users with email + password
        """
        if not username or not password:
            return None
            
        try:
            user = User.objects.get(
                email=username,
                auth_method='email',
                is_active=True
            )
            # Exclude general users from email authentication
            if user.user_type == 'general_user':
                return None
                
            # Check password
            if user.check_password(password) and user.has_usable_password():
                return user
                
        except User.DoesNotExist:
            return None
            
        return None
    
    def get_user(self, user_id):
        """
        Get user by ID for session authentication
        """
        try:
            return User.objects.get(pk=user_id, is_active=True)
        except User.DoesNotExist:
            return None