from django.urls import path
from ..views import supervisor  # Uncomment when views are created

app_name = "supervisor"

urlpatterns = [
    path('', supervisor.SupervisorIssueListView.as_view(), name='issue_list'),
    path('issue/<slug:issue_slug>/', supervisor.IssueDetailView.as_view(), name='issue_detail'),
]
