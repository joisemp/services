from django.urls import path
from . import views

app_name = 'issue_management'

urlpatterns = [
    # Issue views
    path('issues/', views.issue_list, name='issue_list'),
    path('issues/<slug:slug>/', views.issue_detail, name='issue_detail'),
    path('issues/<slug:slug>/update/', views.update_issue, name='update_issue'),
    path('issues/<slug:slug>/escalate/', views.escalate_issue, name='escalate_issue'),
    path('issues/<slug:slug>/reassign-escalated/', views.reassign_escalated_issue, name='reassign_escalated_issue'),
    path('issues/<slug:slug>/change-status/<str:new_status>/', views.change_status, name='change_status'),
    path('issues/<slug:slug>/change-status-comment/<str:new_status>/', views.change_status_with_comment, name='change_status_with_comment'),
    path('report-issue/', views.report_issue, name='report_issue'),
    path('report-issue/voice-record/', views.voice_record, name='voice_record'),
    path('assign-issue/<slug:issue_slug>/', views.assign_issue, name='assign_issue'),
    
    # Category management
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.create_category, name='create_category'),
    path('categories/<slug:slug>/update/', views.update_category, name='update_category'),
    path('categories/<slug:slug>/delete/', views.delete_category, name='delete_category'),
]