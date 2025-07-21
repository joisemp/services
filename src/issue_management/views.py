from django.shortcuts import render, redirect, get_object_or_404
from .models import Issue, IssueImage
from .forms import IssueForm, IssueAssignmentForm
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

from django.shortcuts import render, redirect, get_object_or_404
from .models import Issue, IssueImage
from .forms import IssueForm, IssueAssignmentForm
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

def issue_list(request):
    # Initialize default values
    issues = Issue.objects.none()
    assigned_count = 0
    my_issues_count = 0
    selected_space = None
    space_settings = None
    user_spaces = None
    
    if not request.user.is_authenticated or not hasattr(request.user, 'profile'):
        # Anonymous users see no issues
        issues = Issue.objects.none()
    elif request.user.profile.user_type == 'central_admin':
        # Central admin sees all issues from their organization
        issues = Issue.objects.filter(org=request.user.profile.org).order_by('-created_at')
        
        # Handle space filter for central admin
        space_filter = request.GET.get('space_filter')
        if space_filter:
            try:
                from service_management.models import Spaces
                filtered_space = Spaces.objects.get(slug=space_filter, org=request.user.profile.org)
                issues = issues.filter(space=filtered_space)
                selected_space = filtered_space  # Show which space is being filtered
            except Spaces.DoesNotExist:
                pass  # Invalid filter, show all issues
        elif space_filter == 'no_space':
            # Filter for issues without space assignment
            issues = issues.filter(space__isnull=True)
        
    elif request.user.profile.user_type == 'space_admin':
        # Space admin sees issues from their managed spaces
        user_spaces = request.user.administered_spaces.all()
        selected_space = request.user.profile.current_active_space
        
        # If no active space is set or user can't access it, set to first available
        if not selected_space or not user_spaces.filter(id=selected_space.id).exists():
            if user_spaces.exists():
                selected_space = user_spaces.first()
                request.user.profile.switch_active_space(selected_space)
        
        if selected_space:
            space_settings = selected_space.settings
            # Filter issues by the selected space
            issues = Issue.objects.filter(space=selected_space).order_by('-created_at')
        else:
            # No spaces available
            issues = Issue.objects.none()
            
    elif request.user.profile.user_type == 'maintainer':
        # Maintainer sees only assigned issues
        issues = Issue.objects.filter(maintainer=request.user).order_by('-created_at')
        
    else:
        # Regular users see issues they created from their organization
        issues = Issue.objects.filter(
            created_by=request.user,
            org=request.user.profile.org
        ).order_by('-created_at')
    
    # Calculate statistics based on filtered issues
    assigned_count = issues.filter(maintainer__isnull=False).count()
    pending_count = issues.filter(maintainer__isnull=True).count()
    
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        if request.user.profile.user_type == 'maintainer':
            my_issues_count = issues.filter(maintainer=request.user).count()
        else:
            my_issues_count = issues.filter(created_by=request.user).count()
    
    context = {
        'issues': issues,
        'assigned_count': assigned_count,
        'pending_count': pending_count,
        'my_issues_count': my_issues_count,
        'selected_space': selected_space,
        'space_settings': space_settings,
        'user_spaces': user_spaces,
    }
    
    return render(request, 'issue_management/issue_list.html', context)

def report_issue(request):
    if request.method == 'POST':
        form = IssueForm(request.POST, request.FILES, user=request.user if request.user.is_authenticated else None)
        images = request.FILES.getlist('image')
        if len(images) > 3:
            form.add_error('image', 'You can upload a maximum of 3 images.')
        if form.is_valid():
            issue = form.save(commit=False)
            # Assign organisation and space if user is authenticated and has a profile
            if request.user.is_authenticated and hasattr(request.user, 'profile'):
                issue.org = request.user.profile.org
                issue.created_by = request.user
                
                # Set space based on user type and context
                if request.user.profile.user_type == 'space_admin':
                    # For space admin, use their current active space
                    if request.user.profile.current_active_space:
                        issue.space = request.user.profile.current_active_space
                elif request.user.profile.user_type == 'central_admin':
                    # For central admin, use space from form if selected
                    if form.cleaned_data.get('space'):
                        issue.space = form.cleaned_data['space']
                    # If no space selected, leave it as None (optional)
                        
            issue.save()
            # Handle multiple images (limit to 3)
            for img in images[:3]:
                IssueImage.objects.create(issue=issue, image=img)
            return redirect('issue_management:issue_list')
    else:
        form = IssueForm(user=request.user if request.user.is_authenticated else None)
                
    return render(request, 'issue_management/report_issue.html', {'form': form})

def voice_record(request):
    return render(request, 'issue_management/voice_record.html')

def assign_issue(request, issue_slug):
    issue = get_object_or_404(Issue, slug=issue_slug)
    if not request.user.is_authenticated or not hasattr(request.user, 'profile') or request.user.profile.user_type != 'central_admin':
        return HttpResponseForbidden('You do not have permission to assign issues.')
    if request.method == 'POST':
        form = IssueAssignmentForm(request.POST, instance=issue)
        if form.is_valid():
            form.save()
            return redirect('issue_management:issue_list')
    else:
        form = IssueAssignmentForm(instance=issue)
    return render(request, 'issue_management/assign_issue.html', {'form': form, 'issue': issue})
