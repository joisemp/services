from django.urls import path
from . import views

app_name = 'transportation'

urlpatterns = [
    # Dashboard
    path('', views.transportation_dashboard, name='dashboard'),
    
    # Vehicle URLs
    path('vehicles/', views.vehicle_list, name='vehicle_list'),
    path('vehicles/create/', views.vehicle_create, name='vehicle_create'),
    path('vehicles/<slug:slug>/', views.vehicle_detail, name='vehicle_detail'),
    path('vehicles/<slug:slug>/edit/', views.vehicle_edit, name='vehicle_edit'),
    path('vehicles/<slug:slug>/delete/', views.vehicle_delete, name='vehicle_delete'),
    
    # Vehicle Model URLs
    path('models/', views.vehicle_model_list, name='vehicle_model_list'),
    path('models/create/', views.vehicle_model_create, name='vehicle_model_create'),
    
    # Maintenance URLs
    path('maintenance/', views.maintenance_list, name='maintenance_list'),
    path('maintenance/create/', views.maintenance_create, name='maintenance_create'),
    path('maintenance/<int:pk>/', views.maintenance_detail, name='maintenance_detail'),
    path('maintenance/<int:pk>/edit/', views.maintenance_edit, name='maintenance_edit'),
    path('maintenance/<int:pk>/delete/', views.maintenance_delete, name='maintenance_delete'),
    path('vehicles/<slug:vehicle_slug>/maintenance/create/', views.maintenance_create, name='maintenance_create_for_vehicle'),
    
    # Document URLs
    path('vehicles/<slug:vehicle_slug>/documents/create/', views.document_create, name='document_create'),
    
    # Component URLs
    path('components/', views.component_list, name='component_list'),
    path('components/<slug:slug>/', views.component_detail, name='component_detail'),
    
    # Inspection URLs
    path('instances/<slug:instance_slug>/inspections/create/', views.inspection_create, name='inspection_create'),
    
    # Reports
    path('reports/', views.reports, name='reports'),
    
    # HTMX endpoints
    path('ajax/get-models/', views.get_vehicle_models, name='get_vehicle_models'),
    path('ajax/vehicle-search/', views.vehicle_search_autocomplete, name='vehicle_search_autocomplete'),
    path('ajax/vehicle-model/create/', views.vehicle_model_create_ajax, name='vehicle_model_create_ajax'),
    path('ajax/vehicle-model/form/', views.vehicle_model_form_modal, name='vehicle_model_form_modal'),
    path('ajax/vehicle-model-options/', views.vehicle_model_options_ajax, name='vehicle_model_options_ajax'),
]