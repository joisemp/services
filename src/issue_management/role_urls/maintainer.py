from django.urls import path
from ..views import maintainer

app_name = "maintainer"

urlpatterns = [
    # Work Task Management URLs - Maintainer can only view tasks and toggle completion
    path('tasks/', maintainer.WorkTaskListView.as_view(), name='work_task_list'),
    path('work-tasks/<slug:work_task_slug>/', maintainer.WorkTaskDetailView.as_view(), name='work_task_detail'),
    path('work-tasks/<slug:work_task_slug>/toggle-complete/', maintainer.WorkTaskToggleCompleteView.as_view(), name='work_task_toggle_complete'),
]
