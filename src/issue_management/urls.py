from django.urls import path
from . import views

app_name = 'issue_management'

urlpatterns = [
    # Issue views
    path('issues/', views.issue_list, name='issue_list'),
    path('issues/<slug:slug>/', views.issue_detail, name='issue_detail'),
    path('issues/<slug:slug>/update/', views.update_issue, name='update_issue'),
    path('report-issue/', views.report_issue, name='report_issue'),
    path('report-issue/voice-record/', views.voice_record, name='voice_record'),
    path('assign-issue/<slug:issue_slug>/', views.assign_issue, name='assign_issue'),
    
    # Category management
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.create_category, name='create_category'),
    path('categories/<slug:slug>/update/', views.update_category, name='update_category'),
    path('categories/<slug:slug>/delete/', views.delete_category, name='delete_category'),
]