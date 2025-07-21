from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponseForbidden
from core.models import UserProfile

@login_required
def dashboard_view(request):
    slug = request.GET.get('user')
    if not slug or not hasattr(request.user, 'profile') or request.user.profile.slug != slug:
        return HttpResponseForbidden('You are not allowed to access this dashboard.')
    user = request.user
    user_type = getattr(user.profile, 'user_type', None)
    
    # Space context handling for space admins
    selected_space = None
    if user_type == 'space_admin':
        space_slug = request.GET.get('space_slug')
        user_spaces = user.administered_spaces.all()
        
        if space_slug:
            try:
                selected_space = user_spaces.get(slug=space_slug)
            except:
                selected_space = user_spaces.first() if user_spaces.exists() else None
        else:
            selected_space = user_spaces.first() if user_spaces.exists() else None
    
    template_map = {
        'central_admin': 'dashboard/dashboard_central_admin.html',
        'institution_admin': 'dashboard/dashboard_institution_admin.html',
        'departement_incharge': 'dashboard/dashboard_departement_incharge.html',
        'room_incharge': 'dashboard/dashboard_room_incharge.html',
        'space_admin': 'dashboard/dashboard_space_admin.html',
        'maintainer': 'dashboard/dashboard_maintainer.html',
        'general_user': 'dashboard/dashboard_general_user.html',
    }
    context_map = {
        'central_admin': {'user': user, 'user_type': user_type, 'admin_message': 'Central admin specific context.'},
        'institution_admin': {'user': user, 'user_type': user_type, 'institution_message': 'Institution admin context.'},
        'departement_incharge': {'user': user, 'user_type': user_type, 'department_message': 'Department incharge context.'},
        'room_incharge': {'user': user, 'user_type': user_type, 'room_message': 'Room incharge context.'},
        'space_admin': {
            'user': user, 
            'user_type': user_type, 
            'space_admin_message': 'Space admin context.',
            'selected_space': selected_space,
            'user_spaces': user.administered_spaces.all() if user_type == 'space_admin' else None,
            'space_settings': selected_space.settings if selected_space else None
        },
        'maintainer': {'user': user, 'user_type': user_type, 'maintainer_message': 'Maintainer context.'},
        'general_user': {'user': user, 'user_type': user_type, 'general_message': 'General user context.'},
    }
    template = template_map.get(user_type, 'dashboard/dashboard.html')
    context = context_map.get(user_type, {'user': user, 'user_type': user_type})
    return render(request, template, context)
