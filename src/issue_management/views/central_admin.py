from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from ..models import Issue


class IssueListView(ListView):
    template_name = "central_admin/issue_management/issue_list.html"
    context_object_name = "issues"
    model = Issue

    def get_queryset(self):
        return Issue.objects.all()
    
class IssueCreateView(CreateView):
    template_name = "central_admin/issue_management/issue_create.html"
    model = Issue
    fields = ['title', 'description', 'status', 'priority', 'assigned_to']
    