from django.urls import path
from ..views import central_admin  # Uncomment when views are created

app_name = "central_admin"

urlpatterns = [
    path('', central_admin.IssueListView.as_view(), name='issue_list'),
    path('create/', central_admin.IssueCreateView.as_view(), name='issue_create'),
    path('<slug:issue_slug>/', central_admin.IssueDetailView.as_view(), name='issue_detail'),
    path('<slug:issue_slug>/resolve/', central_admin.IssueResolveView.as_view(), name='issue_resolve'),
    path('<slug:issue_slug>/delete/', central_admin.IssueDeleteView.as_view(), name='issue_delete'),
    
    # Work Task URLs
    path('<slug:issue_slug>/work-tasks/create/', central_admin.WorkTaskCreateView.as_view(), name='work_task_create'),
    path('work-tasks/<slug:work_task_slug>/edit/', central_admin.WorkTaskUpdateView.as_view(), name='work_task_update'),
    path('work-tasks/<slug:work_task_slug>/complete/', central_admin.WorkTaskCompleteView.as_view(), name='work_task_complete'),
    path('work-tasks/<slug:work_task_slug>/toggle-complete/', central_admin.WorkTaskToggleCompleteView.as_view(), name='work_task_toggle_complete'),
    path('work-tasks/<slug:work_task_slug>/delete/', central_admin.WorkTaskDeleteView.as_view(), name='work_task_delete'),
    
    # Comment URLs
    path('<slug:issue_slug>/comments/', central_admin.IssueCommentListView.as_view(), name='comment_list'),
    path('<slug:issue_slug>/comments/create/', central_admin.IssueCommentCreateView.as_view(), name='comment_create'),
    
    # Image URLs
    path('<slug:issue_slug>/images/<slug:image_slug>/delete/', central_admin.IssueImageDeleteView.as_view(), name='image_delete'),
    path('<slug:issue_slug>/images/upload/', central_admin.IssueImageUploadView.as_view(), name='image_upload'),
    
    # Voice URLs
    path('<slug:issue_slug>/voice/delete/', central_admin.IssueVoiceDeleteView.as_view(), name='voice_delete'),
    path('<slug:issue_slug>/voice/upload/', central_admin.IssueVoiceUploadView.as_view(), name='voice_upload'),
]
