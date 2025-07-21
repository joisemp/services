from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
from core.models import UserProfile
from service_management.models import Spaces

@login_required
def dashboard_view(request):
    # Simplified access check - just verify user has profile
    if not hasattr(request.user, 'profile'):
        return HttpResponseForbidden('Access denied - no profile found.')
    
    user = request.user
    user_type = getattr(user.profile, 'user_type', None)
    
    # Space context handling for space admins
    selected_space = None
    if user_type == 'space_admin':
        user_spaces = user.administered_spaces.all()
        
        # Use the current active space from profile, or set to first available space
        selected_space = user.profile.current_active_space
        
        # If no active space is set or user can't access it, set to first available
        if not selected_space or not user_spaces.filter(id=selected_space.id).exists():
            if user_spaces.exists():
                selected_space = user_spaces.first()
                # Update profile with the new active space
                user.profile.switch_active_space(selected_space)
    
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


@login_required
@require_POST
def switch_space(request):
    """Handle space switching for space admins"""
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'space_admin':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    space_slug = request.POST.get('space_slug')
    if not space_slug:
        return JsonResponse({'success': False, 'error': 'Space slug required'}, status=400)
    
    try:
        # Get the space and verify the user can administer it
        space = get_object_or_404(Spaces, slug=space_slug)
        
        if request.user.profile.can_administer_space(space):
            # Switch the active space in the user's profile
            success = request.user.profile.switch_active_space(space)
            if success:
                return JsonResponse({
                    'success': True, 
                    'space_name': space.name,
                    'space_slug': space.slug
                })
            else:
                return JsonResponse({'success': False, 'error': 'Failed to switch space'}, status=400)
        else:
            return JsonResponse({'success': False, 'error': 'Cannot access this space'}, status=403)
            
    except Spaces.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Space not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
