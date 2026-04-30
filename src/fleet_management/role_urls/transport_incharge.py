"""
Fleet Management URLs for Transport Incharge role.
Transport Incharge has full access to all fleet management features.
"""
from django.urls import path
from fleet_management.views import transport_incharge

app_name = 'transport_incharge'

urlpatterns = [
    path('', transport_incharge.VehicleListView.as_view(), name='fleet_list'),
    path('vehicles/', transport_incharge.VehicleListView.as_view(), name='vehicle_list'),
    path('vehicles/create/', transport_incharge.VehicleCreateView.as_view(), name='vehicle_create'),
    path('vehicles/<slug:slug>/', transport_incharge.VehicleDetailView.as_view(), name='vehicle_detail'),
    path('vehicles/<slug:slug>/maintenance/', transport_incharge.VehicleMaintenanceView.as_view(), name='vehicle_maintenance'),
    path('vehicles/<slug:slug>/trips/', transport_incharge.VehicleTripsView.as_view(), name='vehicle_trips'),
    path('vehicles/<slug:slug>/expenses/', transport_incharge.VehicleExpensesView.as_view(), name='vehicle_expenses'),
    path('vehicles/<slug:slug>/edit/', transport_incharge.VehicleUpdateView.as_view(), name='vehicle_update'),
    path('vehicles/<slug:slug>/delete/', transport_incharge.VehicleDeleteView.as_view(), name='vehicle_delete'),
]
