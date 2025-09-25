from django.urls import path
from django.contrib.auth import views as auth_views
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
    
    path('people/create/', 
         views.PeopleCreateView.as_view(), 
         name='people_create'),
    
    path('updates/', 
         views.UpdateListView.as_view(), 
         name='updates'),
    
    path('login/', 
         views.CustomLoginView.as_view(), 
         name='login'),
    
    path('logout/', 
         views.custom_logout_view, 
         name='logout'),
    
    path('spaces/', 
         views.SpaceListView.as_view(),
         name='space_list'),
    
    path('spaces/<slug:space_slug>/', 
         views.SpaceDetailView.as_view(), 
         name='space_detail'),
    
    path('spaces/<slug:space_slug>/edit/', 
         views.SpaceUpdateView.as_view(), 
         name='space_update'),
    
    path('spaces/create/', 
         views.SpaceCreateView.as_view(), 
         name='space_create'),
]