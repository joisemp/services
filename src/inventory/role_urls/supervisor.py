from django.urls import path

from ..views import supervisor

app_name = 'supervisor'

urlpatterns = [
    path('', supervisor.InventoryDashboardView.as_view(), name='inventory_dashboard'),
    path('warehouses/<slug:slug>/', supervisor.InventoryWarehouseDetailView.as_view(), name='warehouse_detail'),
    path('warehouses/<slug:slug>/products/', supervisor.InventoryWarehouseProductListView.as_view(), name='warehouse_products'),
    path('warehouses/<slug:slug>/products/<slug:product_slug>/stock-movements/create/', supervisor.SupervisorStockMovementCreateView.as_view(), name='stock_movement_create'),
    path('warehouses/<slug:slug>/stock-movements/history/', supervisor.SupervisorStockMovementHistoryView.as_view(), name='stock_movement_history'),
    path('warehouses/<slug:slug>/products/<slug:product_slug>/', supervisor.SupervisorProductDetailView.as_view(), name='product_detail'),
    path('warehouses/<slug:slug>/products/<slug:product_slug>/assign-room/', supervisor.SupervisorProductAssignRoomView.as_view(), name='product_assign_room'),
    path('warehouses/<slug:slug>/products/<slug:product_slug>/assign-bucket/', supervisor.SupervisorProductAssignBucketView.as_view(), name='product_assign_bucket'),
    path('warehouses/<slug:slug>/products/<slug:product_slug>/assign-category/', supervisor.SupervisorProductAssignCategoryView.as_view(), name='product_assign_category'),
    path('warehouses/<slug:slug>/products/<slug:product_slug>/assign-brand/', supervisor.SupervisorProductAssignBrandView.as_view(), name='product_assign_brand'),
    path('warehouses/<slug:slug>/products/<slug:product_slug>/variants/create/', supervisor.SupervisorProductVariantCreateView.as_view(), name='product_variant_create'),
    path('warehouses/<slug:slug>/products/<slug:product_slug>/variants/<slug:variant_slug>/update/', supervisor.SupervisorProductVariantUpdateView.as_view(), name='product_variant_update'),
    path('warehouses/<slug:slug>/products/<slug:product_slug>/variants/<slug:variant_slug>/delete/', supervisor.SupervisorProductVariantDeleteView.as_view(), name='product_variant_delete'),
    path('warehouses/<slug:slug>/products/create/step-1/', supervisor.SupervisorProductCreateStepOneView.as_view(), name='product_create_step1'),
    path('warehouses/<slug:slug>/products/create/step-2/', supervisor.SupervisorProductCreateStepTwoView.as_view(), name='product_create_step2'),
    path('warehouses/<slug:slug>/products/create/step-3/single-variant/', supervisor.SupervisorProductCreateSingleVariantStepView.as_view(), name='product_create_step3_single'),
    path('warehouses/<slug:slug>/rooms/create/', supervisor.SupervisorCreateRoomView.as_view(), name='create_room'),
    path('warehouses/<slug:slug>/rooms/<slug:room_slug>/buckets/create/', supervisor.SupervisorCreateBucketView.as_view(), name='create_bucket'),
]
