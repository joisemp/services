"""
Fleet Management URLs for Maintainer role.
Maintainers have restricted access based on assigned issues/tasks or permissions.
"""
from django.urls import path
from fleet_management.views import maintainer

app_name = 'fleet_management_maintainer'

urlpatterns = [
    # Add maintainer routes here
    # TODO: Define URLs for fleet_management maintainer views
    # TODO: Add permission checks for assigned fleet-related issues/tasks
]
