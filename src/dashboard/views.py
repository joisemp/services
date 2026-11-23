from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from ticket_management.models import Ticket, WorkTask
from config.mixins.access_mixin import (
    CentralAdminOnlyAccessMixin,
    SpaceAdminOnlyAccessMixin,
    SpaceAdminWithActiveSpaceMixin,
    TransportInchargeOnlyAccessMixin,
)


class DashboardDataMixin:
    """Reusable helpers for dashboard views."""

    template_name = ''
    recent_issue_limit = 6
    overdue_task_limit = 6
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
            return Ticket.objects.none()

        queryset = Ticket.objects.all()
        if org:
            queryset = queryset.filter(org=org)

        if not user.is_superuser and getattr(user, 'user_type', '') == 'space_admin':
            active_space = getattr(user, 'active_space', None)
            if active_space:
                queryset = queryset.filter(space=active_space)
            else:
                spaces = user.spaces.all()
                if spaces.exists():
                    queryset = queryset.filter(space__in=spaces)
                else:
                    return Ticket.objects.none()

        return queryset.select_related('reporter', 'assigned_to', 'org', 'space')

    def get_recent_tickets(self, queryset):
        recent_queryset = queryset.order_by('-created_at')[: self.recent_issue_limit]
        tickets = []
        status_labels = dict(Ticket.STATUS_CHOICES)
        priority_labels = dict(Ticket.PRIORITY_CHOICES)

        for ticket in recent_queryset:
            reporter = ticket.reporter.get_full_name() or ticket.reporter.email or ticket.reporter.phone_number
            tickets.append(
                {
                    'title': ticket.title,
                    'created_at': ticket.created_at,
                    'priority': ticket.priority,
                    'priority_display': priority_labels.get(ticket.priority, ticket.priority.title()),
                    'priority_class': self.priority_style_map.get(ticket.priority, 'text-bg-secondary'),
                    'reporter': reporter,
                    'status': ticket.status,
                    'status_display': status_labels.get(ticket.status, ticket.status.title()),
                    'status_class': self.status_style_map.get(ticket.status, 'text-bg-secondary'),
                    'url': self.get_ticket_detail_url(ticket),
                }
            )
        return tickets

    def get_ticket_detail_url(self, ticket):
        return reverse(self.get_ticket_detail_route_name(), kwargs={'ticket_slug': ticket.slug})

    def get_view_all_url(self):
        return reverse(self.get_ticket_list_route_name())

    def get_ticket_list_route_name(self):
        raise NotImplementedError

    def get_ticket_detail_route_name(self):
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

        ticket_ids = list(queryset.values_list('pk', flat=True))
        if ticket_ids:
            work_tasks = WorkTask.objects.filter(ticket__in=ticket_ids)
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
            {'label': 'Total Tickets', 'value': total_issues, 'variant': 'primary', 'icon': 'insights'},
            {'label': 'Active Tickets', 'value': active_issues, 'variant': 'info', 'icon': 'pending'},
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
        in_progress_counts = (
            queryset.filter(status='in_progress', updated_at__gte=start_month)
            .annotate(month=TruncMonth('updated_at'))
            .values('month')
            .annotate(count=Count('id'))
        )

        created_map = {entry['month'].date(): entry['count'] for entry in created_counts if entry['month']}
        resolved_map = {entry['month'].date(): entry['count'] for entry in resolved_counts if entry['month']}
        in_progress_map = {entry['month'].date(): entry['count'] for entry in in_progress_counts if entry['month']}

        labels = []
        created_data = []
        resolved_data = []
        in_progress_data = []

        current_month = start_month
        for _ in range(self.trend_months):
            month_point = current_month.date()
            labels.append(current_month.strftime('%b %Y'))
            created_data.append(created_map.get(month_point, 0))
            resolved_data.append(resolved_map.get(month_point, 0))
            in_progress_data.append(in_progress_map.get(month_point, 0))
            current_month = self._add_month(current_month)

        return {
            'type': 'line',
            'data': {
                'labels': labels,
                'datasets': [
                    {
                        'label': 'New',
                        'data': created_data,
                        'borderColor': '#2563EB',
                        'backgroundColor': 'rgba(37, 99, 235, 0.07)',
                        'fill': True,
                        'tension': 0.4,
                        'pointRadius': 3,
                        'pointHoverRadius': 5,
                        'pointBackgroundColor': '#2563EB',
                        'pointBorderColor': '#fff',
                        'pointBorderWidth': 2,
                        'borderWidth': 2,
                    },
                    {
                        'label': 'In Progress',
                        'data': in_progress_data,
                        'borderColor': '#7c3aed',
                        'backgroundColor': 'rgba(124, 58, 237, 0.05)',
                        'fill': True,
                        'tension': 0.4,
                        'pointRadius': 3,
                        'pointHoverRadius': 5,
                        'pointBackgroundColor': '#7c3aed',
                        'pointBorderColor': '#fff',
                        'pointBorderWidth': 2,
                        'borderWidth': 2,
                    },
                    {
                        'label': 'Resolved',
                        'data': resolved_data,
                        'borderColor': '#16a34a',
                        'backgroundColor': 'rgba(22, 163, 74, 0.06)',
                        'fill': True,
                        'tension': 0.4,
                        'pointRadius': 3,
                        'pointHoverRadius': 5,
                        'pointBackgroundColor': '#16a34a',
                        'pointBorderColor': '#fff',
                        'pointBorderWidth': 2,
                        'borderWidth': 2,
                    },
                ],
            },
            'options': {
                'responsive': True,
                'maintainAspectRatio': False,
                'interaction': {'mode': 'index', 'intersect': False},
                'plugins': {
                    'legend': {
                        'position': 'top',
                        'align': 'end',
                        'labels': {
                            'usePointStyle': True,
                            'pointStyle': 'circle',
                            'boxWidth': 7,
                            'boxHeight': 7,
                            'padding': 20,
                            'color': '#6b7280',
                            'font': {'size': 12, 'family': 'Inter, system-ui, sans-serif'},
                        },
                    },
                    'tooltip': {
                        'backgroundColor': '#fff',
                        'borderColor': '#e5e7eb',
                        'borderWidth': 1,
                        'titleColor': '#111827',
                        'bodyColor': '#6b7280',
                        'titleFont': {'size': 13, 'weight': '600', 'family': 'Inter, system-ui, sans-serif'},
                        'bodyFont': {'size': 12, 'family': 'Inter, system-ui, sans-serif'},
                        'padding': 12,
                        'cornerRadius': 8,
                        'boxPadding': 4,
                    },
                },
                'scales': {
                    'y': {
                        'beginAtZero': True,
                        'ticks': {
                            'precision': 0,
                            'color': '#9ca3af',
                            'font': {'size': 11, 'family': 'Inter, system-ui, sans-serif'},
                            'maxTicksLimit': 5,
                        },
                        'grid': {'color': '#f3f4f6'},
                        'border': {'display': False, 'dash': [4, 4]},
                    },
                    'x': {
                        'ticks': {
                            'color': '#9ca3af',
                            'font': {'size': 11, 'family': 'Inter, system-ui, sans-serif'},
                            'maxRotation': 0,
                        },
                        'grid': {'display': False},
                        'border': {'display': False},
                    },
                },
            },
        }

    def get_status_breakdown(self, queryset):
        status_counts = queryset.values('status').annotate(count=Count('id'))
        count_map = {item['status']: item['count'] for item in status_counts}
        total = sum(count_map.values()) or 1

        breakdown = []
        for key, label in Ticket.STATUS_CHOICES:
            count = count_map.get(key, 0)
            breakdown.append(
                {
                    'status': key,
                    'label': label,
                    'count': count,
                    'percent': round((count / total) * 100),
                    'badge_class': self.status_style_map.get(key, 'text-bg-secondary'),
                }
            )
        return breakdown

    def get_priority_breakdown(self, queryset):
        priority_counts = queryset.values('priority').annotate(count=Count('id'))
        count_map = {item['priority']: item['count'] for item in priority_counts}
        total = sum(count_map.values()) or 1
        breakdown = []
        for key, label in Ticket.PRIORITY_CHOICES:
            count = count_map.get(key, 0)
            breakdown.append(
                {
                    'priority': key,
                    'label': label,
                    'count': count,
                    'percent': round((count / total) * 100),
                    'badge_class': self.priority_style_map.get(key, 'text-bg-secondary'),
                }
            )
        return breakdown

    def get_overdue_tasks(self, queryset):
        now = timezone.now()
        ticket_ids = list(queryset.values_list('pk', flat=True))
        if not ticket_ids:
            return []

        overdue_qs = (
            WorkTask.objects.filter(
                ticket__in=ticket_ids,
                completed=False,
                due_date__isnull=False,
                due_date__lt=now,
            )
            .select_related('ticket', 'assigned_to')
            .order_by('due_date')[: self.overdue_task_limit]
        )

        tasks = []
        for task in overdue_qs:
            assignee = (
                task.assigned_to.get_full_name()
                or task.assigned_to.email
                or task.assigned_to.phone_number
            )
            tasks.append(
                {
                    'title': task.title,
                    'ticket_title': task.ticket.title,
                    'due_date': task.due_date,
                    'assigned_to': assignee,
                    'url': self.get_ticket_detail_url(task.ticket),
                }
            )
        return tasks

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        issue_queryset = self.get_issue_queryset()

        context.update(
            {
                'summary_cards': self.get_summary_cards(issue_queryset),
                'chart_config': self.get_trend_config(issue_queryset),
                'recent_tickets': self.get_recent_tickets(issue_queryset),
                'overdue_tasks': self.get_overdue_tasks(issue_queryset),
                'status_breakdown': self.get_status_breakdown(issue_queryset),
                'priority_breakdown': self.get_priority_breakdown(issue_queryset),
                'view_all_issues_url': self.get_view_all_url(),
                'status_style_map': self.status_style_map,
                'priority_style_map': self.priority_style_map,
                'active_space': getattr(self.request.user, 'active_space', None),
            }
        )

        return context


