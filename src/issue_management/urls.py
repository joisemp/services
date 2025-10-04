from django.urls import path, include
from .views import common

app_name = "issue_management"

urlpatterns = [
    # Common URLs - accessible to all authenticated users
    path('issues/<slug:issue_slug>/comments/', common.IssueCommentListView.as_view(), name='comment_list'),
    path('issues/<slug:issue_slug>/comments/create/', common.IssueCommentCreateView.as_view(), name='comment_create'),
    
    # Role-based URL patterns for issue management
    path('central-admin/', include('issue_management.role_urls.central_admin')),
    path('maintainer/', include('issue_management.role_urls.maintainer')),
    path('reviewer/', include('issue_management.role_urls.reviewer')),
    path('space-admin/', include('issue_management.role_urls.space_admin')),
    path('supervisor/', include('issue_management.role_urls.supervisor')),
]
