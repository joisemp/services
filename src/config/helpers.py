from functools import wraps
from django.shortcuts import redirect
from django.urls import reverse


def is_central_admin(user):
    return hasattr(user, 'profile') and user.profile.user_type == 'central_admin'


def is_space_admin(user):
    """Check if user is a space admin"""
    return hasattr(user, 'profile') and user.profile.user_type == 'space_admin'


def has_assigned_spaces(user):
    """Check if a space admin has any assigned spaces"""
    if not is_space_admin(user):
        return True  # Non-space admins don't need space assignments
    
    # Check if user is assigned to any spaces
    from service_management.models import Spaces
    return Spaces.objects.filter(space_admins=user).exists()


def space_admin_has_access(user):
    """Check if space admin has access (either has assigned spaces or is not a space admin)"""
    if not is_space_admin(user):
        return True  # Non-space admins have normal access
    return has_assigned_spaces(user)