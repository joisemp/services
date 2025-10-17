from django.urls import path
from ..views import supervisor

app_name = "supervisor"

urlpatterns = [
    path('', supervisor.SupervisorIssueListView.as_view(), name='issue_list'),
    path('tasks/', supervisor.WorkTaskListView.as_view(), name='work_task_list'),
    path('issue/<slug:issue_slug>/', supervisor.IssueDetailView.as_view(), name='issue_detail'),
    path('issue/<slug:issue_slug>/resolve/', supervisor.IssueResolveView.as_view(), name='issue_resolve'),
    path('issue/<slug:issue_slug>/start-work/', supervisor.IssueStartWorkView.as_view(), name='issue_start_work'),
    
    # Work Task URLs
    path('<slug:issue_slug>/work-tasks/create/', supervisor.WorkTaskCreateView.as_view(), name='work_task_create'),
    path('work-tasks/<slug:work_task_slug>/', supervisor.WorkTaskDetailView.as_view(), name='work_task_detail'),
    path('work-tasks/<slug:work_task_slug>/edit/', supervisor.WorkTaskUpdateView.as_view(), name='work_task_update'),
    path('work-tasks/<slug:work_task_slug>/complete/', supervisor.WorkTaskCompleteView.as_view(), name='work_task_complete'),
    path('work-tasks/<slug:work_task_slug>/toggle-complete/', supervisor.WorkTaskToggleCompleteView.as_view(), name='work_task_toggle_complete'),
    path('work-tasks/<slug:work_task_slug>/delete/', supervisor.WorkTaskDeleteView.as_view(), name='work_task_delete'),
    
    # Work Task Resolution Image URLs
    path('work-tasks/<slug:work_task_slug>/resolution-images/<slug:image_slug>/delete/', supervisor.WorkTaskResolutionImageDeleteView.as_view(), name='resolution_image_delete'),
    
    # Site Visit URLs
    path('issue/<slug:issue_slug>/site-visits/create/', supervisor.SiteVisitCreateView.as_view(), name='site_visit_create'),
    path('site-visits/<slug:site_visit_slug>/edit/', supervisor.SiteVisitUpdateView.as_view(), name='site_visit_update'),
    path('site-visits/<slug:site_visit_slug>/delete/', supervisor.SiteVisitDeleteView.as_view(), name='site_visit_delete'),
]
