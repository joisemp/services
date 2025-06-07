from django.urls import path
from . import views

app_name = 'reporthub'

urlpatterns = [
    path('', views.issue_list, name='issue_list'),
    path('report/', views.report_issue, name='report_issue'),
    path('voice-record/', views.voice_record, name='voice_record'),
]