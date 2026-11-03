"""
Fleet Management Common URLs.
Routes accessible to all authenticated users (role-specific routes in role_urls/).
"""
from django.urls import path, include
from fleet_management.views import common

app_name = 'fleet_management'

urlpatterns = [
    # Common URLs - accessible to all authenticated users
    # TODO: Add shared fleet_management views accessible to all roles
    
    # Role-based URL patterns for fleet management
    path('central-admin/', include('fleet_management.role_urls.central_admin')),
    path('maintainer/', include('fleet_management.role_urls.maintainer')),
    path('reviewer/', include('fleet_management.role_urls.reviewer')),
    path('supervisor/', include('fleet_management.role_urls.supervisor')),
    path('transport-incharge/', include('fleet_management.role_urls.transport_incharge')),
]
