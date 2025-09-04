from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden, JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from django.db import transaction
import logging

from .models import Issue, IssueImage, IssueCategory, IssueComment, IssueStatusHistory, IssueWorkSession, IssueBreakSession
from .forms import IssueForm, IssueAssignmentForm, IssueUpdateForm, IssueCommentForm, IssueCategoryForm, IssueEscalationForm, EscalatedIssueReassignmentForm
from config.helpers import is_central_admin

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
    assigned_filter = request.GET.get('assigned')  # New assigned filter
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
        # Maintainer sees issues assigned to them or that they have worked on before
        from issue_management.models import IssueWorkSession, IssueStatusHistory, IssueComment
        
        # Get issue IDs where maintainer has worked or been involved
        worked_issue_ids = IssueWorkSession.objects.filter(maintainer=request.user).values_list('issue_id', flat=True)
        status_history_issue_ids = IssueStatusHistory.objects.filter(
            Q(old_maintainer=request.user) | Q(new_maintainer=request.user)
        ).values_list('issue_id', flat=True)
        commented_issue_ids = IssueComment.objects.filter(author=request.user).values_list('issue_id', flat=True)
        
        # Combine all relevant issue IDs
        relevant_issue_ids = set(worked_issue_ids) | set(status_history_issue_ids) | set(commented_issue_ids)
        
        # Filter issues: currently assigned OR has worked on before
        maintainer_issues_query = Q(maintainer=request.user) | Q(id__in=relevant_issue_ids)
        
        # Apply org filter for security if user has org
        if request.user.profile.org:
            maintainer_issues_query = maintainer_issues_query & Q(org=request.user.profile.org)
        
        if view_type == 'resolved':
            issues = Issue.objects.filter(
                maintainer_issues_query & Q(status='resolved')
            ).order_by('-updated_at')
        else:
            # Active issues only (excluding escalated and resolved for normal view)
            issues = Issue.objects.filter(
                maintainer_issues_query
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
    if assigned_filter and view_type != 'resolved':  # Filter for assigned issues
        issues = issues.filter(maintainer__isnull=False)
    
    # Calculate statistics based on user type and permissions (should match the same filtering logic as issues)
    base_issues = Issue.objects.none()
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        if request.user.profile.user_type == 'central_admin':
            # Central admin sees org-wide statistics
            base_issues = Issue.objects.filter(org=request.user.profile.org)
            
            # Apply space filter if selected
            if selected_space:
                base_issues = base_issues.filter(space=selected_space)
            elif request.GET.get('space_filter') == 'no_space':
                base_issues = base_issues.filter(space__isnull=True)
                
        elif request.user.profile.user_type == 'space_admin':
            # Space admin sees statistics from their current active space
            if selected_space:
                base_issues = Issue.objects.filter(space=selected_space)
            else:
                # No spaces available - show empty stats
                base_issues = Issue.objects.none()
                
        elif request.user.profile.user_type == 'maintainer':
            # For maintainers, count issues they are assigned to or have worked on
            from issue_management.models import IssueWorkSession, IssueStatusHistory, IssueComment
            
            # Get issue IDs where maintainer has worked or been involved
            worked_issue_ids = IssueWorkSession.objects.filter(maintainer=request.user).values_list('issue_id', flat=True)
            status_history_issue_ids = IssueStatusHistory.objects.filter(
                Q(old_maintainer=request.user) | Q(new_maintainer=request.user)
            ).values_list('issue_id', flat=True)
            commented_issue_ids = IssueComment.objects.filter(author=request.user).values_list('issue_id', flat=True)
            
            # Combine all relevant issue IDs
            relevant_issue_ids = set(worked_issue_ids) | set(status_history_issue_ids) | set(commented_issue_ids)
            
            # Filter issues: currently assigned OR has worked on before
            maintainer_issues_query = Q(maintainer=request.user) | Q(id__in=relevant_issue_ids)
            
            # Apply org filter for security if user has org
            if request.user.profile.org:
                maintainer_issues_query = maintainer_issues_query & Q(org=request.user.profile.org)
            
            # For maintainers, exclude escalated issues from statistics as well since they can no longer work on them
            base_issues = Issue.objects.filter(maintainer_issues_query).exclude(status='escalated')
        else:
            # Regular users see statistics for issues they created
            base_issues = Issue.objects.filter(created_by=request.user, org=request.user.profile.org)
    
    # Separate counts for active and resolved issues
    active_issues = base_issues.exclude(status='resolved')
    resolved_issues = base_issues.filter(status='resolved')
    
    # Calculate specific status counts
    pending_count = active_issues.filter(status='open').count()
    in_progress_count = active_issues.filter(status='in_progress').count()
    escalated_count = active_issues.filter(status='escalated').count()
    resolved_count = resolved_issues.count()
    
    # Assigned count should reflect issues that have a maintainer assigned (excluding resolved)
    assigned_count = active_issues.filter(maintainer__isnull=False).count()
    
    # Total active issues count
    total_active_count = pending_count + in_progress_count + escalated_count
    
    # Initialize my_issues_count
    my_issues_count = 0
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        if request.user.profile.user_type == 'maintainer':
            # For maintainers, count only currently assigned issues
            my_issues_count = base_issues.filter(maintainer=request.user).count()
        elif request.user.profile.user_type in ['central_admin', 'space_admin']:
            # For admins, show total active issues in their scope (not personally created)
            my_issues_count = active_issues.count()
        else:
            # For regular users, show issues they created
            my_issues_count = base_issues.filter(created_by=request.user).count()
    
    # Get categories for filter dropdown
    categories = IssueCategory.objects.filter(
        org=request.user.profile.org, 
        is_active=True
    ).order_by('name') if request.user.is_authenticated and hasattr(request.user, 'profile') else []
    
    # Pagination
    paginator = Paginator(issues, 10)  # Show 10 issues per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'issues': page_obj,
        'page_obj': page_obj,
        'total_active_count': total_active_count,
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
            'assigned': assigned_filter,
            'view': view_type,
        }
        # Space context will be automatically added by middleware and context processor
    }
    
    return render(request, 'issue_management/issue_list.html', context)

