from django.urls import path
from ..views import maintainer

app_name = "maintainer"

urlpatterns = [
    # Work Task Management URLs - Maintainer can only view tasks and toggle completion
    path('tasks/', maintainer.WorkTaskListView.as_view(), name='work_task_list'),
    path('work-tasks/<slug:work_task_slug>/', maintainer.WorkTaskDetailView.as_view(), name='work_task_detail'),
    path('work-tasks/<slug:work_task_slug>/toggle-complete/', maintainer.WorkTaskToggleCompleteView.as_view(), name='work_task_toggle_complete'),
    
    # Site Visit URLs - Maintainer can view and manage site visits assigned to them
    path('site-visits/', maintainer.SiteVisitListView.as_view(), name='site_visit_list'),
    path('site-visits/<slug:site_visit_slug>/', maintainer.SiteVisitDetailView.as_view(), name='site_visit_detail'),
    path('site-visits/<slug:site_visit_slug>/start/', maintainer.SiteVisitStartView.as_view(), name='site_visit_start'),
    path('site-visits/<slug:site_visit_slug>/complete/', maintainer.SiteVisitCompleteView.as_view(), name='site_visit_complete'),
    path('site-visits/<slug:site_visit_slug>/cancel/', maintainer.SiteVisitCancelView.as_view(), name='site_visit_cancel'),
]
