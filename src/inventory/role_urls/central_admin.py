from django.urls import path

from ..views import central_admin

app_name = 'central_admin'

urlpatterns = [
    path('', central_admin.CentralAdminInventoryDashboardView.as_view(), name='inventory_dashboard'),
    path('categories/', central_admin.CentralAdminCategoryListView.as_view(), name='category_list'),
    path('brands/', central_admin.CentralAdminBrandListView.as_view(), name='brand_list'),
]
