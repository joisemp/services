from django.urls import path
from ..views import space_admin

app_name = "space_admin"

urlpatterns = [
    path('', space_admin.TicketListView.as_view(), name='ticket_list'),
    path('create/', space_admin.TicketCreateView.as_view(), name='ticket_create'),
    path('site-visits/', space_admin.SiteVisitListView.as_view(), name='site_visit_list'),
    path('<slug:ticket_slug>/edit/', space_admin.TicketUpdateView.as_view(), name='ticket_update'),
    path('<slug:ticket_slug>/', space_admin.TicketDetailView.as_view(), name='ticket_detail'),
    path('<slug:ticket_slug>/assign/', space_admin.TicketAssignmentView.as_view(), name='ticket_assign'),
    path('<slug:ticket_slug>/select-reviewers/', space_admin.TicketReviewerSelectionView.as_view(), name='ticket_select_reviewers'),
    path('<slug:ticket_slug>/resolve/', space_admin.TicketResolveView.as_view(), name='ticket_resolve'),
    path('<slug:ticket_slug>/reopen/', space_admin.TicketReopenView.as_view(), name='ticket_reopen'),
    path('<slug:ticket_slug>/start-work/', space_admin.TicketStartWorkView.as_view(), name='ticket_start_work'),
    path('<slug:ticket_slug>/delete/', space_admin.TicketDeleteView.as_view(), name='ticket_delete'),
    
    # Work Task URLs
    path('<slug:ticket_slug>/work-tasks/create/', space_admin.WorkTaskCreateView.as_view(), name='work_task_create'),
    path('work-tasks/<slug:work_task_slug>/edit/', space_admin.WorkTaskUpdateView.as_view(), name='work_task_update'),
    path('work-tasks/<slug:work_task_slug>/complete/', space_admin.WorkTaskCompleteView.as_view(), name='work_task_complete'),
    path('work-tasks/<slug:work_task_slug>/toggle-complete/', space_admin.WorkTaskToggleCompleteView.as_view(), name='work_task_toggle_complete'),
    path('work-tasks/<slug:work_task_slug>/delete/', space_admin.WorkTaskDeleteView.as_view(), name='work_task_delete'),
    
    # Image URLs
    path('<slug:ticket_slug>/images/<slug:image_slug>/delete/', space_admin.TicketImageDeleteView.as_view(), name='image_delete'),
    path('<slug:ticket_slug>/images/upload/', space_admin.TicketImageUploadView.as_view(), name='image_upload'),
    
    # Work Task Resolution Image URLs
    path('work-tasks/<slug:work_task_slug>/resolution-images/<slug:image_slug>/delete/', space_admin.WorkTaskResolutionImageDeleteView.as_view(), name='resolution_image_delete'),
    
    # Voice URLs
    path('<slug:ticket_slug>/voice/delete/', space_admin.TicketVoiceDeleteView.as_view(), name='voice_delete'),
    path('<slug:ticket_slug>/voice/upload/', space_admin.TicketVoiceUploadView.as_view(), name='voice_upload'),
    
    # Site Visit URLs
    path('<slug:ticket_slug>/site-visits/create/', space_admin.SiteVisitCreateView.as_view(), name='site_visit_create'),
    path('site-visits/<slug:site_visit_slug>/', space_admin.SiteVisitDetailView.as_view(), name='site_visit_detail'),
    path('site-visits/<slug:site_visit_slug>/edit/', space_admin.SiteVisitUpdateView.as_view(), name='site_visit_update'),
    path('site-visits/<slug:site_visit_slug>/delete/', space_admin.SiteVisitDeleteView.as_view(), name='site_visit_delete'),
    
    # Purchase Request URLs
    path('<slug:ticket_slug>/purchase-requests/create/', space_admin.PurchaseRequestCreateView.as_view(), name='purchase_request_create'),
    path('purchase-requests/<slug:purchase_request_slug>/delete/', space_admin.PurchaseRequestDeleteView.as_view(), name='purchase_request_delete'),
]
