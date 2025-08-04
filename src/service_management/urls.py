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
    
    # Spaces Management URLs
    path('spaces/', views.spaces_list, name='spaces_list'),
    path('spaces/create/', views.create_space, name='create_space'),
    path('spaces/<slug:slug>/', views.space_detail, name='space_detail'),
    path('spaces/<slug:slug>/edit/', views.edit_space, name='edit_space'),
    path('spaces/<slug:slug>/settings/', views.space_settings, name='space_settings'),
    path('spaces/<slug:slug>/admins/', views.manage_space_admins, name='manage_space_admins'),
    path('spaces/<slug:slug>/maintainers/', views.manage_space_maintainers, name='manage_space_maintainers'),
    
    # Space Admin Access Control
    path('no-spaces-assigned/', views.no_spaces_assigned, name='no_spaces_assigned'),
]

urlpatterns += [
    path('people/upgrade/<slug:profile_id>/',
         __import__('service_management.upgrade_views', fromlist=['upgrade_user']).upgrade_user,
         name='upgrade_user'),
    path('people/delete/<slug:profile_id>/',
         views.delete_person,
         name='delete_person'),
]