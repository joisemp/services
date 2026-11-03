"""Database health check endpoint."""
from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.openapi import HealthSerializer


@extend_schema(
    tags=['System'],
    summary='Health check',
    responses={200: HealthSerializer, 503: HealthSerializer},
)
class HealthView(APIView):
    """GET /api/health/ — checks database connectivity only."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        db_ok = False
        try:
            connection.ensure_connection()
            db_ok = True
        except Exception:
            db_ok = False

        payload = {
            'status': 'ok' if db_ok else 'degraded',
            'db': 'up' if db_ok else 'down',
        }
        code = status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(payload, status=code)
