from django.urls import path
from ..views import central_admin  # Uncomment when views are created

app_name = "central_admin"

urlpatterns = [
    path('', central_admin.IssueListView.as_view(), name='issue_list'),
    path('create/', central_admin.IssueCreateView.as_view(), name='issue_create'),
    path('<slug:issue_slug>/', central_admin.IssueDetailView.as_view(), name='issue_detail'),
    
    # Work Task URLs
    path('<slug:issue_slug>/work-tasks/create/', central_admin.WorkTaskCreateView.as_view(), name='work_task_create'),
    path('work-tasks/<slug:work_task_slug>/edit/', central_admin.WorkTaskUpdateView.as_view(), name='work_task_update'),
    path('work-tasks/<slug:work_task_slug>/complete/', central_admin.WorkTaskCompleteView.as_view(), name='work_task_complete'),
    path('work-tasks/<slug:work_task_slug>/toggle-complete/', central_admin.WorkTaskToggleCompleteView.as_view(), name='work_task_toggle_complete'),
    path('work-tasks/<slug:work_task_slug>/delete/', central_admin.WorkTaskDeleteView.as_view(), name='work_task_delete'),
]
