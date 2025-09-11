from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from ..models import Issue
from ..forms import IssueForm


class IssueListView(ListView):
    template_name = "central_admin/issue_management/issue_list.html"
    context_object_name = "issues"
    model = Issue
    
    def get_queryset(self):
        return Issue.objects.all()
    
class IssueCreateView(CreateView):
    template_name = "central_admin/issue_management/issue_create.html"
    form_class = IssueForm
    success_url = reverse_lazy('issue_management:central_admin:issue_list')
    