from django.urls import path
from ..views import central_admin  # Uncomment when views are created

app_name = "central_admin"

urlpatterns = [
    path('', central_admin.IssueListView.as_view(), name='issue_list'),
    path('create/', central_admin.IssueCreateView.as_view(), name='issue_create'),
    path('<slug:issue_slug>/', central_admin.IssueDetailView.as_view(), name='issue_detail'),
]
