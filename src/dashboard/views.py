from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseForbidden, JsonResponse
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.contrib import messages
from datetime import timedelta
from core.models import UserProfile, User, Organisation
from service_management.models import Spaces
from issue_management.models import Issue, IssueCategory
from finance.models import FinancialTransaction, TransactionCategory


def get_dashboard_stats(user, selected_space=None):
    """Get dashboard statistics based on user type and context"""
    stats = {}
    thirty_days_ago = timezone.now() - timedelta(days=30)
    user_type = user.profile.user_type
    
    # Initialize default queries
    resolved_issues_base = Issue.objects.none()
    
    # Base queries depending on user type and context
    if user_type == 'central_admin':
        # Central admin sees org-wide stats
        org = user.profile.org
        issues_base = Issue.objects.filter(org=org).exclude(status='resolved')  # Exclude resolved issues from main stats
        resolved_issues_base = Issue.objects.filter(org=org, status='resolved')  # Separate resolved issues
        users_base = User.objects.filter(profile__org=org)
        transactions_base = FinancialTransaction.objects.filter(org=org)
        categories_base = IssueCategory.objects.filter(org=org)
        spaces_base = Spaces.objects.filter(org=org)
        
    elif user_type == 'space_admin' and selected_space:
        # Space admin sees space-specific stats with same privileges as central admin within their space
        issues_base = Issue.objects.filter(space=selected_space).exclude(status='resolved')  # Exclude resolved issues from main stats
        resolved_issues_base = Issue.objects.filter(space=selected_space, status='resolved')  # Separate resolved issues
        users_base = User.objects.filter(profile__org=selected_space.org)
        transactions_base = FinancialTransaction.objects.filter(space=selected_space)
        categories_base = IssueCategory.objects.filter(org=selected_space.org)
        spaces_base = Spaces.objects.filter(id=selected_space.id)
        
    elif user_type == 'general_user':
        # General users only see their own issues
        issues_base = Issue.objects.filter(created_by=user).exclude(status='resolved')  # Exclude resolved issues from main stats
        resolved_issues_base = Issue.objects.filter(created_by=user, status='resolved')  # Separate resolved issues
        users_base = User.objects.filter(id=user.id)  # Only themselves
        transactions_base = FinancialTransaction.objects.filter(created_by=user)
        categories_base = IssueCategory.objects.filter(org=user.profile.org) if user.profile.org else IssueCategory.objects.none()
        spaces_base = Spaces.objects.none()  # General users don't see space stats
        
    elif user_type == 'maintainer':
        # Maintainers see issues assigned to them or that they have worked on before
        from django.db.models import Q
        
        # Get issues where the maintainer:
        # 1. Is currently assigned (maintainer=user)
        # 2. Has work sessions (worked on it before)
        # 3. Has status history (was assigned before) 
        # 4. Has commented on the issue (was involved)
        
        # Import work session model
        from issue_management.models import IssueWorkSession, IssueStatusHistory, IssueComment
        
        # Get issue IDs where maintainer has worked or been involved
        worked_issue_ids = IssueWorkSession.objects.filter(maintainer=user).values_list('issue_id', flat=True)
        status_history_issue_ids = IssueStatusHistory.objects.filter(
            Q(old_maintainer=user) | Q(new_maintainer=user)
        ).values_list('issue_id', flat=True)
        commented_issue_ids = IssueComment.objects.filter(author=user).values_list('issue_id', flat=True)
        
        # Combine all relevant issue IDs
        relevant_issue_ids = set(worked_issue_ids) | set(status_history_issue_ids) | set(commented_issue_ids)
        
        # Filter issues: currently assigned OR has worked on before
        maintainer_issues_query = Q(maintainer=user) | Q(id__in=relevant_issue_ids)
        
        if user.profile.org:
            # Filter by org as well for security
            issues_base = Issue.objects.filter(
                maintainer_issues_query & Q(org=user.profile.org)
            ).exclude(status__in=['resolved', 'escalated'])
            
            resolved_issues_base = Issue.objects.filter(
                maintainer_issues_query & Q(org=user.profile.org, status='resolved')
            )
            
            users_base = User.objects.filter(profile__org=user.profile.org)
            transactions_base = FinancialTransaction.objects.filter(org=user.profile.org)
            categories_base = IssueCategory.objects.filter(org=user.profile.org)
            spaces_base = Spaces.objects.filter(org=user.profile.org)
        else:
            # No org context, only see assigned issues or ones worked on
            issues_base = Issue.objects.filter(maintainer_issues_query).exclude(status__in=['resolved', 'escalated'])
            resolved_issues_base = Issue.objects.filter(maintainer_issues_query & Q(status='resolved'))
            users_base = User.objects.filter(id=user.id)
            transactions_base = FinancialTransaction.objects.none()
            categories_base = IssueCategory.objects.none()
            spaces_base = Spaces.objects.none()
        
    else:
        # Other user types get org-wide stats if they have an org
        if user.profile.org:
            issues_base = Issue.objects.filter(org=user.profile.org).exclude(status='resolved')  # Exclude resolved issues from main stats
            resolved_issues_base = Issue.objects.filter(org=user.profile.org, status='resolved')  # Separate resolved issues
            users_base = User.objects.filter(profile__org=user.profile.org)
            transactions_base = FinancialTransaction.objects.filter(org=user.profile.org)
            categories_base = IssueCategory.objects.filter(org=user.profile.org)
            spaces_base = Spaces.objects.filter(org=user.profile.org)
        else:
            # No org context, return empty stats
            return {
                'total_issues': 0,
                'total_users': 0,
                'total_transactions': 0,
                'total_categories': 0,
                'total_resolved_issues': 0,
                'issues_last_30_days': 0,
                'users_last_30_days': 0,
                'transactions_last_30_days': 0,
                'resolved_issues_last_30_days': 0,
                'open_issues': 0,
                'closed_issues': 0,
                'in_progress_issues': 0,
                'escalated_issues': 0,
                'resolved_issues': 0,
                'critical_issues': 0,
                'high_issues': 0,
                'medium_issues': 0,
                'low_issues': 0,
                'total_transaction_amount': 0,
                'recent_issues': [],
                'recent_resolved_issues': [],
                'issue_status_data': [],
                'monthly_issues_data': [],
            }
    
    # Calculate statistics
    stats['total_issues'] = issues_base.count()  # Active issues only (excluding resolved)
    stats['total_resolved_issues'] = resolved_issues_base.count()  # Resolved issues count
    stats['total_users'] = users_base.count()
    stats['total_transactions'] = transactions_base.count()
    stats['total_categories'] = categories_base.count()
    stats['total_spaces'] = spaces_base.count()
    
    # Last 30 days stats
    stats['issues_last_30_days'] = issues_base.filter(created_at__gte=thirty_days_ago).count()
    stats['resolved_issues_last_30_days'] = resolved_issues_base.filter(created_at__gte=thirty_days_ago).count()
    stats['users_last_30_days'] = users_base.filter(date_joined__gte=thirty_days_ago).count()
    stats['transactions_last_30_days'] = transactions_base.filter(created_at__gte=thirty_days_ago).count()
    
    # Issue status breakdown (for active issues only)
    stats['open_issues'] = issues_base.filter(status='open').count()
    stats['closed_issues'] = issues_base.filter(status='closed').count()
    stats['in_progress_issues'] = issues_base.filter(status='in_progress').count()
    stats['escalated_issues'] = issues_base.filter(status='escalated').count()
    stats['resolved_issues'] = resolved_issues_base.count()  # Count from separate resolved query
    
    # Priority breakdown (useful for maintainer dashboard)
    stats['critical_issues'] = issues_base.filter(priority='critical').count()
    stats['high_issues'] = issues_base.filter(priority='high').count()
    stats['medium_issues'] = issues_base.filter(priority='medium').count()
    stats['low_issues'] = issues_base.filter(priority='low').count()
    
    # Financial stats
    completed_transactions = transactions_base.filter(status='completed')
    stats['total_transaction_amount'] = completed_transactions.aggregate(
        total=Sum('amount'))['total'] or 0
    
    # Recent issues for table (active issues only)
    stats['recent_issues'] = issues_base.select_related('category', 'created_by__profile', 'space').order_by('-created_at')[:10]
    
    # Recent resolved issues for separate display
    stats['recent_resolved_issues'] = resolved_issues_base.select_related('category', 'created_by__profile', 'space').order_by('-updated_at')[:10]
    
    # User role statistics (for central admin)
    if user_type == 'central_admin':
        stats['space_admins'] = users_base.filter(profile__user_type='space_admin').count()
        stats['maintainers'] = users_base.filter(profile__user_type='maintainer').count()
        stats['general_users'] = users_base.filter(profile__user_type='general_user').count()
        stats['active_spaces'] = spaces_base.filter(is_active=True).count() if hasattr(spaces_base.model, 'is_active') else spaces_base.count()
    
    # Issue status data for charts
    stats['issue_status_data'] = [
        stats['open_issues'],
        stats['closed_issues'], 
        stats['in_progress_issues'],
        stats['escalated_issues']
    ]
    
    # Monthly issues data for the last 6 months (including both active and resolved)
    monthly_data = []
    monthly_resolved_data = []
    for i in range(6):
        month_start = timezone.now().replace(day=1) - timedelta(days=30*i)
        month_end = month_start + timedelta(days=30)
        month_issues = issues_base.filter(
            created_at__gte=month_start,
            created_at__lt=month_end
        ).count()
        month_resolved = resolved_issues_base.filter(
            created_at__gte=month_start,
            created_at__lt=month_end
        ).count()
        monthly_data.insert(0, month_issues)
        monthly_resolved_data.insert(0, month_resolved)
    
    stats['monthly_issues_data'] = monthly_data
    stats['monthly_resolved_data'] = monthly_resolved_data
    
    return stats

