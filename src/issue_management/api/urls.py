"""Issue management API URLs mounted under /api/."""
from django.urls import path

from issue_management.api import views

app_name = 'api_issues'

urlpatterns = [
    # Issues
    path('issues/', views.IssueListCreateView.as_view(), name='issue-list'),
    path('issues/<slug:slug>/', views.IssueDetailView.as_view(), name='issue-detail'),
    path('issues/<slug:slug>/assign/', views.IssueAssignView.as_view(), name='issue-assign'),
    path('issues/<slug:slug>/select-reviewers/', views.IssueSelectReviewersView.as_view(), name='issue-select-reviewers'),
    path('issues/<slug:slug>/start-work/', views.IssueStartWorkView.as_view(), name='issue-start-work'),
    path('issues/<slug:slug>/resolve/', views.IssueResolveView.as_view(), name='issue-resolve'),
    path('issues/<slug:slug>/reopen/', views.IssueReopenView.as_view(), name='issue-reopen'),
    path('issues/<slug:slug>/change-workshop/', views.IssueChangeWorkshopView.as_view(), name='issue-change-workshop'),
    path('issues/<slug:slug>/images/', views.IssueImageUploadView.as_view(), name='issue-image-upload'),
    path('issues/<slug:slug>/images/<slug:image_slug>/', views.IssueImageDeleteView.as_view(), name='issue-image-delete'),
    path('issues/<slug:slug>/voice/', views.IssueVoiceUploadView.as_view(), name='issue-voice-upload'),
    path('issues/<slug:slug>/voice/delete/', views.IssueVoiceDeleteView.as_view(), name='issue-voice-delete'),
    path('issues/<slug:slug>/comments/', views.IssueCommentListCreateView.as_view(), name='issue-comments'),
    path('issues/<slug:slug>/review-comments/', views.IssueReviewCommentCreateView.as_view(), name='issue-review-comments'),
    path('issues/<slug:slug>/work-tasks/', views.WorkTaskCreateView.as_view(), name='issue-work-task-create'),
    path('issues/<slug:slug>/site-visits/', views.SiteVisitCreateView.as_view(), name='issue-site-visit-create'),
    path('issues/<slug:slug>/purchase-requests/', views.PurchaseRequestCreateView.as_view(), name='issue-purchase-create'),
    # Work tasks
    path('work-tasks/', views.WorkTaskListView.as_view(), name='work-task-list'),
    path('work-tasks/<slug:slug>/', views.WorkTaskDetailView.as_view(), name='work-task-detail'),
    path('work-tasks/<slug:slug>/complete/', views.WorkTaskCompleteView.as_view(), name='work-task-complete'),
    path('work-tasks/<slug:slug>/toggle-complete/', views.WorkTaskToggleCompleteView.as_view(), name='work-task-toggle'),
    path('work-tasks/<slug:slug>/resolution-images/', views.WorkTaskResolutionImageUploadView.as_view(), name='work-task-resolution-upload'),
    path('work-tasks/<slug:slug>/resolution-images/<slug:image_slug>/', views.WorkTaskResolutionImageDeleteView.as_view(), name='work-task-resolution-delete'),
    # Site visits
    path('site-visits/', views.SiteVisitListView.as_view(), name='site-visit-list'),
    path('site-visits/<slug:slug>/', views.SiteVisitDetailView.as_view(), name='site-visit-detail'),
    path('site-visits/<slug:slug>/start/', views.SiteVisitStartView.as_view(), name='site-visit-start'),
    path('site-visits/<slug:slug>/complete/', views.SiteVisitCompleteView.as_view(), name='site-visit-complete'),
    path('site-visits/<slug:slug>/cancel/', views.SiteVisitCancelView.as_view(), name='site-visit-cancel'),
    path('site-visits/<slug:slug>/images/', views.SiteVisitImageUploadView.as_view(), name='site-visit-image-upload'),
    # Purchases
    path('purchase-requests/', views.PurchaseRequestListView.as_view(), name='purchase-list'),
    path('purchase-requests/<slug:slug>/', views.PurchaseRequestDetailView.as_view(), name='purchase-detail'),
    path('purchase-requests/<slug:slug>/approve/', views.PurchaseRequestApproveView.as_view(), name='purchase-approve'),
    path('purchase-requests/<slug:slug>/reject/', views.PurchaseRequestRejectView.as_view(), name='purchase-reject'),
    path('shopping-lists/', views.ShoppingListListView.as_view(), name='shopping-list'),
    path('shopping-lists/generate/', views.ShoppingListGenerateView.as_view(), name='shopping-generate'),
    path('shopping-lists/<slug:slug>/', views.ShoppingListDetailView.as_view(), name='shopping-detail'),
    # Reports
    path('reports/issues/', views.IssueListReportAPIView.as_view(), name='report-issues'),
    path('reports/performance/', views.PerformanceReportAPIView.as_view(), name='report-performance'),
]
