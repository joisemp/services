from django.urls import path

from ..views import supervisor

app_name = 'supervisor'

urlpatterns = [
    path('', supervisor.InventoryDashboardView.as_view(), name='inventory_dashboard'),
]
