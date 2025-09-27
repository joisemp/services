from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.views.generic import TemplateView

from issue_management.models import Issue


class DashboardMetricsMixin:
    """Shared helpers for dashboard views that expose issue metrics."""

    status_badge_classes = {
        'open': 'text-bg-primary',
        'assigned': 'text-bg-info',
        'in_progress': 'text-bg-info',
        'resolved': 'text-bg-success',
        'escalated': 'text-bg-warning',
        'closed': 'text-bg-secondary',
        'cancelled': 'text-bg-dark',
    }

    priority_badge_classes = {
        'low': 'text-bg-success',
        'medium': 'text-bg-warning',
        'high': 'text-bg-danger',
        'critical': 'text-bg-danger',
    }

    def get_issue_queryset(self):
        """Return the base queryset used for metrics. Override per view."""
        return Issue.objects.none()

    def get_dashboard_scope_label(self):
        return 'your organization'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        issues_queryset = self.get_issue_queryset().select_related(
            'reporter', 'assigned_to', 'space', 'org'
        )

        metrics = self._build_issue_metrics(self.request.user, issues_queryset)
        context.update(metrics)
        context['dashboard_scope_label'] = self.get_dashboard_scope_label()
        context['organization_name'] = getattr(getattr(self.request.user, 'organization', None), 'name', None)
        return context

    def _build_issue_metrics(self, user, issues_queryset):
        counts = issues_queryset.aggregate(
            total=Count('id'),
            open=Count('id', filter=Q(status='open')),
            active=Count('id', filter=Q(status__in=['assigned', 'in_progress'])),
            resolved=Count('id', filter=Q(status__in=['resolved', 'closed'])),
        )

        recent_issues = list(issues_queryset.order_by('-created_at')[:6])
        for issue in recent_issues:
            issue.status_badge_class = self.status_badge_classes.get(issue.status, 'text-bg-secondary')
            issue.priority_badge_class = self.priority_badge_classes.get(issue.priority, 'text-bg-secondary')

        chart_data = self._build_chart_data(issues_queryset)

        return {
            'total_issues': counts['total'],
            'open_issues': counts['open'],
            'active_issues': counts['active'],
            'resolved_issues': counts['resolved'],
            'greeting_name': user.first_name or user.get_short_name() or 'there',
            'recent_issues': recent_issues,
            'chart_data': chart_data,
        }

    def _build_chart_data(self, issues_queryset):
        def shift_month(reference, delta):
            year = reference.year + (reference.month - 1 + delta) // 12
            month = (reference.month - 1 + delta) % 12 + 1
            return reference.replace(year=year, month=month)

        now = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_starts = [shift_month(now, -offset) for offset in range(5, -1, -1)]
        month_labels = [month.strftime('%b %Y') for month in month_starts]

        def month_key(dt):
            return dt.strftime('%Y-%m')

        reported_counts = {
            month_key(entry['month']): entry['total']
            for entry in (
                issues_queryset.annotate(month=TruncMonth('created_at'))
                .filter(month__gte=month_starts[0])
                .values('month')
                .annotate(total=Count('id'))
            )
        }

        closed_counts = {
            month_key(entry['month']): entry['total']
            for entry in (
                issues_queryset.filter(status__in=['resolved', 'closed'])
                .annotate(month=TruncMonth('updated_at'))
                .filter(month__gte=month_starts[0])
                .values('month')
                .annotate(total=Count('id'))
            )
        }

        datasets = [
            {
                'label': 'Reported Issues',
                'data': [reported_counts.get(month_key(month), 0) for month in month_starts],
                'borderColor': '#4C6EF5',
                'backgroundColor': 'rgba(76, 110, 245, 0.1)',
                'fill': True,
            },
            {
                'label': 'Resolved Issues',
                'data': [closed_counts.get(month_key(month), 0) for month in month_starts],
                'borderColor': '#2F9E44',
                'backgroundColor': 'rgba(47, 158, 68, 0.1)',
                'fill': True,
            },
        ]

        total_points = sum(sum(dataset['data']) for dataset in datasets)

        return {
            'labels': month_labels,
            'datasets': datasets,
            'has_activity': total_points > 0,
        }


class CentralAdminDashboardView(DashboardMetricsMixin, TemplateView):
    template_name = 'central_admin/dashboard.html'

    def get_issue_queryset(self):
        user = self.request.user
        organization = getattr(user, 'organization', None)

        if user.is_superuser and organization is None:
            return Issue.objects.all()

        if organization:
            return Issue.objects.filter(org=organization)

        return Issue.objects.none()

    def get_dashboard_scope_label(self):
        organization = getattr(self.request.user, 'organization', None)
        if organization:
            return organization.name
        return 'all organizations'


class SpaceAdminDashboardView(DashboardMetricsMixin, TemplateView):
    template_name = 'space_admin/dashboard.html'

    def get_issue_queryset(self):
        user = self.request.user
        organization = getattr(user, 'organization', None)

        if not organization:
            return Issue.objects.none()

        queryset = Issue.objects.filter(org=organization)

        spaces_manager = getattr(user, 'spaces', None)
        if spaces_manager is not None:
            user_spaces = spaces_manager.all()
            if user_spaces.exists():
                queryset = queryset.filter(Q(space__in=user_spaces) | Q(space__isnull=True))

        return queryset

    def get_dashboard_scope_label(self):
        return 'your spaces'
