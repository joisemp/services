from django.urls import path
from ..views.space_admin import IssueListView, IssueCreateView, IssueDetailView, IssueImageDeleteView, IssueImageUploadView, IssueVoiceDeleteView

app_name = "space_admin"

urlpatterns = [
    path('', IssueListView.as_view(), name='issue_list'),
    path('create/', IssueCreateView.as_view(), name='issue_create'),
    path('<slug:issue_slug>/', IssueDetailView.as_view(), name='issue_detail'),
    
    # Image URLs
    path('<slug:issue_slug>/images/<slug:image_slug>/delete/', IssueImageDeleteView.as_view(), name='image_delete'),
    path('<slug:issue_slug>/images/upload/', IssueImageUploadView.as_view(), name='image_upload'),
    
    # Voice URLs
    path('<slug:issue_slug>/voice/delete/', IssueVoiceDeleteView.as_view(), name='voice_delete'),
    
    # Voice URLs
    path('<slug:issue_slug>/voice/delete/', IssueVoiceDeleteView.as_view(), name='voice_delete'),
]
