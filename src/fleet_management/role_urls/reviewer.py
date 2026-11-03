"""
Fleet Management URLs for Reviewer role.
Reviewers have restricted access based on assigned issues/tasks or permissions.
"""
from django.urls import path
from fleet_management.views import reviewer

app_name = 'fleet_management_reviewer'

urlpatterns = [
    # Add reviewer routes here
    # TODO: Define URLs for fleet_management reviewer views
    # TODO: Add permission checks for assigned fleet-related issues/tasks
]
