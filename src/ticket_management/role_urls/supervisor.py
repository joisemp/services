from django.urls import path
from ..views import supervisor

app_name = "supervisor"

urlpatterns = [
    path('', supervisor.SupervisorTicketListView.as_view(), name='ticket_list'),
    path('create/', supervisor.TicketCreateView.as_view(), name='ticket_create'),
    path('tasks/', supervisor.WorkTaskListView.as_view(), name='work_task_list'),
    path('site-visits/', supervisor.SiteVisitListView.as_view(), name='site_visit_list'),
    path('site-visits/<slug:site_visit_slug>/', supervisor.SiteVisitDetailView.as_view(), name='site_visit_detail'),
    path('ticket/<slug:ticket_slug>/', supervisor.TicketDetailView.as_view(), name='ticket_detail'),
    path('ticket/<slug:ticket_slug>/resolve/', supervisor.TicketResolveView.as_view(), name='ticket_resolve'),
    path('ticket/<slug:ticket_slug>/start-work/', supervisor.TicketStartWorkView.as_view(), name='ticket_start_work'),
    
    # Work Task URLs
    path('<slug:ticket_slug>/work-tasks/create/', supervisor.WorkTaskCreateView.as_view(), name='work_task_create'),
    path('work-tasks/<slug:work_task_slug>/', supervisor.WorkTaskDetailView.as_view(), name='work_task_detail'),
    path('work-tasks/<slug:work_task_slug>/edit/', supervisor.WorkTaskUpdateView.as_view(), name='work_task_update'),
    path('work-tasks/<slug:work_task_slug>/complete/', supervisor.WorkTaskCompleteView.as_view(), name='work_task_complete'),
    path('work-tasks/<slug:work_task_slug>/toggle-complete/', supervisor.WorkTaskToggleCompleteView.as_view(), name='work_task_toggle_complete'),
    path('work-tasks/<slug:work_task_slug>/delete/', supervisor.WorkTaskDeleteView.as_view(), name='work_task_delete'),
    
    # Work Task Resolution Image URLs
    path('work-tasks/<slug:work_task_slug>/resolution-images/<slug:image_slug>/delete/', supervisor.WorkTaskResolutionImageDeleteView.as_view(), name='resolution_image_delete'),
    
    # Site Visit URLs
    path('ticket/<slug:ticket_slug>/site-visits/create/', supervisor.SiteVisitCreateView.as_view(), name='site_visit_create'),
    path('site-visits/<slug:site_visit_slug>/edit/', supervisor.SiteVisitUpdateView.as_view(), name='site_visit_update'),
    path('site-visits/<slug:site_visit_slug>/delete/', supervisor.SiteVisitDeleteView.as_view(), name='site_visit_delete'),
    path('site-visits/<slug:site_visit_slug>/start/', supervisor.SiteVisitStartView.as_view(), name='site_visit_start'),
    path('site-visits/<slug:site_visit_slug>/complete/', supervisor.SiteVisitCompleteView.as_view(), name='site_visit_complete'),
    path('site-visits/<slug:site_visit_slug>/cancel/', supervisor.SiteVisitCancelView.as_view(), name='site_visit_cancel'),
]
