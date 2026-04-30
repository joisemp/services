"""
Fleet Management URLs for Central Admin role.
Central admin has full access to all fleet management features.
"""
from django.urls import path
from fleet_management.views import central_admin

app_name = 'central_admin'

urlpatterns = [
    path('', central_admin.VehicleListView.as_view(), name='fleet_list'),
    path('vehicles/', central_admin.VehicleListView.as_view(), name='vehicle_list'),
    path('vehicles/create/', central_admin.VehicleCreateView.as_view(), name='vehicle_create'),
    path('vehicles/<slug:slug>/', central_admin.VehicleDetailView.as_view(), name='vehicle_detail'),
    path('vehicles/<slug:slug>/maintenance/', central_admin.VehicleMaintenanceView.as_view(), name='vehicle_maintenance'),
    path('vehicles/<slug:slug>/trips/', central_admin.VehicleTripsView.as_view(), name='vehicle_trips'),
    path('vehicles/<slug:slug>/fuel/', central_admin.VehicleFuelView.as_view(), name='vehicle_fuel'),
    path('vehicles/<slug:slug>/inspections/', central_admin.VehicleInspectionsView.as_view(), name='vehicle_inspections'),
    path('vehicles/<slug:slug>/edit/', central_admin.VehicleUpdateView.as_view(), name='vehicle_update'),
    path('vehicles/<slug:slug>/delete/', central_admin.VehicleDeleteView.as_view(), name='vehicle_delete'),
]
