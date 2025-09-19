from django.urls import path
from .. views.space_admin import IssueListView

app_name = "space_admin"

urlpatterns = [
    path('', IssueListView.as_view(), name='issue_list'),
]