class CentralAdminDashboardView(CentralAdminOnlyAccessMixin, DashboardDataMixin, TemplateView):
    template_name = 'central_admin/dashboard.html'

    def get_ticket_list_route_name(self):
        return 'ticket_management:central_admin:ticket_list'

    def get_ticket_detail_route_name(self):
        return 'ticket_management:central_admin:ticket_detail'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['quick_links'] = [
            {
                'label': 'People',
                'url': reverse('core:people_list'),
                'icon': 'group',
                'hint': 'Manage users & roles',
            },
            {
                'label': 'Spaces',
                'url': reverse('core:space_list'),
                'icon': 'apartment',
                'hint': 'Sites & locations',
            },
            {
                'label': 'Inventory',
                'url': reverse('inventory:central_admin:inventory_dashboard'),
                'icon': 'inventory_2',
                'hint': 'Stock & assets',
            },
        ]
        return context


class SpaceAdminDashboardView(SpaceAdminWithActiveSpaceMixin, DashboardDataMixin, TemplateView):
    template_name = 'space_admin/dashboard.html'

    def get_ticket_list_route_name(self):
        return 'ticket_management:space_admin:ticket_list'

    def get_ticket_detail_route_name(self):
        return 'ticket_management:space_admin:ticket_detail'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['quick_links'] = [
            {
                'label': 'Tickets',
                'url': reverse('ticket_management:space_admin:ticket_list'),
                'icon': 'confirmation_number',
            },
            {
                'label': 'Site visits',
                'url': reverse('ticket_management:space_admin:site_visit_list'),
                'icon': 'location_on',
            },
            {
                'label': 'Switch space',
                'url': reverse('core:switch_space'),
                'icon': 'swap_horiz',
            },
        ]
        return context


class TransportInchargeDashboardView(TransportInchargeOnlyAccessMixin, TemplateView):
    template_name = 'transport_incharge/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['transport_summary'] = {
            'active_vehicles': 12,
            'on_trip': 5,
            'in_maintenance': 2,
            'available': 5,
        }
        context['today_schedule'] = [
            {'vehicle': 'KL-07-AB-1021', 'route': 'City Hub -> North Depot', 'status': 'On Time'},
            {'vehicle': 'KL-07-AB-1184', 'route': 'South Depot -> Airport', 'status': 'Delayed'},
            {'vehicle': 'KL-07-AB-1210', 'route': 'Warehouse A -> Service Center', 'status': 'On Time'},
        ]
        return context
