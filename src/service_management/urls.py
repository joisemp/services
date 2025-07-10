from . import views
from django.urls import path

app_name = 'service_management'

urlpatterns = [
    path('people/', views.people_list, name='people_list'),
    path('people/add/', views.add_person, name='add_person'),
    path('people/edit/<slug:profile_id>/', views.edit_person, name='edit_person'),
    path('work-categories/', views.work_category_list, name='work_category_list'),
    path('work-categories/create/', views.create_work_category, name='create_work_category'),
    path('work-categories/<slug:category_slug>/edit/', views.update_work_category, name='update_work_category'),
    path('work-categories/<slug:category_slug>/delete/', views.delete_work_category, name='delete_work_category'),
    
    # Marketplace URLs (Purchase Management)
    path('marketplace/', views.marketplace, name='marketplace'),
    path('marketplace/shopping-lists/', views.shopping_list_list, name='shopping_list_list'),
    path('marketplace/shopping-lists/create/', views.create_shopping_list, name='create_shopping_list'),
    path('marketplace/shopping-lists/<slug:slug>/', views.shopping_list_detail, name='shopping_list_detail'),
    path('marketplace/shopping-lists/<slug:slug>/add-item/', views.add_shopping_list_item, name='add_shopping_list_item'),
    path('marketplace/shopping-lists/<slug:slug>/item/<slug:item_slug>/edit/', views.edit_shopping_list_item, name='edit_shopping_list_item'),
    path('marketplace/shopping-lists/<slug:slug>/approve/', views.approve_shopping_list, name='approve_shopping_list'),
    path('marketplace/shopping-lists/<slug:slug>/create-purchase/', views.create_purchase, name='create_purchase'),
    path('marketplace/shopping-lists/<slug:slug>/create-multi-shop-purchase/', views.create_multi_shop_purchase, name='create_multi_shop_purchase'),
    path('marketplace/purchases/<slug:slug>/', views.purchase_detail, name='purchase_detail'),
]

urlpatterns += [
    path('people/upgrade/<slug:profile_id>/',
         __import__('service_management.upgrade_views', fromlist=['upgrade_user']).upgrade_user,
         name='upgrade_user'),
    path('people/delete/<slug:profile_id>/',
         views.delete_person,
         name='delete_person'),
]