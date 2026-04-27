"""
Fleet Management URLs for Supervisor role.
Supervisors have restricted access based on assigned issues/tasks or permissions.
"""
from django.urls import path
from fleet_management.views import supervisor

app_name = 'fleet_management_supervisor'

urlpatterns = [
    # Add supervisor routes here
    # TODO: Define URLs for fleet_management supervisor views
    # TODO: Add permission checks for assigned fleet-related issues/tasks
]
