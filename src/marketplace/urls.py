from django.urls import path
from . import views

app_name = 'marketplace'

urlpatterns = [
    # Main marketplace page
    path('', views.marketplace, name='marketplace'),
    
    # Shopping List Management URLs
    path('shopping-lists/', views.shopping_list_list, name='shopping_list_list'),
    path('shopping-lists/create/', views.create_shopping_list, name='create_shopping_list'),
    path('shopping-lists/<slug:slug>/', views.shopping_list_detail, name='shopping_list_detail'),
    path('shopping-lists/<slug:slug>/add-item/', views.add_shopping_list_item, name='add_shopping_list_item'),
    path('shopping-lists/<slug:slug>/item/<slug:item_slug>/edit/', views.edit_shopping_list_item, name='edit_shopping_list_item'),
    path('shopping-lists/<slug:slug>/approve/', views.approve_shopping_list, name='approve_shopping_list'),
    path('shopping-lists/<slug:slug>/create-purchase/', views.create_purchase, name='create_purchase'),
    path('shopping-lists/<slug:slug>/create-multi-shop-purchase/', views.create_multi_shop_purchase, name='create_multi_shop_purchase'),
    
    # Purchase Management URLs
    path('purchases/<slug:slug>/', views.purchase_detail, name='purchase_detail'),
]