@login_required
def dashboard_view(request):
    # Simplified access check - just verify user has profile
    if not hasattr(request.user, 'profile'):
        return HttpResponseForbidden('Access denied - no profile found.')
    
    user = request.user
    user_type = getattr(user.profile, 'user_type', None)
    
    # Space context is now handled by middleware, so we can access it directly
    selected_space = getattr(request, 'selected_space', None)
    
    # Get dashboard statistics
    dashboard_stats = get_dashboard_stats(user, selected_space)
    
    template_map = {
        'central_admin': 'dashboard/dashboard_central_admin.html',
        'institution_admin': 'dashboard/dashboard_institution_admin.html',
        'departement_incharge': 'dashboard/dashboard_departement_incharge.html',
        'room_incharge': 'dashboard/dashboard_room_incharge.html',
        'space_admin': 'dashboard/dashboard_space_admin.html',
        'maintainer': 'dashboard/dashboard_maintainer.html',
        'general_user': 'dashboard/dashboard_general_user.html',
    }
    
    # Base context with real data - space context will be added by context processor
    base_context = {
        'user': user, 
        'user_type': user_type,
        'stats': dashboard_stats,
    }
    
    context_map = {
        'central_admin': {
            **base_context,
            'admin_message': 'Central admin specific context.',
        },
        'institution_admin': {
            **base_context,
            'institution_message': 'Institution admin context.',
        },
        'departement_incharge': {
            **base_context,
            'department_message': 'Department incharge context.',
        },
        'room_incharge': {
            **base_context,
            'room_message': 'Room incharge context.',
        },
        'space_admin': {
            **base_context,
            'space_admin_message': 'Space admin context.',
            # Space context will be automatically added by middleware and context processor
        },
        'maintainer': {
            **base_context,
            'maintainer_message': 'Maintainer context.',
        },
        'general_user': {
            **base_context,
            'general_message': 'General user context.',
        },
    }
    template = template_map.get(user_type, 'dashboard/dashboard.html')
    context = context_map.get(user_type, base_context)
    return render(request, template, context)


