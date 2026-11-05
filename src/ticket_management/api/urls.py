"""Ticket management API URLs mounted under /api/."""
from django.urls import path

from ticket_management.api import views

app_name = 'api_tickets'

urlpatterns = [
    # Tickets
    path('tickets/', views.TicketListCreateView.as_view(), name='ticket-list'),
    path('tickets/<slug:slug>/', views.TicketDetailView.as_view(), name='ticket-detail'),
    path('tickets/<slug:slug>/assign/', views.TicketAssignView.as_view(), name='ticket-assign'),
    path('tickets/<slug:slug>/select-reviewers/', views.TicketSelectReviewersView.as_view(), name='ticket-select-reviewers'),
    path('tickets/<slug:slug>/start-work/', views.TicketStartWorkView.as_view(), name='ticket-start-work'),
    path('tickets/<slug:slug>/resolve/', views.TicketResolveView.as_view(), name='ticket-resolve'),
    path('tickets/<slug:slug>/reopen/', views.TicketReopenView.as_view(), name='ticket-reopen'),
    path('tickets/<slug:slug>/change-workshop/', views.TicketChangeWorkshopView.as_view(), name='ticket-change-workshop'),
    path('tickets/<slug:slug>/images/', views.TicketImageUploadView.as_view(), name='ticket-image-upload'),
    path('tickets/<slug:slug>/images/<slug:image_slug>/', views.TicketImageDeleteView.as_view(), name='ticket-image-delete'),
    path('tickets/<slug:slug>/voice/', views.TicketVoiceUploadView.as_view(), name='ticket-voice-upload'),
    path('tickets/<slug:slug>/voice/delete/', views.TicketVoiceDeleteView.as_view(), name='ticket-voice-delete'),
    path('tickets/<slug:slug>/comments/', views.TicketCommentListCreateView.as_view(), name='ticket-comments'),
    path('tickets/<slug:slug>/review-comments/', views.TicketReviewCommentCreateView.as_view(), name='ticket-review-comments'),
    path('tickets/<slug:slug>/work-tasks/', views.WorkTaskCreateView.as_view(), name='ticket-work-task-create'),
    path('tickets/<slug:slug>/site-visits/', views.SiteVisitCreateView.as_view(), name='ticket-site-visit-create'),
    path('tickets/<slug:slug>/purchase-requests/', views.PurchaseRequestCreateView.as_view(), name='ticket-purchase-create'),
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
    path('reports/tickets/', views.TicketListReportAPIView.as_view(), name='report-tickets'),
    path('reports/performance/', views.PerformanceReportAPIView.as_view(), name='report-performance'),
]
