from . import views
from django.urls import path

app_name = 'service_management'

urlpatterns = [
    path('people/', views.people_list, name='people_list'),
    path('people/add/', views.add_person, name='add_person'),
    path('people/edit/<slug:profile_id>/', views.edit_person, name='edit_person'),
]