def report_issue(request):
    logger = logging.getLogger(__name__)
    
    if request.method == 'POST':
        try:
            form = IssueForm(request.POST, request.FILES, user=request.user if request.user.is_authenticated else None)
            images = request.FILES.getlist('image')
            
            # Validate images separately since they're not part of the form model
            image_errors = []
            if len(images) > 3:
                image_errors.append('You can upload a maximum of 3 images.')
            
            # Validate image file types and sizes
            allowed_image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            max_image_size = 3 * 1024 * 1024  # Reduced to 3MB to prevent timeouts
            
            for img in images:
                if img.content_type not in allowed_image_types:
                    image_errors.append(f'Invalid image type: {img.name}. Allowed types: JPEG, PNG, GIF, WebP.')
                if img.size > max_image_size:
                    image_errors.append(f'Image {img.name} is too large. Maximum size is 3MB.')
            
            if image_errors:
                for error in image_errors:
                    form.add_error(None, error)
            
            if form.is_valid() and not image_errors:
                logger.info(f"Starting issue creation process for user: {request.user.id if request.user.is_authenticated else 'anonymous'}")
            
            # Check for potential duplicate submissions using multiple methods
            
            # Method 1: Session-based duplicate prevention
            session_key = f"last_issue_submission_{request.user.id if request.user.is_authenticated else request.session.session_key}"
            last_submission = request.session.get(session_key)
            
            if last_submission:
                from django.utils import timezone
                import json
                from datetime import timedelta
                
                try:
                    last_data = json.loads(last_submission)
                    last_time = timezone.datetime.fromisoformat(last_data['timestamp'])
                    last_title = last_data['title']
                    
                    # Prevent duplicate submission within 30 seconds with same title
                    if (timezone.now() - last_time < timedelta(seconds=30) and 
                        last_title == form.cleaned_data['title']):
                        logger.warning(f"Duplicate submission prevented for user {request.user.id}: {last_title}")
                        messages.warning(request, 
                            'You recently submitted an issue with the same title. '
                            'Please wait a moment before submitting again or use a different title.'
                        )
                        return render(request, 'issue_management/report_issue.html', {'form': form})
                except (json.JSONDecodeError, KeyError, ValueError):
                    logger.warning("Invalid session data found, continuing with submission")
                    pass  # Invalid session data, continue with submission
            
            # Method 2: Database duplicate check for authenticated users
            if request.user.is_authenticated:
                from django.utils import timezone
                from datetime import timedelta
                
                recent_cutoff = timezone.now() - timedelta(minutes=2)  # 2 minute window
                existing_issue = Issue.objects.filter(
                    created_by=request.user,
                    title=form.cleaned_data['title'],
                    created_at__gte=recent_cutoff
                ).first()
                
                if existing_issue:
                    logger.warning(f"Duplicate issue found, redirecting to existing issue: {existing_issue.id}")
                    messages.warning(request, 
                        f'An issue with the same title was recently created. '
                        f'<a href="/issues/{existing_issue.slug}/" class="alert-link">View the existing issue</a>.'
                    )
                    return redirect('issue_management:issue_detail', slug=existing_issue.slug)
            
            try:
                logger.info("Starting issue creation with optimized file handling")
                
                # Create the issue object first without files to avoid timeout
                issue = form.save(commit=False)
                
                # Clear the voice file temporarily to save the issue first
                voice_file = issue.voice
                issue.voice = None
                
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
                
                logger.info(f"Issue prepared for saving: {issue.title}")
                
                # Save the issue first without files to get an ID quickly
                issue.save()
                logger.info(f"Issue saved successfully: {issue.id}")
                
                # Now handle file uploads with timeout protection
                uploaded_images = 0
                image_upload_errors = []
                voice_uploaded = False
                
                # Handle voice file upload if present
                if voice_file:
                    try:
                        logger.info(f"Uploading voice file for issue {issue.id}")
                        issue.voice = voice_file
                        issue.save(update_fields=['voice'])
                        voice_uploaded = True
                        logger.info(f"Voice file uploaded successfully for issue {issue.id}")
                    except Exception as voice_error:
                        logger.error(f"Voice upload failed for issue {issue.id}: {str(voice_error)}")
                        # Don't fail the entire process for voice upload failure
                
                # Handle image uploads with individual error handling
                for i, img in enumerate(images[:3]):
                    try:
                        logger.info(f"Processing image {i+1}/{len(images[:3])}: {img.name}")
                        
                        # Validate image size before upload
                        if img.size > 5 * 1024 * 1024:  # 5MB limit
                            raise ValueError(f"Image too large: {img.size} bytes")
                        
                        issue_image = IssueImage.objects.create(issue=issue, image=img)
                        uploaded_images += 1
                        logger.info(f"Image {i+1} uploaded successfully for issue {issue.id}")
                        
                    except Exception as img_error:
                        logger.error(f"Failed to upload image {img.name} for issue {issue.id}: {str(img_error)}")
                        image_upload_errors.append(f"Failed to upload {img.name}: {str(img_error)}")
                        # Continue with other images even if one fails
                
                # Store submission info in session for duplicate prevention
                import json
                from django.utils import timezone
                submission_data = {
                    'timestamp': timezone.now().isoformat(),
                    'title': issue.title,
                    'issue_id': issue.id
                }
                request.session[session_key] = json.dumps(submission_data)
                
                # Create success message
                success_msg = f'Issue "{issue.title}" has been reported successfully.'
                if uploaded_images > 0:
                    success_msg += f' {uploaded_images} of {len(images)} image(s) uploaded.'
                if voice_uploaded:
                    success_msg += ' Voice note uploaded.'
                if image_upload_errors:
                    success_msg += f' Note: {len(image_upload_errors)} file(s) failed to upload.'
                
                logger.info(f"Issue creation completed: {issue.id}, images: {uploaded_images}, voice: {voice_uploaded}")
                messages.success(request, success_msg)
                
                # Add warnings for any upload failures
                for error in image_upload_errors:
                    messages.warning(request, error)
                    
                return redirect('issue_management:issue_detail', slug=issue.slug)
                
            except Exception as e:
                logger.error(f"Critical error creating issue: {str(e)}", exc_info=True)
                
                # Add more specific error details for debugging
                error_details = {
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'user_id': request.user.id if request.user.is_authenticated else None,
                    'form_data': {
                        'title': form.cleaned_data.get('title', '') if form.cleaned_data else '',
                        'has_voice': bool(request.FILES.get('voice')),
                        'image_count': len(images)
                    }
                }
                logger.error(f"Issue creation error details: {error_details}")
                
                messages.error(request, 
                    'An error occurred while creating the issue. Please try again. '
                    'If the problem persists, please contact support.'
                )
            else:
                # Log form validation errors
                logger.warning(f"Form validation failed: {form.errors}, Image errors: {image_errors}")
        
        except Exception as general_error:
            logger.error(f"Unexpected error in issue creation: {str(general_error)}", exc_info=True)
            messages.error(request, 
                'An unexpected error occurred. Please try again.'
            )
                
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
    
    # Get resolution images if issue is resolved
    resolution_images = []
    if issue.status == 'resolved':
        resolution_images = issue.resolution_images.all()
    
    # Check if user can delete the issue
    can_delete = False
    
    # Central admins can delete any issue in their organization
    if user_profile.user_type == 'central_admin' and issue.org == user_profile.org:
        can_delete = True
    # General users can delete their own issues within 15 minutes if certain conditions are met
    elif (user_profile.user_type == 'general_user' and 
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
        'resolution_images': resolution_images,
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
            old_status = issue.status
            new_maintainer = form.cleaned_data['maintainer']
            
            # Save the form, which will trigger the model's save method
            updated_issue = form.save()
            
            # Create status history for assignment change
            if old_maintainer != new_maintainer:
                # Check if status changed due to assignment
                status_change_comment = ""
                if old_status != updated_issue.status:
                    status_change_comment = f" (Status changed from {old_status} to {updated_issue.status})"
                
                IssueStatusHistory.objects.create(
                    issue=updated_issue,
                    changed_by=request.user,
                    old_status=old_status,
                    new_status=updated_issue.status,
                    old_maintainer=old_maintainer,
                    new_maintainer=new_maintainer,
                    comment=f"Assigned to {new_maintainer.profile.first_name} {new_maintainer.profile.last_name}{status_change_comment}" if new_maintainer else f"Unassigned{status_change_comment}"
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
    
    # Can only escalate issues that are assigned or in progress
    if not issue.can_be_escalated:
        messages.error(request, 'This issue cannot be escalated. It must be assigned or in progress.')
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
@user_passes_test(is_central_admin)
def category_list(request):
    """List all issue categories for the organization"""
    categories = IssueCategory.objects.filter(org=request.user.profile.org).order_by('name')
    return render(request, 'issue_management/category_list.html', {'categories': categories})

@login_required
@user_passes_test(is_central_admin)
def create_category(request):
    """Create a new issue category"""
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
@user_passes_test(is_central_admin)
def update_category(request, slug):
    """Update an existing issue category"""
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
@user_passes_test(is_central_admin)
def delete_category(request, slug):
    """Delete an issue category"""
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
    
    # Handle optional resolution images for resolved status
    resolution_images = []
    if new_status == 'resolved':
        uploaded_files = request.FILES.getlist('resolution_images')
        # Limit to 3 images maximum
        if len(uploaded_files) > 3:
            messages.error(request, 'You can upload a maximum of 3 resolution images.')
            return redirect('issue_management:issue_detail', slug=slug)
        resolution_images = uploaded_files[:3]
    
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
    
    # Handle resolution images if status is resolved
    if new_status == 'resolved' and resolution_images:
        from .models import IssueResolutionImage
        for image in resolution_images:
            IssueResolutionImage.objects.create(
                issue=issue,
                image=image,
                uploaded_by=request.user,
                description=f"Resolution image uploaded with status change"
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
    """Delete an issue - allowed for general users within 15 minutes of creation or central admins at any time"""
    issue = get_object_or_404(Issue, slug=slug)
    
    # Check permissions
    if not hasattr(request.user, 'profile'):
        return HttpResponseForbidden('Access denied.')
    
    user_profile = request.user.profile
    can_delete = False
    is_central_admin = False
    
    # Central admins can delete any issue in their organization
    if user_profile.user_type == 'central_admin' and issue.org == user_profile.org:
        can_delete = True
        is_central_admin = True
    # General users can delete their own issues within 15 minutes
    elif (user_profile.user_type == 'general_user' and 
          issue.created_by == request.user):
        
        # Check if issue was created within the last 15 minutes
        from datetime import timedelta
        time_limit = timedelta(minutes=15)
        time_since_creation = timezone.now() - issue.created_at
        
        if time_since_creation <= time_limit:
            # Additional checks for general users
            if issue.maintainer:
                messages.error(request, 'Cannot delete an issue that has been assigned to a maintainer.')
                return redirect('issue_management:issue_detail', slug=slug)
            
            if issue.status != 'open':
                messages.error(request, 'Cannot delete an issue that is no longer in open status.')
                return redirect('issue_management:issue_detail', slug=slug)
            
            can_delete = True
        else:
            messages.error(request, 'You can only delete issues within 15 minutes of creation.')
            return redirect('issue_management:issue_detail', slug=slug)
    else:
        return HttpResponseForbidden('You do not have permission to delete this issue.')
    
    if not can_delete:
        return HttpResponseForbidden('You do not have permission to delete this issue.')
    
    if request.method == 'POST':
        issue_title = issue.title
        
        # Create a status history record for deletion (for audit purposes)
        if not is_central_admin:
            # For general users, create history as usual
            IssueStatusHistory.objects.create(
                issue=issue,
                changed_by=request.user,
                old_status=issue.status,
                new_status='deleted',
                comment=f"Issue deleted by {request.user.profile.first_name} {request.user.profile.last_name} (general user within time limit)"
            )
        else:
            # For central admins, create history record noting admin deletion
            IssueStatusHistory.objects.create(
                issue=issue,
                changed_by=request.user,
                old_status=issue.status,
                new_status='deleted',
                comment=f"Issue deleted by central admin {request.user.profile.first_name} {request.user.profile.last_name}"
            )
        
        issue.delete()
        messages.success(request, f'Issue "{issue_title}" has been deleted successfully.')
        return redirect('issue_management:issue_list')
    
    # Calculate remaining time for deletion (only for general users)
    remaining_time = None
    remaining_minutes = None
    remaining_seconds = None
    
    if not is_central_admin:
        from datetime import timedelta
        time_limit = timedelta(minutes=15)
        time_since_creation = timezone.now() - issue.created_at
        remaining_time = time_limit - time_since_creation
        remaining_minutes = int(remaining_time.total_seconds() // 60)
        remaining_seconds = int(remaining_time.total_seconds() % 60)
    
    context = {
        'issue': issue,
        'is_central_admin': is_central_admin,
        'remaining_minutes': remaining_minutes,
        'remaining_seconds': remaining_seconds,
    }
    
    return render(request, 'issue_management/delete_issue.html', context)
