from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string

from .models import Issue, IssueImage, IssueCategory, IssueComment, IssueStatusHistory, IssueWorkSession, IssueBreakSession
from .forms import IssueForm, IssueAssignmentForm, IssueUpdateForm, IssueCommentForm, IssueCategoryForm, IssueEscalationForm, EscalatedIssueReassignmentForm

def issue_list(request):
    # Initialize default values
    issues = Issue.objects.none()
    assigned_count = 0
    my_issues_count = 0
    
    # Filter parameters
    status_filter = request.GET.get('status')
    priority_filter = request.GET.get('priority')
    category_filter = request.GET.get('category')
    search = request.GET.get('search')
    view_type = request.GET.get('view', 'active')  # 'active' or 'resolved'
    
    # Space context is now handled by middleware, so we can access it directly
    selected_space = getattr(request, 'selected_space', None)
    
    if not request.user.is_authenticated or not hasattr(request.user, 'profile'):
        # Anonymous users see no issues
        issues = Issue.objects.none()
    elif request.user.profile.user_type == 'central_admin':
        # Central admin sees all issues from their organization
        if view_type == 'resolved':
            issues = Issue.objects.filter(org=request.user.profile.org, status='resolved').order_by('-updated_at')
        else:
            issues = Issue.objects.filter(org=request.user.profile.org).exclude(status='resolved').order_by('-created_at')
        
        # Handle space filter for central admin (selected_space is set by middleware based on space_filter parameter)
        if selected_space:
            issues = issues.filter(space=selected_space)
        elif request.GET.get('space_filter') == 'no_space':
            # Filter for issues without space assignment
            issues = issues.filter(space__isnull=True)
        
    elif request.user.profile.user_type == 'space_admin':
        # Space admin sees issues from their current active space (set by middleware)
        if selected_space:
            # Filter issues by the selected space
            if view_type == 'resolved':
                issues = Issue.objects.filter(space=selected_space, status='resolved').order_by('-updated_at')
            else:
                issues = Issue.objects.filter(space=selected_space).exclude(status='resolved').order_by('-created_at')
        else:
            # No spaces available
            issues = Issue.objects.none()
            
    elif request.user.profile.user_type == 'maintainer':
        # Maintainer sees assigned issues - can view resolved ones separately
        if view_type == 'resolved':
            issues = Issue.objects.filter(
                maintainer=request.user,
                status='resolved'
            ).order_by('-updated_at')
        else:
            # Active issues only (excluding escalated and resolved for normal view)
            issues = Issue.objects.filter(
                maintainer=request.user
            ).exclude(status__in=['escalated', 'resolved']).order_by('-created_at')
        
    else:
        # Regular users see issues they created from their organization
        if view_type == 'resolved':
            issues = Issue.objects.filter(
                created_by=request.user,
                org=request.user.profile.org,
                status='resolved'
            ).order_by('-updated_at')
        else:
            issues = Issue.objects.filter(
                created_by=request.user,
                org=request.user.profile.org
            ).exclude(status='resolved').order_by('-created_at')
    
    # Apply additional filters
    if status_filter and view_type != 'resolved':  # Don't filter by status for resolved view
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
            # For maintainers, count all their assigned issues for stats
            base_issues = Issue.objects.filter(maintainer=request.user)
        elif request.user.profile.user_type not in ['central_admin']:
            base_issues = Issue.objects.filter(created_by=request.user, org=request.user.profile.org)
    
    # Separate counts for active and resolved issues
    active_issues = base_issues.exclude(status='resolved')
    resolved_issues = base_issues.filter(status='resolved')
    
    assigned_count = active_issues.filter(maintainer__isnull=False).count()
    pending_count = active_issues.filter(status='open').count()
    in_progress_count = active_issues.filter(status='in_progress').count()
    resolved_count = resolved_issues.count()
    escalated_count = active_issues.filter(status='escalated').count()
    
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
        'escalated_count': escalated_count,
        'my_issues_count': my_issues_count,
        'categories': categories,
        'view_type': view_type,  # Add view type to context
        'current_filters': {
            'status': status_filter,
            'priority': priority_filter,
            'category': category_filter,
            'search': search,
            'view': view_type,
        }
        # Space context will be automatically added by middleware and context processor
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
                    if request.user.profile.current_active_space:
                        issue.space = request.user.profile.current_active_space
                elif request.user.profile.user_type == 'central_admin':
                    if form.cleaned_data.get('space'):
                        issue.space = form.cleaned_data['space']
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
            can_view = can_edit = can_comment = True  # Space admins now have same privileges as central admin within their space
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
    if user_profile.user_type not in ['maintainer', 'central_admin', 'space_admin']:
        comments = comments.filter(is_internal=False)
    
    # Get status history
    status_history = issue.status_history.all()[:10]  # Last 10 changes
    
    # Get escalation history
    escalation_history = issue.escalation_history
    
    # Check if user can delete the issue (general users within 15 minutes)
    can_delete = False
    if (user_profile.user_type == 'general_user' and 
        issue.created_by == request.user and 
        issue.status == 'open' and 
        not issue.maintainer):
        from datetime import timedelta
        time_limit = timedelta(minutes=15)
        time_since_creation = timezone.now() - issue.created_at
        can_delete = time_since_creation <= time_limit
    
    context = {
        'issue': issue,
        'can_edit': can_edit,
        'can_comment': can_comment,
        'can_delete': can_delete,
        'comment_form': comment_form,
        'comments': comments,
        'status_history': status_history,
        'escalation_history': escalation_history,
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
    elif user_profile.user_type == 'space_admin':
        # Space admins can edit issues within their managed spaces (same as central admin within space)
        if issue.space and issue.space in request.user.administered_spaces.all():
            can_edit = True
    elif user_profile.user_type == 'maintainer' and issue.maintainer == request.user:
        # Maintainers can only edit if issue is not escalated
        can_edit = issue.status != 'escalated'
    
    if not can_edit:
        if issue.status == 'escalated' and user_profile.user_type == 'maintainer':
            return HttpResponseForbidden('This issue has been escalated and can only be managed by central admin or space admin.')
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
    
    # Check permissions - central admins and space admins can assign issues
    if not request.user.is_authenticated or not hasattr(request.user, 'profile'):
        return HttpResponseForbidden('You do not have permission to assign issues.')
    
    user_profile = request.user.profile
    can_assign = False
    
    if user_profile.user_type == 'central_admin' and issue.org == user_profile.org:
        can_assign = True
    elif user_profile.user_type == 'space_admin':
        if issue.space and issue.space in request.user.administered_spaces.all():
            can_assign = True
    
    if not can_assign:
        return HttpResponseForbidden('You do not have permission to assign this issue.')
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

@login_required
def escalate_issue(request, slug):
    """Escalate an issue to central admin"""
    issue = get_object_or_404(Issue, slug=slug)
    
    # Check permissions - only assigned maintainers can escalate
    if not hasattr(request.user, 'profile'):
        return HttpResponseForbidden('Access denied.')
    
    user_profile = request.user.profile
    
    # Only maintainers assigned to the issue can escalate it
    if user_profile.user_type != 'maintainer' or issue.maintainer != request.user:
        return HttpResponseForbidden('You do not have permission to escalate this issue.')
    
    # Can only escalate issues that are in progress
    if not issue.can_be_escalated:
        messages.error(request, 'This issue cannot be escalated. It must be in progress.')
        return redirect('issue_management:issue_detail', slug=slug)
    
    if request.method == 'POST':
        form = IssueEscalationForm(request.POST, instance=issue)
        if form.is_valid():
            # Track changes for history
            old_status = issue.status
            
            # Update issue status and escalation details
            issue = form.save(commit=False)
            issue.status = 'escalated'
            issue.escalated_by = request.user
            issue.escalation_count += 1  # Increment escalation count
            issue.save()
            
            # Clear maintainer assignment since it's now escalated
            old_maintainer = issue.maintainer
            issue.maintainer = None
            issue.save()
            
            # Create status history
            IssueStatusHistory.objects.create(
                issue=issue,
                changed_by=request.user,
                old_status=old_status,
                new_status='escalated',
                old_maintainer=request.user,
                new_maintainer=None,
                comment=f"Escalated by {request.user.profile.first_name} {request.user.profile.last_name} (Escalation #{issue.escalation_count}). Reason: {issue.escalation_reason}"
            )
            
            messages.success(request, 'Issue has been escalated successfully. Central admin will now manage this issue.')
            return redirect('issue_management:issue_detail', slug=slug)
    else:
        form = IssueEscalationForm(instance=issue)
    
    return render(request, 'issue_management/escalate_issue.html', {
        'form': form, 
        'issue': issue
    })

@login_required
def reassign_escalated_issue(request, slug):
    """Reassign an escalated issue to a maintainer (Central Admin and Space Admin)"""
    issue = get_object_or_404(Issue, slug=slug)
    
    # Check permissions - central admins and space admins can reassign escalated issues
    if not hasattr(request.user, 'profile'):
        return HttpResponseForbidden('Access denied.')
    
    user_profile = request.user.profile
    
    # Central admins can reassign escalated issues in their org
    if user_profile.user_type == 'central_admin' and issue.org != user_profile.org:
        return HttpResponseForbidden('You do not have permission to reassign this issue.')
    # Space admins can reassign escalated issues in their managed spaces
    elif user_profile.user_type == 'space_admin':
        if not (issue.space and issue.space in request.user.administered_spaces.all()):
            return HttpResponseForbidden('You do not have permission to reassign this issue.')
    # Other user types cannot reassign escalated issues
    elif user_profile.user_type not in ['central_admin', 'space_admin']:
        return HttpResponseForbidden('You do not have permission to reassign this issue.')
    
    # Can only reassign escalated issues
    if not issue.is_escalated:
        messages.error(request, 'This issue has not been escalated and cannot be reassigned through this process.')
        return redirect('issue_management:issue_detail', slug=slug)
    
    if request.method == 'POST':
        form = EscalatedIssueReassignmentForm(request.POST, instance=issue, org=issue.org)
        if form.is_valid():
            # Track changes for history
            old_maintainer = issue.maintainer
            new_maintainer = form.cleaned_data['maintainer']
            reassignment_message = form.cleaned_data['reassignment_message']
            
            # Reset issue from escalated status to normal workflow
            issue.maintainer = new_maintainer
            issue.status = 'open'  # Reset to open so maintainer can manage normally
            
            # Clear current escalation fields but preserve escalation_count for history
            issue.escalated_by = None
            issue.escalated_at = None
            issue.escalation_reason = ''
            # Note: We keep escalation_count to track total escalations
            
            issue.save()
            
            # Create status history
            IssueStatusHistory.objects.create(
                issue=issue,
                changed_by=request.user,
                old_status='escalated',
                new_status='open',  # Reset to open status
                old_maintainer=old_maintainer,
                new_maintainer=new_maintainer,
                comment=f"Escalated issue reassigned by {request.user.profile.first_name} {request.user.profile.last_name} to {new_maintainer.profile.first_name} {new_maintainer.profile.last_name}. Issue reset to normal workflow (Total escalations: {issue.escalation_count}). Message: {reassignment_message}"
            )
            
            messages.success(request, f'Escalated issue has been reassigned to {new_maintainer.profile.first_name} {new_maintainer.profile.last_name} and reset to normal workflow.')
            return redirect('issue_management:issue_detail', slug=slug)
    else:
        form = EscalatedIssueReassignmentForm(instance=issue, org=issue.org)
    
    return render(request, 'issue_management/reassign_escalated_issue.html', {
        'form': form, 
        'issue': issue
    })

# Category Management Views
@login_required
def category_list(request):
    """List all issue categories for the organization"""
    if not hasattr(request.user, 'profile') or request.user.profile.user_type not in ['central_admin', 'space_admin']:
        return HttpResponseForbidden('You do not have permission to manage categories.')
    
    categories = IssueCategory.objects.filter(org=request.user.profile.org).order_by('name')
    return render(request, 'issue_management/category_list.html', {'categories': categories})

@login_required
def create_category(request):
    """Create a new issue category"""
    if not hasattr(request.user, 'profile') or request.user.profile.user_type not in ['central_admin', 'space_admin']:
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
    if not hasattr(request.user, 'profile') or request.user.profile.user_type not in ['central_admin', 'space_admin']:
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
    if not hasattr(request.user, 'profile') or request.user.profile.user_type not in ['central_admin', 'space_admin']:
        return HttpResponseForbidden('You do not have permission to delete categories.')
    
    category = get_object_or_404(IssueCategory, slug=slug, org=request.user.profile.org)
    
    if request.method == 'POST':
        category_name = category.name
        category.delete()
        messages.success(request, f'Category "{category_name}" deleted successfully.')
        return redirect('issue_management:category_list')
    
    return render(request, 'issue_management/delete_category.html', {'category': category})

@login_required
def change_status(request, slug, new_status):
    """Change issue status - for maintainers only (central admins use update form)"""
    issue = get_object_or_404(Issue, slug=slug)
    
    # Check permissions - only assigned maintainer can use quick status change
    if not hasattr(request.user, 'profile'):
        return HttpResponseForbidden('Invalid user profile.')
    
    # Only maintainer assigned to the issue (and not escalated) can use quick actions
    if not (request.user.profile.user_type == 'maintainer' and 
            issue.maintainer == request.user and 
            not issue.is_escalated):
        return HttpResponseForbidden('You do not have permission to change this issue status.')
    
    # Validate the new status
    valid_statuses = [choice[0] for choice in Issue.STATUS_CHOICES]
    if new_status not in valid_statuses:
        messages.error(request, 'Invalid status.')
        return redirect('issue_management:issue_detail', slug=slug)
    
    # Prevent changing to escalated status (use escalate_issue view for that)
    if new_status == 'escalated':
        messages.error(request, 'Use the escalate button to escalate issues.')
        return redirect('issue_management:issue_detail', slug=slug)
    
    # Prevent maintainers from reopening resolved issues
    if issue.status == 'resolved' and new_status in ['open', 'in_progress']:
        messages.error(request, 'Maintainers cannot reopen resolved issues. Contact central admin if needed.')
        return redirect('issue_management:issue_detail', slug=slug)
    
    # Enforce single issue workflow - maintainer can only work on one issue at a time
    if new_status == 'in_progress':
        # Check if maintainer already has another issue in progress
        current_in_progress = Issue.objects.filter(
            maintainer=request.user,
            status='in_progress'
        ).exclude(id=issue.id)
        
        if current_in_progress.exists():
            in_progress_issue = current_in_progress.first()
            messages.error(request, 
                f'You already have an issue in progress: "{in_progress_issue.title}". '
                f'Please set it to "Open" or complete it before starting work on this issue.'
            )
            return redirect('issue_management:issue_detail', slug=slug)
    
    # Record the old status for history
    old_status = issue.status
    old_maintainer = issue.maintainer  # Track maintainer change
    
    # Update the issue status
    issue.status = new_status
    
    # Clear maintainer assignment when issue is resolved
    if new_status == 'resolved':
        issue.maintainer = None
    
    issue.save()
    
    # Create status history record
    history_comment = f"Status changed from {dict(Issue.STATUS_CHOICES)[old_status]} to {dict(Issue.STATUS_CHOICES)[new_status]} by maintainer"
    if new_status == 'resolved':
        history_comment += f"\n\nMaintainer assignment cleared (issue resolved)."
    
    IssueStatusHistory.objects.create(
        issue=issue,
        changed_by=request.user,
        old_status=old_status,
        new_status=new_status,
        old_maintainer=old_maintainer,
        new_maintainer=issue.maintainer,  # Will be None if resolved
        comment=history_comment
    )
    
    # Success message
    status_display = dict(Issue.STATUS_CHOICES)[new_status]
    messages.success(request, f'Issue status changed to "{status_display}".')
    
    # Redirect to focus mode if starting work on an issue
    if new_status == 'in_progress':
        return redirect('issue_management:focus_mode', slug=slug)
    
    return redirect('issue_management:issue_detail', slug=slug)

@login_required
def change_status_with_comment(request, slug, new_status):
    """Change issue status with optional comment - for maintainers to track activity"""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('issue_management:issue_detail', slug=slug)
    
    issue = get_object_or_404(Issue, slug=slug)
    
    # Check permissions - only assigned maintainer can change status (and not escalated)
    if not hasattr(request.user, 'profile'):
        return HttpResponseForbidden('Invalid user profile.')
    
    if not (request.user.profile.user_type == 'maintainer' and 
            issue.maintainer == request.user and 
            not issue.is_escalated):
        return HttpResponseForbidden('You do not have permission to change this issue status.')
    
    # Validate the new status
    valid_statuses = [choice[0] for choice in Issue.STATUS_CHOICES]
    if new_status not in valid_statuses:
        messages.error(request, 'Invalid status.')
        return redirect('issue_management:issue_detail', slug=slug)
    
    # Prevent changing to escalated status (use escalate_issue view for that)
    if new_status == 'escalated':
        messages.error(request, 'Use the escalate button to escalate issues.')
        return redirect('issue_management:issue_detail', slug=slug)
    
    # Prevent maintainers from reopening resolved issues
    if issue.status == 'resolved' and new_status in ['open', 'in_progress']:
        messages.error(request, 'Maintainers cannot reopen resolved issues. Contact central admin if needed.')
        return redirect('issue_management:issue_detail', slug=slug)
    
    # Enforce single issue workflow - maintainer can only work on one issue at a time
    if new_status == 'in_progress':
        # Check if maintainer already has another issue in progress
        current_in_progress = Issue.objects.filter(
            maintainer=request.user,
            status='in_progress'
        ).exclude(id=issue.id)
        
        if current_in_progress.exists():
            in_progress_issue = current_in_progress.first()
            messages.error(request, 
                f'You already have an issue in progress: "{in_progress_issue.title}". '
                f'Please set it to "Open" or complete it before starting work on this issue.'
            )
            return redirect('issue_management:issue_detail', slug=slug)
    
    # Get the comment from the form
    comment = request.POST.get('comment', '').strip()
    
    # Record the old status for history
    old_status = issue.status
    old_maintainer = issue.maintainer  # Track maintainer change
    
    # Update the issue status
    issue.status = new_status
    
    # If setting to resolved and comment provided, save it as resolution notes
    if new_status == 'resolved' and comment:
        issue.resolution_notes = comment
    
    # Clear maintainer assignment when issue is resolved
    if new_status == 'resolved':
        issue.maintainer = None
    
    issue.save()
    
    # Create status history record with comment
    history_comment = f"Status changed from {dict(Issue.STATUS_CHOICES)[old_status]} to {dict(Issue.STATUS_CHOICES)[new_status]} by maintainer"
    if comment:
        history_comment += f"\n\nMaintainer notes: {comment}"
    
    # Add note about maintainer being cleared if resolved
    if new_status == 'resolved':
        history_comment += f"\n\nMaintainer assignment cleared (issue resolved)."
    
    IssueStatusHistory.objects.create(
        issue=issue,
        changed_by=request.user,
        old_status=old_status,
        new_status=new_status,
        old_maintainer=old_maintainer,
        new_maintainer=issue.maintainer,  # Will be None if resolved
        comment=history_comment
    )
    
    # Also create a comment if the maintainer added one
    if comment:
        comment_content = f"Status changed to '{dict(Issue.STATUS_CHOICES)[new_status]}'"
        if new_status == 'resolved':
            comment_content += f" with resolution notes:\n\n{comment}"
        else:
            comment_content += f"\n\n{comment}"
            
        IssueComment.objects.create(
            issue=issue,
            author=request.user,
            content=comment_content,
            is_internal=False
        )
    
    # Success message
    status_display = dict(Issue.STATUS_CHOICES)[new_status]
    messages.success(request, f'Issue status changed to "{status_display}".')
    
    # Redirect to focus mode if starting work on an issue
    if new_status == 'in_progress':
        return redirect('issue_management:focus_mode', slug=slug)
    
    return redirect('issue_management:issue_detail', slug=slug)

@login_required
def focus_mode(request, slug):
    """Focus mode for maintainers working on an issue"""
    issue = get_object_or_404(Issue, slug=slug)
    
    # Check permissions - only assigned maintainer can enter focus mode
    if not hasattr(request.user, 'profile'):
        return HttpResponseForbidden('Invalid user profile.')
    
    if not (request.user.profile.user_type == 'maintainer' and 
            issue.maintainer == request.user and 
            issue.status == 'in_progress'):
        messages.error(request, 'Focus mode is only available for issues you are actively working on.')
        return redirect('issue_management:issue_detail', slug=slug)
    
    # Get or create current work session
    current_session = issue.current_work_session
    if not current_session:
        current_session = IssueWorkSession.objects.create(
            issue=issue,
            maintainer=request.user,
            is_focus_mode=True
        )
        messages.info(request, 'Started new focus work session.')
    
    # Get recent comments for the issue
    recent_comments = issue.comments.all().order_by('-created_at')[:5]
    
    # Set focus mode start time in session
    session_key = f'focus_start_time_{issue.id}'
    if session_key not in request.session:
        request.session[session_key] = current_session.started_at.isoformat()
    
    context = {
        'issue': issue,
        'recent_comments': recent_comments,
        'focus_start_time': current_session.started_at,
        'current_session': current_session,
    }
    
    return render(request, 'issue_management/focus_mode.html', context)


@login_required
@require_http_methods(["POST"])
def add_progress_note(request, slug):
    """Add progress note via HTMX without leaving focus mode"""
    issue = get_object_or_404(Issue, slug=slug)
    
    # Check permissions - only assigned maintainer can add progress notes in focus mode
    if not hasattr(request.user, 'profile'):
        return HttpResponseForbidden('Invalid user profile.')
    
    if not (request.user.profile.user_type == 'maintainer' and 
            issue.maintainer == request.user and 
            issue.status == 'in_progress'):
        return HttpResponseForbidden('You can only add progress notes to issues you are actively working on.')
    
    content = request.POST.get('content', '').strip()
    is_internal = request.POST.get('is_internal') == 'on'
    
    if content:
        # Create the comment
        comment = IssueComment.objects.create(
            issue=issue,
            author=request.user,
            content=content,
            is_internal=is_internal
        )
        
        # Get updated recent comments
        recent_comments = issue.comments.all().order_by('-created_at')[:5]
        
        # Return updated comments list
        context = {
            'recent_comments': recent_comments,
        }
        
        return render(request, 'issue_management/partials/recent_comments.html', context)
    
    # If no content, return error
    return HttpResponse('<div class="alert alert-danger">Please enter a progress note.</div>', status=400)


@login_required
@require_http_methods(["POST"])
def start_break(request, slug):
    """Start a break session via HTMX"""
    issue = get_object_or_404(Issue, slug=slug)
    
    # Check permissions
    if not (hasattr(request.user, 'profile') and 
            request.user.profile.user_type == 'maintainer' and 
            issue.maintainer == request.user and 
            issue.status == 'in_progress'):
        return HttpResponseForbidden('You can only start breaks for issues you are actively working on.')
    
    # Get current work session
    current_session = issue.current_work_session
    if not current_session:
        return HttpResponse('<div class="alert alert-danger">No active work session found.</div>', status=400)
    
    # Check if there's already an active break
    active_break = current_session.breaks.filter(ended_at__isnull=True).first()
    if active_break:
        return HttpResponse('<div class="alert alert-warning">Break already in progress.</div>', status=400)
    
    # Create new break session
    break_type = request.POST.get('break_type', 'manual')
    break_session = IssueBreakSession.objects.create(
        work_session=current_session,
        break_type=break_type
    )
    
    return JsonResponse({
        'success': True,
        'break_id': break_session.id,
        'started_at': break_session.started_at.isoformat()
    })


@login_required
@require_http_methods(["POST"])
def end_break(request, slug):
    """End a break session via HTMX"""
    issue = get_object_or_404(Issue, slug=slug)
    
    # Check permissions
    if not (hasattr(request.user, 'profile') and 
            request.user.profile.user_type == 'maintainer' and 
            issue.maintainer == request.user and 
            issue.status == 'in_progress'):
        return HttpResponseForbidden('You can only end breaks for issues you are actively working on.')
    
    # Get current work session
    current_session = issue.current_work_session
    if not current_session:
        return HttpResponse('<div class="alert alert-danger">No active work session found.</div>', status=400)
    
    # Get active break
    active_break = current_session.breaks.filter(ended_at__isnull=True).first()
    if not active_break:
        return HttpResponse('<div class="alert alert-warning">No active break found.</div>', status=400)
    
    # End the break
    active_break.ended_at = timezone.now()
    active_break.save()
    
    # Update work session's total break time
    total_break_time = sum([
        break_session.duration for break_session in current_session.breaks.filter(duration__isnull=False)
    ], timezone.timedelta())
    current_session.total_break_time = total_break_time
    current_session.save()
    
    return JsonResponse({
        'success': True,
        'break_duration': str(active_break.duration),
        'total_break_time': str(current_session.total_break_time)
    })


@login_required
@require_http_methods(["POST"])
def end_work_session(request, slug):
    """End current work session when leaving focus mode"""
    issue = get_object_or_404(Issue, slug=slug)
    
    # Check permissions
    if not (hasattr(request.user, 'profile') and 
            request.user.profile.user_type == 'maintainer' and 
            issue.maintainer == request.user):
        return HttpResponseForbidden('You can only end work sessions for issues assigned to you.')
    
    # Get current work session
    current_session = issue.current_work_session
    if not current_session:
        return JsonResponse({'success': False, 'error': 'No active work session found.'})
    
    # End any active breaks
    active_break = current_session.breaks.filter(ended_at__isnull=True).first()
    if active_break:
        active_break.ended_at = timezone.now()
        active_break.save()
    
    # End the work session
    current_session.ended_at = timezone.now()
    
    # Calculate total work time (session duration minus break time)
    session_duration = current_session.session_duration
    current_session.total_work_time = session_duration - current_session.total_break_time
    current_session.save()
    
    return JsonResponse({
        'success': True,
        'session_duration': str(session_duration),
        'work_time': str(current_session.total_work_time),
        'break_time': str(current_session.total_break_time)
    })

@login_required
def delete_issue(request, slug):
    """Delete an issue - only allowed for general users within 15 minutes of creation"""
    issue = get_object_or_404(Issue, slug=slug)
    
    # Check permissions
    if not hasattr(request.user, 'profile'):
        return HttpResponseForbidden('Access denied.')
    
    user_profile = request.user.profile
    
    # Only the issue creator can delete their own issue
    if issue.created_by != request.user:
        return HttpResponseForbidden('You can only delete issues you created.')
    
    # Only general users can delete issues (other user types have different workflows)
    if user_profile.user_type != 'general_user':
        return HttpResponseForbidden('Only general users can delete their own issues.')
    
    # Check if issue was created within the last 15 minutes
    from datetime import timedelta
    time_limit = timedelta(minutes=15)
    time_since_creation = timezone.now() - issue.created_at
    
    if time_since_creation > time_limit:
        messages.error(request, 'You can only delete issues within 15 minutes of creation.')
        return redirect('issue_management:issue_detail', slug=slug)
    
    # Check if issue has been assigned to a maintainer
    if issue.maintainer:
        messages.error(request, 'Cannot delete an issue that has been assigned to a maintainer.')
        return redirect('issue_management:issue_detail', slug=slug)
    
    # Check if issue status has changed from 'open'
    if issue.status != 'open':
        messages.error(request, 'Cannot delete an issue that is no longer in open status.')
        return redirect('issue_management:issue_detail', slug=slug)
    
    if request.method == 'POST':
        issue_title = issue.title
        issue.delete()
        messages.success(request, f'Issue "{issue_title}" has been deleted successfully.')
        return redirect('issue_management:issue_list')
    
    # Calculate remaining time for deletion
    remaining_time = time_limit - time_since_creation
    remaining_minutes = int(remaining_time.total_seconds() // 60)
    remaining_seconds = int(remaining_time.total_seconds() % 60)
    
    context = {
        'issue': issue,
        'remaining_minutes': remaining_minutes,
        'remaining_seconds': remaining_seconds,
    }
    
    return render(request, 'issue_management/delete_issue.html', context)
