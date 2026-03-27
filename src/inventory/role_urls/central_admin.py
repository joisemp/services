from django.urls import path

from ..views import central_admin

app_name = 'central_admin'

urlpatterns = [
    path('', central_admin.CentralAdminInventoryDashboardView.as_view(), name='inventory_dashboard'),
    path('warehouses/create/', central_admin.CentralAdminCreateWarehouseView.as_view(), name='create_warehouse'),
    path('warehouses/<slug:slug>/', central_admin.CentralAdminWarehouseDetailView.as_view(), name='warehouse_detail'),
    path('warehouses/<slug:slug>/edit/', central_admin.CentralAdminEditWarehouseView.as_view(), name='edit_warehouse'),
    path('warehouses/<slug:slug>/add-user/', central_admin.CentralAdminWarehouseUserAddView.as_view(), name='warehouse_add_user'),
    path('warehouses/<slug:slug>/remove-user/', central_admin.CentralAdminWarehouseUserRemoveView.as_view(), name='warehouse_remove_user'),
    path('categories/', central_admin.CentralAdminCategoryListView.as_view(), name='category_list'),
    path('categories/create/', central_admin.CentralAdminCreateCategoryView.as_view(), name='create_category'),
    path('categories/<slug:slug>/edit/', central_admin.CentralAdminEditCategoryView.as_view(), name='edit_category'),
    path('brands/', central_admin.CentralAdminBrandListView.as_view(), name='brand_list'),
    path('brands/create/', central_admin.CentralAdminCreateBrandView.as_view(), name='create_brand'),
    path('brands/<slug:slug>/edit/', central_admin.CentralAdminEditBrandView.as_view(), name='edit_brand'),
]
