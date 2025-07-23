from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone

from .models import Issue, IssueImage, IssueCategory, IssueComment, IssueStatusHistory
from .forms import IssueForm, IssueAssignmentForm, IssueUpdateForm, IssueCommentForm, IssueCategoryForm

def issue_list(request):
    # Initialize default values
    issues = Issue.objects.none()
    assigned_count = 0
    my_issues_count = 0
    selected_space = None
    space_settings = None
    user_spaces = None
    
    # Filter parameters
    status_filter = request.GET.get('status')
    priority_filter = request.GET.get('priority')
    category_filter = request.GET.get('category')
    search = request.GET.get('search')
    
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
    
    # Apply additional filters
    if status_filter:
        issues = issues.filter(status=status_filter)
    if priority_filter:
        issues = issues.filter(priority=priority_filter)
    if category_filter:
        try:
            category = IssueCategory.objects.get(slug=category_filter, org=request.user.profile.org)
            issues = issues.filter(category=category)
        except IssueCategory.DoesNotExist:
            pass
    if search:
        issues = issues.filter(
            Q(title__icontains=search) | 
            Q(description__icontains=search)
        )
    
    # Calculate statistics based on filtered issues (before additional filters)
    base_issues = Issue.objects.filter(org=request.user.profile.org) if request.user.is_authenticated and hasattr(request.user, 'profile') else Issue.objects.none()
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        if request.user.profile.user_type == 'space_admin' and selected_space:
            base_issues = Issue.objects.filter(space=selected_space)
        elif request.user.profile.user_type == 'maintainer':
            base_issues = Issue.objects.filter(maintainer=request.user)
        elif request.user.profile.user_type not in ['central_admin']:
            base_issues = Issue.objects.filter(created_by=request.user, org=request.user.profile.org)
    
    assigned_count = base_issues.filter(maintainer__isnull=False).count()
    pending_count = base_issues.filter(status='open').count()
    in_progress_count = base_issues.filter(status='in_progress').count()
    resolved_count = base_issues.filter(status='resolved').count()
    
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        if request.user.profile.user_type == 'maintainer':
            my_issues_count = base_issues.filter(maintainer=request.user).count()
        else:
            my_issues_count = base_issues.filter(created_by=request.user).count()
    
    # Get categories for filter dropdown
    categories = IssueCategory.objects.filter(
        org=request.user.profile.org, 
        is_active=True
    ).order_by('name') if request.user.is_authenticated and hasattr(request.user, 'profile') else []
    
    context = {
        'issues': issues,
        'assigned_count': assigned_count,
        'pending_count': pending_count,
        'in_progress_count': in_progress_count,
        'resolved_count': resolved_count,
        'my_issues_count': my_issues_count,
        'selected_space': selected_space,
        'space_settings': space_settings,
        'user_spaces': user_spaces,
        'categories': categories,
        'current_filters': {
            'status': status_filter,
            'priority': priority_filter,
            'category': category_filter,
            'search': search,
        }
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
            
            messages.success(request, f'Issue "{issue.title}" has been reported successfully.')
            return redirect('issue_management:issue_detail', slug=issue.slug)
    else:
        form = IssueForm(user=request.user if request.user.is_authenticated else None)
                
    return render(request, 'issue_management/report_issue.html', {'form': form})

def issue_detail(request, slug):
    """View detailed information about an issue"""
    issue = get_object_or_404(Issue, slug=slug)
    
    # Check permissions
    if not request.user.is_authenticated or not hasattr(request.user, 'profile'):
        return HttpResponseForbidden('You must be logged in to view issues.')
    
    user_profile = request.user.profile
    can_view = False
    can_edit = False
    can_comment = False
    
    # Permission checks
    if user_profile.user_type == 'central_admin' and issue.org == user_profile.org:
        can_view = can_edit = can_comment = True
    elif user_profile.user_type == 'space_admin':
        if issue.space and issue.space in request.user.administered_spaces.all():
            can_view = can_comment = True
    elif user_profile.user_type == 'maintainer':
        if issue.maintainer == request.user:
            can_view = can_edit = can_comment = True
        elif issue.org == user_profile.org:
            can_view = can_comment = True
    elif issue.created_by == request.user:
        can_view = can_comment = True
    
    if not can_view:
        return HttpResponseForbidden('You do not have permission to view this issue.')
    
    # Handle comment submission
    if request.method == 'POST' and can_comment:
        comment_form = IssueCommentForm(request.POST, user=request.user)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.issue = issue
            comment.author = request.user
            comment.save()
            messages.success(request, 'Comment added successfully.')
            return redirect('issue_management:issue_detail', slug=slug)
    else:
        comment_form = IssueCommentForm(user=request.user) if can_comment else None
    
    # Get comments (filter internal comments based on user type)
    comments = issue.comments.all()
    if user_profile.user_type not in ['maintainer', 'central_admin']:
        comments = comments.filter(is_internal=False)
    
    # Get status history
    status_history = issue.status_history.all()[:10]  # Last 10 changes
    
    context = {
        'issue': issue,
        'can_edit': can_edit,
        'can_comment': can_comment,
        'comment_form': comment_form,
        'comments': comments,
        'status_history': status_history,
    }
    
    return render(request, 'issue_management/issue_detail.html', context)

@login_required
def update_issue(request, slug):
    """Update issue status and details"""
    issue = get_object_or_404(Issue, slug=slug)
    
    # Check permissions
    if not hasattr(request.user, 'profile'):
        return HttpResponseForbidden('Access denied.')
    
    user_profile = request.user.profile
    can_edit = False
    
    if user_profile.user_type == 'central_admin' and issue.org == user_profile.org:
        can_edit = True
    elif user_profile.user_type == 'maintainer' and issue.maintainer == request.user:
        can_edit = True
    
    if not can_edit:
        return HttpResponseForbidden('You do not have permission to edit this issue.')
    
    if request.method == 'POST':
        form = IssueUpdateForm(request.POST, instance=issue, user=request.user)
        if form.is_valid():
            # Track changes for history
            old_status = issue.status
            old_priority = issue.priority
            old_maintainer = issue.maintainer
            
            updated_issue = form.save()
            
            # Create status history if status changed
            if (old_status != updated_issue.status or 
                old_priority != updated_issue.priority or 
                old_maintainer != updated_issue.maintainer):
                
                IssueStatusHistory.objects.create(
                    issue=updated_issue,
                    changed_by=request.user,
                    old_status=old_status,
                    new_status=updated_issue.status,
                    old_priority=old_priority,
                    new_priority=updated_issue.priority,
                    old_maintainer=old_maintainer,
                    new_maintainer=updated_issue.maintainer,
                    comment=f"Updated by {request.user.profile.first_name} {request.user.profile.last_name}"
                )
            
            messages.success(request, 'Issue updated successfully.')
            return redirect('issue_management:issue_detail', slug=slug)
    else:
        form = IssueUpdateForm(instance=issue, user=request.user)
    
    return render(request, 'issue_management/update_issue.html', {
        'form': form,
        'issue': issue
    })

def voice_record(request):
    return render(request, 'issue_management/voice_record.html')

@login_required
def assign_issue(request, issue_slug):
    issue = get_object_or_404(Issue, slug=issue_slug)
    if not request.user.is_authenticated or not hasattr(request.user, 'profile') or request.user.profile.user_type != 'central_admin':
        return HttpResponseForbidden('You do not have permission to assign issues.')
    if request.method == 'POST':
        form = IssueAssignmentForm(request.POST, instance=issue)
        if form.is_valid():
            # Track assignment change
            old_maintainer = issue.maintainer
            new_maintainer = form.cleaned_data['maintainer']
            
            form.save()
            
            # Create status history for assignment change
            if old_maintainer != new_maintainer:
                IssueStatusHistory.objects.create(
                    issue=issue,
                    changed_by=request.user,
                    old_status=issue.status,
                    new_status=issue.status,
                    old_maintainer=old_maintainer,
                    new_maintainer=new_maintainer,
                    comment=f"Assigned to {new_maintainer.profile.first_name} {new_maintainer.profile.last_name}" if new_maintainer else "Unassigned"
                )
            
            messages.success(request, f'Issue assigned to {new_maintainer.profile.first_name} {new_maintainer.profile.last_name}' if new_maintainer else 'Issue unassigned')
            return redirect('issue_management:issue_detail', slug=issue_slug)
    else:
        form = IssueAssignmentForm(instance=issue)
    return render(request, 'issue_management/assign_issue.html', {'form': form, 'issue': issue})

# Category Management Views
@login_required
def category_list(request):
    """List all issue categories for the organization"""
    if not hasattr(request.user, 'profile') or request.user.profile.user_type not in ['central_admin']:
        return HttpResponseForbidden('You do not have permission to manage categories.')
    
    categories = IssueCategory.objects.filter(org=request.user.profile.org).order_by('name')
    return render(request, 'issue_management/category_list.html', {'categories': categories})

@login_required
def create_category(request):
    """Create a new issue category"""
    if not hasattr(request.user, 'profile') or request.user.profile.user_type not in ['central_admin']:
        return HttpResponseForbidden('You do not have permission to create categories.')
    
    if request.method == 'POST':
        form = IssueCategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.org = request.user.profile.org
            category.save()
            messages.success(request, f'Category "{category.name}" created successfully.')
            return redirect('issue_management:category_list')
    else:
        form = IssueCategoryForm()
    
    return render(request, 'issue_management/create_category.html', {'form': form})

@login_required
def update_category(request, slug):
    """Update an existing issue category"""
    if not hasattr(request.user, 'profile') or request.user.profile.user_type not in ['central_admin']:
        return HttpResponseForbidden('You do not have permission to edit categories.')
    
    category = get_object_or_404(IssueCategory, slug=slug, org=request.user.profile.org)
    
    if request.method == 'POST':
        form = IssueCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Category "{category.name}" updated successfully.')
            return redirect('issue_management:category_list')
    else:
        form = IssueCategoryForm(instance=category)
    
    return render(request, 'issue_management/update_category.html', {
        'form': form, 
        'category': category
    })

@login_required
def delete_category(request, slug):
    """Delete an issue category"""
    if not hasattr(request.user, 'profile') or request.user.profile.user_type not in ['central_admin']:
        return HttpResponseForbidden('You do not have permission to delete categories.')
    
    category = get_object_or_404(IssueCategory, slug=slug, org=request.user.profile.org)
    
    if request.method == 'POST':
        category_name = category.name
        category.delete()
        messages.success(request, f'Category "{category_name}" deleted successfully.')
        return redirect('issue_management:category_list')
    
    return render(request, 'issue_management/delete_category.html', {'category': category})
