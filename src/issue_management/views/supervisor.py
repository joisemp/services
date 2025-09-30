from django.views.generic import ListView
from .. models import Issue


class SupervisorIssueListView(ListView):
    model = Issue
    template_name = "supervisor/issue_management/issue_list.html"
    context_object_name = "issues"

    def get_queryset(self):
        return Issue.objects.filter(assigned_to=self.request.user).order_by('-created_at')