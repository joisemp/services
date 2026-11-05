"""
URL configuration for config project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.utils import extend_schema
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.permissions import IsAdminUser

from core.api.health import HealthView
from core.api.openapi import error_responses
from dashboard.api import DashboardAPIView
from .views import HomePageView, ServiceWorkerView


class DocumentedSchemaView(SpectacularAPIView):
    """Raw OpenAPI schema — admin session required."""

    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=['System'],
        summary='OpenAPI schema',
        responses={200: {'description': 'OpenAPI 3 schema.'}, **error_responses(401, 403)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class DocumentedSwaggerView(SpectacularSwaggerView):
    """Swagger UI — admin session required."""

    permission_classes = [IsAdminUser]
    url_name = 'schema'

    @extend_schema(
        tags=['System'],
        summary='Swagger UI',
        responses={200: {'description': 'Swagger UI HTML.'}, **error_responses(401, 403)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class DocumentedRedocView(SpectacularRedocView):
    """ReDoc — admin session required."""

    permission_classes = [IsAdminUser]
    url_name = 'schema'

    @extend_schema(
        tags=['System'],
        summary='ReDoc',
        responses={200: {'description': 'ReDoc HTML.'}, **error_responses(401, 403)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('django.contrib.auth.urls')),
    path('', HomePageView.as_view(), name='home'),
    path('firebase-messaging-sw.js', ServiceWorkerView.as_view(), name='firebase-sw'),
    path('core/', include('core.urls')),
    path('tickets/', include('ticket_management.urls')),
    path('inventory/', include('inventory.urls')),
    path('fleet/', include('fleet_management.urls')),
    path('dashboard/', include('dashboard.urls')),
    # API
    path('api/auth/', include('core.api.auth.urls')),
    path('api/health/', HealthView.as_view(), name='api-health'),
    path('api/dashboard/', DashboardAPIView.as_view(), name='api-dashboard'),
    path('api/', include('core.api.urls')),
    path('api/', include('ticket_management.api.urls')),
    path('api/schema/', DocumentedSchemaView.as_view(), name='schema'),
    path('api/docs/', DocumentedSwaggerView.as_view(), name='swagger-ui'),
    path('api/redoc/', DocumentedRedocView.as_view(), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
