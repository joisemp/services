from django.urls import path

from ..views import supervisor

app_name = 'supervisor'

urlpatterns = [
    path('', supervisor.InventoryDashboardView.as_view(), name='inventory_dashboard'),
    path('warehouses/<slug:slug>/', supervisor.InventoryWarehouseDetailView.as_view(), name='warehouse_detail'),
    path('warehouses/<slug:slug>/products/', supervisor.InventoryWarehouseProductListView.as_view(), name='warehouse_products'),
    path('warehouses/<slug:slug>/rooms/create/', supervisor.SupervisorCreateRoomView.as_view(), name='create_room'),
    path('warehouses/<slug:slug>/rooms/<slug:room_slug>/buckets/create/', supervisor.SupervisorCreateBucketView.as_view(), name='create_bucket'),
]
