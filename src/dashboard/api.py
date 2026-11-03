"""Dashboard JSON API reusing DashboardDataMixin helpers."""
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.openapi import error_responses
from core.api.permissions import IsDashboardRole
from dashboard.views import DashboardDataMixin
from fleet_management.models import Vehicle


class DashboardAPIView(DashboardDataMixin, APIView):
    """
    GET /api/dashboard/ — summary cards, trends, and recent issues for
    central admin / space admin, or a light transport summary for
    transport incharge.
    """

    permission_classes = [IsDashboardRole]

    def get_issue_list_route_name(self):
        return 'issue_management:central_admin:issue_list'

    def get_issue_detail_route_name(self):
        return 'issue_management:central_admin:issue_detail'

    def get_issue_detail_url(self, issue):
        # Prefer slug for API clients instead of HTML reverse routes.
        return f'/api/issues/{issue.slug}/'

    def get_view_all_url(self):
        return '/api/issues/'

    @extend_schema(
        tags=['Dashboard'],
        summary='Role dashboard summary',
        responses={200: dict, **error_responses(401, 403)},
    )
    def get(self, request):
        user = request.user
        if user.is_transport_incharge:
            org = user.organization
            vehicles = Vehicle.objects.filter(org=org) if org else Vehicle.objects.none()
            return Response(
                {
                    'role': 'transport_incharge',
                    'transport_summary': {
                        'total_vehicles': vehicles.count(),
                        'active': vehicles.filter(status=Vehicle.STATUS_ACTIVE).count(),
                        'in_maintenance': vehicles.filter(status=Vehicle.STATUS_IN_MAINTENANCE).count(),
                        'out_of_service': vehicles.filter(status=Vehicle.STATUS_OUT_OF_SERVICE).count(),
                    },
                }
            )

        if user.is_space_admin and not user.active_space:
            return Response(
                {'detail': 'Select an active space before continuing.'},
                status=403,
            )

        issue_queryset = self.get_issue_queryset()
        return Response(
            {
                'role': user.user_type,
                'summary_cards': self.get_summary_cards(issue_queryset),
                'chart_config': self.get_trend_config(issue_queryset),
                'recent_issues': self.get_recent_issues(issue_queryset),
                'status_breakdown': self.get_status_breakdown(issue_queryset),
                'priority_breakdown': self.get_priority_breakdown(issue_queryset),
                'active_space': (
                    {'slug': user.active_space.slug, 'name': user.active_space.name}
                    if getattr(user, 'active_space', None)
                    else None
                ),
            }
        )
