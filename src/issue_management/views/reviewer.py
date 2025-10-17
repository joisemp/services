from django.views.generic import ListView, DetailView
from django.db.models import Case, When, IntegerField
from ..models import Issue
from config.mixins.access_mixin import ReviewerOnlyAccessMixin


class ReviewerIssueListView(ReviewerOnlyAccessMixin, ListView):
    """
    View to list all issues where the reviewer is assigned as a reviewer.
    Only shows issues that have the current user in the reviewers field.
    """
    model = Issue
    template_name = "reviewer/issue_management/issue_list.html"
    context_object_name = "issues"

    def get_queryset(self):
        """
        Filter issues where the current user is in the reviewers many-to-many field.
        Order by status (open/assigned/in_progress first), then priority (critical first, low last), 
        then creation date.
        """
        queryset = Issue.objects.filter(
            reviewers=self.request.user
        ).select_related(
            'org', 
            'space', 
            'reporter',
            'assigned_to'
        ).prefetch_related(
            'images',
            'reviewers'
        )
        
        # Filter by status if provided in query params
        status_filter = self.request.GET.get('status', None)
        if status_filter and status_filter != 'all':
            if status_filter == 'critical':
                # Filter by priority instead
                queryset = queryset.filter(priority='critical')
            else:
                queryset = queryset.filter(status=status_filter)
        
        # Order by status, then priority, then creation date
        return queryset.annotate(
            status_order=Case(
                When(status='open', then=1),
                When(status='assigned', then=2),
                When(status='in_progress', then=3),
                When(status='resolved', then=4),
                When(status='escalated', then=5),
                When(status='closed', then=6),
                When(status='cancelled', then=7),
                default=8,
                output_field=IntegerField(),
            ),
            priority_order=Case(
                When(priority='critical', then=1),
                When(priority='high', then=2),
                When(priority='medium', then=3),
                When(priority='low', then=4),
                default=5,
                output_field=IntegerField(),
            )
        ).order_by('status_order', 'priority_order', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add current filter for template highlighting
        status_filter = self.request.GET.get('status', 'all')
        context['current_filter'] = status_filter
        return context


class IssueDetailView(ReviewerOnlyAccessMixin, DetailView):
    """
    View details of a specific issue assigned to the reviewer.
    """
    template_name = "reviewer/issue_management/issue_detail.html"
    context_object_name = "issue"
    model = Issue
    slug_field = 'slug'
    slug_url_kwarg = 'issue_slug'
    
    def get_queryset(self):
        """
        Only show issues where the current user is assigned as a reviewer.
        """
        return Issue.objects.filter(
            reviewers=self.request.user
        ).select_related(
            'org',
            'space',
            'reporter',
            'assigned_to',
            'reviewed_by'
        ).prefetch_related(
            'images',
            'comments__user',
            'work_tasks__assigned_to',
            'work_tasks__resolution_images',
            'reviewers'
        )
