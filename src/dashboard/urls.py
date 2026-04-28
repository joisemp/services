from django.urls import path
from . import views

app_name = 'dashboard'


urlpatterns = [
    path('central-admin/', views.CentralAdminDashboardView.as_view(), name='central_admin_dashboard'),
    path('space-admin/', views.SpaceAdminDashboardView.as_view(), name='space_admin_dashboard'),
    path('transport-incharge/', views.TransportInchargeDashboardView.as_view(), name='transport_incharge_dashboard'),
]