from django.urls import path
from ..views import central_admin

app_name = "central_admin"

urlpatterns = [
    path('', central_admin.IssueListView.as_view(), name='issue_list'),
    path('create/', central_admin.IssueCreateView.as_view(), name='issue_create'),
    path('site-visits/', central_admin.SiteVisitListView.as_view(), name='site_visit_list'),
    path('performance-report/', central_admin.PerformanceReportView.as_view(), name='performance_report'),
    path('<slug:issue_slug>/edit/', central_admin.IssueUpdateView.as_view(), name='issue_update'),
    path('<slug:issue_slug>/', central_admin.IssueDetailView.as_view(), name='issue_detail'),
    path('<slug:issue_slug>/assign/', central_admin.IssueAssignmentView.as_view(), name='issue_assign'),
    path('<slug:issue_slug>/select-reviewers/', central_admin.IssueReviewerSelectionView.as_view(), name='issue_select_reviewers'),
    path('<slug:issue_slug>/resolve/', central_admin.IssueResolveView.as_view(), name='issue_resolve'),
    path('<slug:issue_slug>/reopen/', central_admin.IssueReopenView.as_view(), name='issue_reopen'),
    path('<slug:issue_slug>/start-work/', central_admin.IssueStartWorkView.as_view(), name='issue_start_work'),
    path('<slug:issue_slug>/delete/', central_admin.IssueDeleteView.as_view(), name='issue_delete'),
    
    # Work Task URLs
    path('<slug:issue_slug>/work-tasks/create/', central_admin.WorkTaskCreateView.as_view(), name='work_task_create'),
    path('work-tasks/<slug:work_task_slug>/edit/', central_admin.WorkTaskUpdateView.as_view(), name='work_task_update'),
    path('work-tasks/<slug:work_task_slug>/complete/', central_admin.WorkTaskCompleteView.as_view(), name='work_task_complete'),
    path('work-tasks/<slug:work_task_slug>/toggle-complete/', central_admin.WorkTaskToggleCompleteView.as_view(), name='work_task_toggle_complete'),
    path('work-tasks/<slug:work_task_slug>/delete/', central_admin.WorkTaskDeleteView.as_view(), name='work_task_delete'),
    
    # Image URLs
    path('<slug:issue_slug>/images/<slug:image_slug>/delete/', central_admin.IssueImageDeleteView.as_view(), name='image_delete'),
    path('<slug:issue_slug>/images/upload/', central_admin.IssueImageUploadView.as_view(), name='image_upload'),
    
    # Work Task Resolution Image URLs
    path('work-tasks/<slug:work_task_slug>/resolution-images/<slug:image_slug>/delete/', central_admin.WorkTaskResolutionImageDeleteView.as_view(), name='resolution_image_delete'),
    
    # Voice URLs
    path('<slug:issue_slug>/voice/delete/', central_admin.IssueVoiceDeleteView.as_view(), name='voice_delete'),
    path('<slug:issue_slug>/voice/upload/', central_admin.IssueVoiceUploadView.as_view(), name='voice_upload'),
    
    # Site Visit URLs
    path('<slug:issue_slug>/site-visits/create/', central_admin.SiteVisitCreateView.as_view(), name='site_visit_create'),
    path('site-visits/<slug:site_visit_slug>/', central_admin.SiteVisitDetailView.as_view(), name='site_visit_detail'),
    path('site-visits/<slug:site_visit_slug>/edit/', central_admin.SiteVisitUpdateView.as_view(), name='site_visit_update'),
    path('site-visits/<slug:site_visit_slug>/delete/', central_admin.SiteVisitDeleteView.as_view(), name='site_visit_delete'),
]
