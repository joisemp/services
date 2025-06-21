from django.urls import path
from . import views

app_name = 'issue_management'

urlpatterns = [
    path('issues/', views.issue_list, name='issue_list'),
    path('report-issue/', views.report_issue, name='report_issue'),
    path('report-issue/voice-record/', views.voice_record, name='voice_record'),
]