from django.urls import path

from ..views import central_admin

app_name = 'central_admin'

urlpatterns = [
    path('', central_admin.CentralAdminInventoryDashboardView.as_view(), name='inventory_dashboard'),
]
