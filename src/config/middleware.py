from django.shortcuts import redirect
from django.http import HttpResponse
from django.urls import reverse, NoReverseMatch
from django.contrib.auth.models import AnonymousUser


class SpaceAdminAccessMiddleware:
    """
    Middleware to restrict space admins without assigned spaces from accessing protected pages.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Skip middleware for anonymous users
        if isinstance(request.user, AnonymousUser) or not request.user.is_authenticated:
            return self.get_response(request)
        
        # Skip middleware if user doesn't have a profile
        if not hasattr(request.user, 'profile'):
            return self.get_response(request)
        
        # Skip middleware for non-space admins
        if request.user.profile.user_type != 'space_admin':
            return self.get_response(request)
        
        # Check if space admin has assigned spaces
        from service_management.models import Spaces
        has_spaces = Spaces.objects.filter(space_admins=request.user).exists()
        
        if has_spaces:
            # Space admin has assigned spaces, allow normal access
            return self.get_response(request)
        
        # At this point, user is a space admin without assigned spaces
        current_path = request.path
        
        # URLs that space admins can access even without assigned spaces
        allowed_patterns = [
            '/admin/',  # Django admin
            '/static/',  # Static files
            '/media/',   # Media files
            '/services/no-spaces-assigned/',  # No spaces assigned page
            '/core/logout/',  # Logout page
        ]
        
        # Check if current path is allowed
        if any(current_path.startswith(pattern) for pattern in allowed_patterns):
            return self.get_response(request)
        
        # Redirect to the no spaces assigned page using hardcoded URL to avoid reverse issues
        return redirect('/services/no-spaces-assigned/')
        
        # This should never be reached
        return self.get_response(request)
