from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from issue_management.models import Issue

class FocusModeMiddleware:
    """
    Middleware to enforce focus mode for maintainers working on issues.
    When a maintainer has an issue in progress, they are restricted to focus mode
    unless they are performing allowed actions (pause, escalate, resolve).
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URLs that are allowed when in focus mode
        self.allowed_patterns = [
            'issue_management:focus_mode',
            'issue_management:change_status_with_comment',
            'issue_management:change_status',
            'issue_management:escalate_issue',
            'issue_management:issue_detail',  # For comment submission
            'admin:logout',  # Allow logout
            'core:logout',   # Allow logout
        ]
        
        # URL paths that are allowed (for static files, etc.)
        self.allowed_paths = [
            '/static/',
            '/media/',
            '/admin/logout/',
            '/logout/',
        ]
    
    def __call__(self, request):
        # Only apply to authenticated users with profiles
        if (request.user.is_authenticated and 
            hasattr(request.user, 'profile') and 
            request.user.profile.user_type == 'maintainer'):
            
            # Check if maintainer has an issue in progress
            in_progress_issue = Issue.objects.filter(
                maintainer=request.user,
                status='in_progress'
            ).first()
            
            # Also check if we're in the middle of a status change operation
            # by checking if this is a redirect after a form submission
            is_post_status_change = (
                request.method == 'GET' and 
                request.META.get('HTTP_REFERER') and 
                'change-status' in request.META.get('HTTP_REFERER', '')
            )
            
            if in_progress_issue and not is_post_status_change:
                current_url = request.resolver_match
                current_path = request.path
                
                # Allow POST requests to status change endpoints (these are pause/resolve actions)
                if (request.method == 'POST' and current_url and 
                    current_url.url_name in ['change_status_with_comment', 'change_status'] and
                    current_url.namespace == 'issue_management'):
                    # Clear any focus session when pausing/resolving
                    if 'focus_start_time' in request.session:
                        del request.session['focus_start_time']
                    # Let the POST request proceed without interference
                    pass
                else:
                    # Check if current URL is allowed for GET requests
                    is_allowed = False
                    
                    # Check against allowed patterns
                    if current_url:
                        url_name = f"{current_url.namespace}:{current_url.url_name}" if current_url.namespace else current_url.url_name
                        if url_name in self.allowed_patterns:
                            is_allowed = True
                        
                        # Also allow the specific issue detail page for the in-progress issue
                        if (current_url.url_name == 'issue_detail' and 
                            current_url.namespace == 'issue_management' and
                            current_url.kwargs.get('slug') == in_progress_issue.slug):
                            is_allowed = True
                        
                        # Allow status change actions for the current in-progress issue
                        if (current_url.url_name in ['change_status_with_comment', 'change_status'] and 
                            current_url.namespace == 'issue_management' and
                            current_url.kwargs.get('slug') == in_progress_issue.slug):
                            is_allowed = True
                    
                    # Check against allowed paths
                    for allowed_path in self.allowed_paths:
                        if current_path.startswith(allowed_path):
                            is_allowed = True
                            break
                    
                    # If not allowed and not already in focus mode, redirect to focus mode
                    if not is_allowed:
                        focus_url = reverse('issue_management:focus_mode', kwargs={'slug': in_progress_issue.slug})
                        if current_path != focus_url:
                            # Clean up the title for display (handle encoding issues)
                            clean_title = str(in_progress_issue.title).strip().replace('"', '').replace(';', '')
                            messages.warning(
                                request, 
                                f'You are currently working on "{clean_title}". '
                                f'Please complete, pause, or escalate it before accessing other pages.'
                            )
                            return redirect(focus_url)
        
        response = self.get_response(request)
        return response
