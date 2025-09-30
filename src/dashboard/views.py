from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from issue_management.models import Issue, WorkTask
from config.mixins.access_mixin import CentralAdminOnlyAccessMixin


class DashboardDataMixin:
    """Reusable helpers for dashboard views."""

    template_name = ''
    recent_issue_limit = 6
    trend_months = 6

    status_style_map = {
        'open': 'text-bg-secondary',
        'assigned': 'text-bg-info',
        'in_progress': 'text-bg-primary',
        'resolved': 'text-bg-success',
        'escalated': 'text-bg-warning',
        'closed': 'text-bg-dark',
        'cancelled': 'text-bg-light text-dark',
    }

    priority_style_map = {
        'low': 'text-bg-success',
        'medium': 'text-bg-warning',
        'high': 'text-bg-danger',
        'critical': 'text-bg-danger',
    }

    @staticmethod
    def _month_floor(dt):
        return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def _subtract_months(dt, months):
        year = dt.year
        month = dt.month
        for _ in range(months):
            month -= 1
            if month == 0:
                month = 12
                year -= 1
        return dt.replace(year=year, month=month)

    @staticmethod
    def _add_month(dt):
        year = dt.year
        month = dt.month + 1
        if month > 12:
            month = 1
            year += 1
        return dt.replace(year=year, month=month)

    def get_issue_queryset(self):
        user = self.request.user
        org = getattr(user, 'organization', None)

        if not org and not user.is_superuser:
            return Issue.objects.none()

        queryset = Issue.objects.all()
        if org:
            queryset = queryset.filter(org=org)

        if not user.is_superuser and getattr(user, 'user_type', '') == 'space_admin':
            spaces = user.spaces.all()
            if spaces.exists():
                queryset = queryset.filter(space__in=spaces)
            else:
                return Issue.objects.none()

        return queryset.select_related('reporter', 'assigned_to', 'org', 'space')

    def get_recent_issues(self, queryset):
        recent_queryset = queryset.order_by('-created_at')[: self.recent_issue_limit]
        issues = []
        status_labels = dict(Issue.STATUS_CHOICES)
        priority_labels = dict(Issue.PRIORITY_CHOICES)

        for issue in recent_queryset:
            reporter = issue.reporter.get_full_name() or issue.reporter.email or issue.reporter.phone_number
            issues.append(
                {
                    'title': issue.title,
                    'created_at': issue.created_at,
                    'priority': issue.priority,
                    'priority_display': priority_labels.get(issue.priority, issue.priority.title()),
                    'priority_class': self.priority_style_map.get(issue.priority, 'text-bg-secondary'),
                    'reporter': reporter,
                    'status': issue.status,
                    'status_display': status_labels.get(issue.status, issue.status.title()),
                    'status_class': self.status_style_map.get(issue.status, 'text-bg-secondary'),
                    'url': self.get_issue_detail_url(issue),
                }
            )
        return issues

    def get_issue_detail_url(self, issue):
        return reverse(self.get_issue_detail_route_name(), kwargs={'issue_slug': issue.slug})

    def get_view_all_url(self):
        return reverse(self.get_issue_list_route_name())

    def get_issue_list_route_name(self):
        raise NotImplementedError

    def get_issue_detail_route_name(self):
        raise NotImplementedError

    def get_summary_cards(self, queryset):
        now = timezone.now()
        month_start = self._month_floor(now)

        total_issues = queryset.count()
        active_statuses = ['open', 'assigned', 'in_progress', 'escalated']
        active_issues = queryset.filter(status__in=active_statuses).count()
        resolved_this_month = queryset.filter(
            status__in=['resolved', 'closed'],
            updated_at__gte=month_start,
        ).count()

        issue_ids = list(queryset.values_list('pk', flat=True))
        if issue_ids:
            work_tasks = WorkTask.objects.filter(issue__in=issue_ids)
            pending_tasks = work_tasks.filter(completed=False).count()
            overdue_tasks = work_tasks.filter(
                completed=False,
                due_date__isnull=False,
                due_date__lt=now,
            ).count()
        else:
            pending_tasks = 0
            overdue_tasks = 0

        summary = [
            {'label': 'Total Issues', 'value': total_issues, 'variant': 'primary', 'icon': 'insights'},
            {'label': 'Active Issues', 'value': active_issues, 'variant': 'info', 'icon': 'pending'},
            {'label': 'Resolved This Month', 'value': resolved_this_month, 'variant': 'success', 'icon': 'task_alt'},
            {'label': 'Overdue Tasks', 'value': overdue_tasks, 'variant': 'danger', 'icon': 'warning'},
            {'label': 'Pending Tasks', 'value': pending_tasks, 'variant': 'warning', 'icon': 'assignment'},
        ]

        return summary

    def get_trend_config(self, queryset):
        now = timezone.now()
        base_month = self._month_floor(now)
        start_month = self._subtract_months(base_month, self.trend_months - 1)

        created_counts = (
            queryset.filter(created_at__gte=start_month)
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(count=Count('id'))
        )
        resolved_counts = (
            queryset.filter(status__in=['resolved', 'closed'], updated_at__gte=start_month)
            .annotate(month=TruncMonth('updated_at'))
            .values('month')
            .annotate(count=Count('id'))
        )

        created_map = {entry['month'].date(): entry['count'] for entry in created_counts if entry['month']}
        resolved_map = {entry['month'].date(): entry['count'] for entry in resolved_counts if entry['month']}

        labels = []
        created_data = []
        resolved_data = []

        current_month = start_month
        for _ in range(self.trend_months):
            month_point = current_month.date()
            labels.append(current_month.strftime('%b %Y'))
            created_data.append(created_map.get(month_point, 0))
            resolved_data.append(resolved_map.get(month_point, 0))
            current_month = self._add_month(current_month)

        return {
            'type': 'line',
            'data': {
                'labels': labels,
                'datasets': [
                    {
                        'label': 'New Issues',
                        'data': created_data,
                        'borderColor': 'rgba(54, 162, 235, 1)',
                        'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                        'fill': True,
                        'tension': 0.3,
                    },
                    {
                        'label': 'Issues Resolved',
                        'data': resolved_data,
                        'borderColor': 'rgba(75, 192, 192, 1)',
                        'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                        'fill': True,
                        'tension': 0.3,
                    },
                ],
            },
            'options': {
                'responsive': True,
                'maintainAspectRatio': False,
                'interaction': {'mode': 'index', 'intersect': False},
                'plugins': {'legend': {'position': 'top'}},
                'scales': {'y': {'beginAtZero': True, 'precision': 0}},
            },
        }

    def get_status_breakdown(self, queryset):
        status_counts = queryset.values('status').annotate(count=Count('id'))
        count_map = {item['status']: item['count'] for item in status_counts}

        breakdown = []
        for key, label in Issue.STATUS_CHOICES:
            breakdown.append(
                {
                    'status': key,
                    'label': label,
                    'count': count_map.get(key, 0),
                    'badge_class': self.status_style_map.get(key, 'text-bg-secondary'),
                }
            )
        return breakdown

    def get_priority_breakdown(self, queryset):
        priority_counts = queryset.values('priority').annotate(count=Count('id'))
        count_map = {item['priority']: item['count'] for item in priority_counts}
        breakdown = []
        for key, label in Issue.PRIORITY_CHOICES:
            breakdown.append(
                {
                    'priority': key,
                    'label': label,
                    'count': count_map.get(key, 0),
                    'badge_class': self.priority_style_map.get(key, 'text-bg-secondary'),
                }
            )
        return breakdown

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        issue_queryset = self.get_issue_queryset()

        context.update(
            {
                'summary_cards': self.get_summary_cards(issue_queryset),
                'chart_config': self.get_trend_config(issue_queryset),
                'recent_issues': self.get_recent_issues(issue_queryset),
                'status_breakdown': self.get_status_breakdown(issue_queryset),
                'priority_breakdown': self.get_priority_breakdown(issue_queryset),
                'view_all_issues_url': self.get_view_all_url(),
                'status_style_map': self.status_style_map,
                'priority_style_map': self.priority_style_map,
            }
        )

        return context


class CentralAdminDashboardView(CentralAdminOnlyAccessMixin, DashboardDataMixin, TemplateView):
    template_name = 'central_admin/dashboard.html'

    def get_issue_list_route_name(self):
        return 'issue_management:central_admin:issue_list'

    def get_issue_detail_route_name(self):
        return 'issue_management:central_admin:issue_detail'


class SpaceAdminDashboardView(DashboardDataMixin, TemplateView):
    template_name = 'space_admin/dashboard.html'

    def get_issue_list_route_name(self):
        return 'issue_management:space_admin:issue_list'

    def get_issue_detail_route_name(self):
        return 'issue_management:space_admin:issue_detail'
