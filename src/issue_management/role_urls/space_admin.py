from django.urls import path
from .. views.space_admin import IssueListView, IssueCreateView

app_name = "space_admin"

urlpatterns = [
    path('', IssueListView.as_view(), name='issue_list'),
    path('create/', IssueCreateView.as_view(), name='issue_create'),
]
