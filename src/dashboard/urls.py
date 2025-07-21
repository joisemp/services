from django.urls import path
from .views import dashboard_view, switch_space

app_name = 'dashboard'

urlpatterns = [
    path('', dashboard_view, name='dashboard'),
    path('switch-space/', switch_space, name='switch_space'),
]
