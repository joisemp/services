from . import views
from django.urls import path

app_name = 'service_management'

urlpatterns = [
    path('people/', views.people_list, name='people_list'),
]