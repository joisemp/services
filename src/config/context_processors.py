"""
Context processors for making space context available in templates.
"""

def space_context(request):
    """
    Context processor to make space context available in templates.
    This works together with SpaceContextMiddleware.
    """
    context = {}
    
    # Add space context if it exists on the request
    if hasattr(request, 'selected_space'):
        context['selected_space'] = request.selected_space
    
    if hasattr(request, 'space_settings'):
        context['space_settings'] = request.space_settings
        
    if hasattr(request, 'user_spaces'):
        context['user_spaces'] = request.user_spaces
    
    return context
