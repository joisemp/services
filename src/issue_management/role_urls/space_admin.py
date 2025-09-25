from django.urls import path
from ..views import space_admin

app_name = "space_admin"

urlpatterns = [
    path('', space_admin.IssueListView.as_view(), name='issue_list'),
    path('create/', space_admin.IssueCreateView.as_view(), name='issue_create'),
    path('<slug:issue_slug>/edit/', space_admin.IssueUpdateView.as_view(), name='issue_update'),
    path('<slug:issue_slug>/', space_admin.IssueDetailView.as_view(), name='issue_detail'),
    path('<slug:issue_slug>/assign/', space_admin.IssueAssignmentView.as_view(), name='issue_assign'),
    path('<slug:issue_slug>/resolve/', space_admin.IssueResolveView.as_view(), name='issue_resolve'),
    path('<slug:issue_slug>/reopen/', space_admin.IssueReopenView.as_view(), name='issue_reopen'),
    path('<slug:issue_slug>/delete/', space_admin.IssueDeleteView.as_view(), name='issue_delete'),
    
    # Work Task URLs
    path('<slug:issue_slug>/work-tasks/create/', space_admin.WorkTaskCreateView.as_view(), name='work_task_create'),
    path('work-tasks/<slug:work_task_slug>/edit/', space_admin.WorkTaskUpdateView.as_view(), name='work_task_update'),
    path('work-tasks/<slug:work_task_slug>/complete/', space_admin.WorkTaskCompleteView.as_view(), name='work_task_complete'),
    path('work-tasks/<slug:work_task_slug>/toggle-complete/', space_admin.WorkTaskToggleCompleteView.as_view(), name='work_task_toggle_complete'),
    path('work-tasks/<slug:work_task_slug>/delete/', space_admin.WorkTaskDeleteView.as_view(), name='work_task_delete'),
    
    # Comment URLs
    path('<slug:issue_slug>/comments/', space_admin.IssueCommentListView.as_view(), name='comment_list'),
    path('<slug:issue_slug>/comments/create/', space_admin.IssueCommentCreateView.as_view(), name='comment_create'),
    
    # Image URLs
    path('<slug:issue_slug>/images/<slug:image_slug>/delete/', space_admin.IssueImageDeleteView.as_view(), name='image_delete'),
    path('<slug:issue_slug>/images/upload/', space_admin.IssueImageUploadView.as_view(), name='image_upload'),
    
    # Voice URLs
    path('<slug:issue_slug>/voice/delete/', space_admin.IssueVoiceDeleteView.as_view(), name='voice_delete'),
    path('<slug:issue_slug>/voice/upload/', space_admin.IssueVoiceUploadView.as_view(), name='voice_upload'),
]
