from django.urls import path
from ..views import reviewer

app_name = "reviewer"

urlpatterns = [
    # Reviewer-specific URLs for issue review and approval
    path('', reviewer.ReviewerIssueListView.as_view(), name='issue_list'),
    path('issues/<slug:issue_slug>/', reviewer.IssueDetailView.as_view(), name='issue_detail'),
]
