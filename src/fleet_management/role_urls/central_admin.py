"""
Fleet Management URLs for Central Admin role.
Central admin has full access to all fleet management features.
"""
from django.urls import path
from fleet_management.views import central_admin

app_name = 'central_admin'

urlpatterns = [
    path('', central_admin.FleetManagementListView.as_view(), name='fleet_list'),
]