@login_required
def switch_space(request):
    """Handle space switching for space admins"""
    if request.method != 'POST':
        # If not POST, redirect to dashboard
        return redirect('dashboard:dashboard')
        
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'space_admin':
        # Return JSON for AJAX requests, redirect for form submissions
        if request.headers.get('Content-Type') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
        else:
            messages.error(request, 'Unauthorized to switch spaces')
            return redirect('dashboard:dashboard')
    
    space_slug = request.POST.get('space_slug')
    if not space_slug:
        if request.headers.get('Content-Type') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Space slug required'}, status=400)
        else:
            messages.error(request, 'Please select a space to switch to')
            return redirect('dashboard:dashboard')
    
    try:
        # Get the space and verify the user can administer it
        space = get_object_or_404(Spaces, slug=space_slug)
        
        if request.user.profile.can_administer_space(space):
            # Switch the active space in the user's profile
            success = request.user.profile.switch_active_space(space)
            if success:
                # Return JSON for AJAX requests, redirect for form submissions
                if request.headers.get('Content-Type') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True, 
                        'space_name': space.name,
                        'space_slug': space.slug
                    })
                else:
                    messages.success(request, f'Switched to {space.name} space')
                    return redirect('dashboard:dashboard')
            else:
                if request.headers.get('Content-Type') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Failed to switch space'}, status=400)
                else:
                    messages.error(request, 'Failed to switch space')
                    return redirect('dashboard:dashboard')
        else:
            if request.headers.get('Content-Type') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Cannot access this space'}, status=403)
            else:
                messages.error(request, 'You do not have access to this space')
                return redirect('dashboard:dashboard')
            
    except Spaces.DoesNotExist:
        if request.headers.get('Content-Type') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Space not found'}, status=404)
        else:
            messages.error(request, 'Space not found')
            return redirect('dashboard:dashboard')
    except Exception as e:
        if request.headers.get('Content-Type') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        else:
            messages.error(request, f'An error occurred: {str(e)}')
            return redirect('dashboard:dashboard')


@login_required
def dashboard_api_stats(request):
    """API endpoint to get dashboard statistics in JSON format"""
    if not hasattr(request.user, 'profile'):
        return JsonResponse({'error': 'Access denied - no profile found.'}, status=403)
    
    # Space context is now handled by middleware
    selected_space = getattr(request, 'selected_space', None)
    
    stats = get_dashboard_stats(request.user, selected_space)
    return JsonResponse(stats)
