from django.contrib.auth.models import AnonymousUser


class SpaceContextMiddleware:
    """
    Middleware to automatically add space context to requests for space admins.
    This eliminates the need to add space context logic to every view.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Add space context before processing the request
        self.add_space_context(request)
        
        # Process the request
        response = self.get_response(request)
        
        return response
    
    def add_space_context(self, request):
        """Add space-related context to the request for space admins"""
        # Skip for anonymous users
        if isinstance(request.user, AnonymousUser) or not request.user.is_authenticated:
            return
        
        # Skip if user doesn't have a profile
        if not hasattr(request.user, 'profile'):
            return
        
        # Initialize space context variables
        request.selected_space = None
        request.space_settings = None
        request.user_spaces = None
        
        # Handle space context for space admins
        if request.user.profile.user_type == 'space_admin':
            request.user_spaces = request.user.administered_spaces.all()
            request.selected_space = request.user.profile.current_active_space
            
            # If no active space is set or user can't access it, set to first available
            if not request.selected_space or not request.user_spaces.filter(id=request.selected_space.id).exists():
                if request.user_spaces.exists():
                    request.selected_space = request.user_spaces.first()
                    # Update the user's profile with the new active space
                    request.user.profile.switch_active_space(request.selected_space)
            
            # Set space settings if we have a selected space
            if request.selected_space:
                request.space_settings = request.selected_space.settings
        
        # Handle space context for central admins (for space filtering)
        elif request.user.profile.user_type == 'central_admin':
            # For central admin, check if filtering by specific space
            space_filter = request.GET.get('space_filter')
            if space_filter and space_filter != 'no_space':
                try:
                    from service_management.models import Spaces
                    from core.models import Organisation
                    
                    # Get organisations managed by this central admin
                    orgs = Organisation.objects.filter(central_admins=request.user)
                    request.selected_space = Spaces.objects.get(slug=space_filter, org__in=orgs)
                    request.space_settings = request.selected_space.settings
                except Spaces.DoesNotExist:
                    pass
