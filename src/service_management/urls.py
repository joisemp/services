from . import views
from django.urls import path

app_name = 'service_management'

urlpatterns = [
    path('people/', views.people_list, name='people_list'),
    path('people/add/', views.add_person, name='add_person'),
    path('people/edit/<slug:profile_id>/', views.edit_person, name='edit_person'),
    path('work-categories/', views.work_category_list, name='work_category_list'),
    path('work-categories/create/', views.create_work_category, name='create_work_category'),
]

urlpatterns += [
    path('people/upgrade/<slug:profile_id>/',
         __import__('service_management.upgrade_views', fromlist=['upgrade_user']).upgrade_user,
         name='upgrade_user'),
    path('people/delete/<slug:profile_id>/',
         views.delete_person,
         name='delete_person'),
]