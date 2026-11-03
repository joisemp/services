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
    path('vehicles/<slug:slug>/expenses/list/', transport_incharge.VehicleExpenseListView.as_view(), name='vehicle_expense_list'),
    path('vehicles/<slug:slug>/expenses/create/', transport_incharge.ExpenseCreateView.as_view(), name='vehicle_expense_create'),
    path('vehicles/<slug:slug>/status/', transport_incharge.VehicleStatusChangeView.as_view(), name='vehicle_status_change'),
    path('vehicles/<slug:slug>/edit/', transport_incharge.VehicleUpdateView.as_view(), name='vehicle_update'),
    path('vehicles/<slug:slug>/delete/', transport_incharge.VehicleDeleteView.as_view(), name='vehicle_delete'),
    
    # Expense management (organization-level)
    path('expenses/', transport_incharge.ExpenseListView.as_view(), name='expense_list'),
    path('expenses/create/', transport_incharge.ExpenseCreateView.as_view(), name='expense_create'),
    path('expenses/<int:pk>/edit/', transport_incharge.ExpenseUpdateView.as_view(), name='expense_update'),
    path('expenses/<int:pk>/delete/', transport_incharge.ExpenseDeleteView.as_view(), name='expense_delete'),
    
    path('workshops/', transport_incharge.WorkshopListView.as_view(), name='workshop_list'),
    path('workshops/create/', transport_incharge.WorkshopCreateView.as_view(), name='workshop_create'),
    path('workshops/<slug:slug>/', transport_incharge.WorkshopDetailView.as_view(), name='workshop_detail'),
    path('workshops/<slug:slug>/edit/', transport_incharge.WorkshopUpdateView.as_view(), name='workshop_update'),
    path('workshops/<slug:slug>/delete/', transport_incharge.WorkshopDeleteView.as_view(), name='workshop_delete'),
]
