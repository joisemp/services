from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    # Password Reset URLs with custom views
    path('password-reset/', 
         views.CustomPasswordResetView.as_view(), 
         name='password_reset'),
    
    path('password-reset/done/', 
         views.CustomPasswordResetDoneView.as_view(), 
         name='password_reset_done'),
    
    path('password-reset-confirm/<uidb64>/<token>/', 
         views.CustomPasswordResetConfirmView.as_view(), 
         name='password_reset_confirm'),
    
    path('password-reset-complete/', 
         views.CustomPasswordResetCompleteView.as_view(), 
         name='password_reset_complete'),
    
    path('people/', 
         views.PeopleListView.as_view(), 
         name='people_list'),
]