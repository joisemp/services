from django.views.generic import ListView, DetailView
from .. forms import IssueCommentForm
from .. models import Issue


class SupervisorIssueListView(ListView):
    model = Issue
    template_name = "supervisor/issue_management/issue_list.html"
    context_object_name = "issues"

    def get_queryset(self):
        return Issue.objects.filter(assigned_to=self.request.user).order_by('-created_at')
    
    
class IssueDetailView(DetailView):
    template_name = "supervisor/issue_management/issue_detail.html"
    context_object_name = "issue"
    model = Issue
    slug_field = 'slug'
    slug_url_kwarg = 'issue_slug'
    
    def get_queryset(self):
        return Issue.objects.prefetch_related('images', 'comments', 'work_tasks__assigned_to').select_related('org', 'space')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add work tasks to context
        work_tasks = self.object.work_tasks.all().order_by('-created_at')
        context['work_tasks'] = work_tasks
        # Check if there are any incomplete work tasks
        context['has_incomplete_tasks'] = work_tasks.filter(completed=False).exists()
        # Add comment form to context
        context['comment_form'] = IssueCommentForm()
        return context