from django.urls import path
from .. views.space_admin import IssueListView, IssueCreateView, IssueImageDeleteView

app_name = "space_admin"

urlpatterns = [
    path('', IssueListView.as_view(), name='issue_list'),
    path('create/', IssueCreateView.as_view(), name='issue_create'),
    
    # Image URLs
    path('<slug:issue_slug>/images/<slug:image_slug>/delete/', IssueImageDeleteView.as_view(), name='image_delete'),
]
