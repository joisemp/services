from django.urls import path

from ..views import supervisor

app_name = 'supervisor'

urlpatterns = [
    path('', supervisor.InventoryDashboardView.as_view(), name='inventory_dashboard'),
    path('categories/', supervisor.SupervisorCategoryListView.as_view(), name='category_list'),
    path('categories/create/', supervisor.SupervisorCreateCategoryView.as_view(), name='create_category'),
    path('categories/<slug:slug>/edit/', supervisor.SupervisorEditCategoryView.as_view(), name='edit_category'),
    path('categories/<slug:slug>/delete/', supervisor.SupervisorDeleteCategoryView.as_view(), name='delete_category'),
    path('brands/', supervisor.SupervisorBrandListView.as_view(), name='brand_list'),
    path('brands/create/', supervisor.SupervisorCreateBrandView.as_view(), name='create_brand'),
    path('brands/<slug:slug>/edit/', supervisor.SupervisorEditBrandView.as_view(), name='edit_brand'),
    path('brands/<slug:slug>/delete/', supervisor.SupervisorDeleteBrandView.as_view(), name='delete_brand'),
    path('warehouses/<slug:slug>/', supervisor.InventoryWarehouseDetailView.as_view(), name='warehouse_detail'),
    path('warehouses/<slug:slug>/products/', supervisor.InventoryWarehouseProductListView.as_view(), name='warehouse_products'),
    path('warehouses/<slug:slug>/products/<slug:product_slug>/stock-movements/create/', supervisor.SupervisorStockMovementCreateView.as_view(), name='stock_movement_create'),
    path('warehouses/<slug:slug>/stock-movements/history/', supervisor.SupervisorStockMovementHistoryView.as_view(), name='stock_movement_history'),
    path('warehouses/<slug:slug>/stock-movements/<int:movement_id>/correct/', supervisor.SupervisorStockMovementCorrectView.as_view(), name='stock_movement_correct'),
    path('warehouses/<slug:slug>/products/<slug:product_slug>/', supervisor.SupervisorProductDetailView.as_view(), name='product_detail'),
    path('warehouses/<slug:slug>/products/<slug:product_slug>/edit/', supervisor.SupervisorProductEditView.as_view(), name='product_edit'),
    path('warehouses/<slug:slug>/products/<slug:product_slug>/delete/', supervisor.SupervisorProductDeleteView.as_view(), name='product_delete'),
    path('warehouses/<slug:slug>/products/<slug:product_slug>/convert-type/', supervisor.SupervisorProductTypeConvertView.as_view(), name='product_convert_type'),
    path('warehouses/<slug:slug>/products/<slug:product_slug>/assign-room/', supervisor.SupervisorProductAssignRoomView.as_view(), name='product_assign_room'),
    path('warehouses/<slug:slug>/products/<slug:product_slug>/assign-bucket/', supervisor.SupervisorProductAssignBucketView.as_view(), name='product_assign_bucket'),
    path('warehouses/<slug:slug>/products/<slug:product_slug>/assign-category/', supervisor.SupervisorProductAssignCategoryView.as_view(), name='product_assign_category'),
    path('warehouses/<slug:slug>/products/<slug:product_slug>/assign-brand/', supervisor.SupervisorProductAssignBrandView.as_view(), name='product_assign_brand'),
    path('warehouses/<slug:slug>/products/<slug:product_slug>/images/manage/', supervisor.SupervisorProductImageManagementView.as_view(), name='product_images_manage'),
    path('warehouses/<slug:slug>/products/<slug:product_slug>/images/<slug:image_slug>/delete/', supervisor.SupervisorProductImageDeleteView.as_view(), name='product_image_delete'),
    path('warehouses/<slug:slug>/products/<slug:product_slug>/variants/create/', supervisor.SupervisorProductVariantCreateView.as_view(), name='product_variant_create'),
    path('warehouses/<slug:slug>/products/<slug:product_slug>/variants/<slug:variant_slug>/update/', supervisor.SupervisorProductVariantUpdateView.as_view(), name='product_variant_update'),
    path('warehouses/<slug:slug>/products/<slug:product_slug>/variants/<slug:variant_slug>/delete/', supervisor.SupervisorProductVariantDeleteView.as_view(), name='product_variant_delete'),
    path('warehouses/<slug:slug>/products/<slug:product_slug>/variants/<slug:variant_slug>/images/manage/', supervisor.SupervisorVariantImageManagementView.as_view(), name='variant_images_manage'),
    path('warehouses/<slug:slug>/products/<slug:product_slug>/variants/<slug:variant_slug>/images/<slug:image_slug>/delete/', supervisor.SupervisorVariantImageDeleteView.as_view(), name='variant_image_delete'),
    path('warehouses/<slug:slug>/products/create/step-1/', supervisor.SupervisorProductCreateStepOneView.as_view(), name='product_create_step1'),
    path('warehouses/<slug:slug>/products/create/step-2/', supervisor.SupervisorProductCreateStepTwoView.as_view(), name='product_create_step2'),
    path('warehouses/<slug:slug>/products/create/step-3/single-variant/', supervisor.SupervisorProductCreateSingleVariantStepView.as_view(), name='product_create_step3_single'),
    path('warehouses/<slug:slug>/rooms/create/', supervisor.SupervisorCreateRoomView.as_view(), name='create_room'),
    path('warehouses/<slug:slug>/rooms/<slug:room_slug>/buckets/create/', supervisor.SupervisorCreateBucketView.as_view(), name='create_bucket'),
]
