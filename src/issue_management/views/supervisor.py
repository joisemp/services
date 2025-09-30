from django.shortcuts import get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.urls import reverse_lazy
from .. forms import IssueCommentForm, WorkTaskForm, WorkTaskUpdateForm, WorkTaskCompleteForm
from django.contrib import messages
from .. models import Issue, WorkTask
from django.shortcuts import redirect



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
    

class IssueResolveView(View):
    """Mark an issue as resolved with resolution notes"""
    
    def post(self, request, issue_slug):
        # Get the issue
        issue = get_object_or_404(Issue, slug=issue_slug)
        
        # Check if issue is already resolved, closed, or cancelled
        if issue.status in ['resolved', 'closed', 'cancelled']:
            messages.error(request, f'This issue is already {issue.get_status_display().lower()} and cannot be resolved again.')
            return redirect('issue_management:supervisor:issue_detail', issue_slug=issue.slug)
        
        # Check if there are any incomplete work tasks
        incomplete_tasks = issue.work_tasks.filter(completed=False)
        if incomplete_tasks.exists():
            incomplete_count = incomplete_tasks.count()
            task_word = 'task' if incomplete_count == 1 else 'tasks'
            messages.error(request, f'Cannot resolve issue while {incomplete_count} work {task_word} remain incomplete. Please complete all work tasks before marking the issue as resolved.')
            return redirect('issue_management:supervisor:issue_detail', issue_slug=issue.slug)

        # Get resolution notes from the form
        resolution_notes = request.POST.get('resolution_notes', '').strip()
        
        if not resolution_notes:
            messages.error(request, 'Resolution notes are required to mark an issue as resolved.')
            return redirect('issue_management:supervisor:issue_detail', issue_slug=issue.slug)
        
        try:
            # Update the issue status and resolution notes
            issue.status = 'resolved'
            issue.resolution_notes = resolution_notes
            issue.save()
            
            messages.success(request, f'Issue "{issue.title}" has been successfully marked as resolved.')
            
        except Exception as e:
            messages.error(request, f'Failed to resolve issue: {str(e)}')
        
        # Redirect back to the issue detail page
        return redirect('issue_management:supervisor:issue_detail', issue_slug=issue.slug)

    

class WorkTaskCreateView(CreateView):
    template_name = "supervisor/issue_management/work_task_create.html"
    form_class = WorkTaskForm
    model = WorkTask
    
    def dispatch(self, request, *args, **kwargs):
        # Get the issue this work task belongs to
        self.issue = get_object_or_404(Issue, slug=kwargs['issue_slug'])
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['issue'] = self.issue
        return kwargs
    
    def form_valid(self, form):
        # Set the issue before saving
        form.instance.issue = self.issue
        response = super().form_valid(form)
        messages.success(self.request, f'Work task "{form.instance.title}" created successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('issue_management:supervisor:issue_detail', kwargs={'issue_slug': self.issue.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['issue'] = self.issue
        return context


class WorkTaskUpdateView(UpdateView):
    template_name = "supervisor/issue_management/work_task_update.html"
    form_class = WorkTaskUpdateForm
    model = WorkTask
    slug_field = 'slug'
    slug_url_kwarg = 'work_task_slug'
    
    def dispatch(self, request, *args, **kwargs):
        # Get the work task and its associated issue
        self.work_task = get_object_or_404(WorkTask, slug=kwargs['work_task_slug'])
        self.issue = self.work_task.issue
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['issue'] = self.issue
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Work task "{form.instance.title}" updated successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('issue_management:supervisor:issue_detail', kwargs={'issue_slug': self.issue.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['issue'] = self.issue
        context['work_task'] = self.work_task
        return context


class WorkTaskCompleteView(UpdateView):
    """Complete a work task with resolution notes"""
    template_name = "supervisor/issue_management/work_task_complete.html"
    form_class = WorkTaskCompleteForm
    model = WorkTask
    slug_field = 'slug'
    slug_url_kwarg = 'work_task_slug'
    
    def dispatch(self, request, *args, **kwargs):
        self.work_task = get_object_or_404(WorkTask, slug=kwargs['work_task_slug'])
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        # Mark the task as completed and save resolution notes
        form.instance.completed = True
        response = super().form_valid(form)
        messages.success(self.request, f'Work task "{form.instance.title}" marked as completed!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('issue_management:supervisor:issue_detail', kwargs={'issue_slug': self.work_task.issue.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['work_task'] = self.work_task
        context['issue'] = self.work_task.issue
        return context


class WorkTaskToggleCompleteView(UpdateView):
    """Toggle the completion status of a work task"""
    model = WorkTask
    slug_field = 'slug'
    slug_url_kwarg = 'work_task_slug'
    fields = ['completed']
    
    def dispatch(self, request, *args, **kwargs):
        self.work_task = get_object_or_404(WorkTask, slug=kwargs['work_task_slug'])
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        # Toggle the completion status (only for reopening)
        if self.work_task.completed:
            self.work_task.completed = False
            self.work_task.save()
            messages.success(self.request, f'Work task "{self.work_task.title}" marked as pending!')
        
        return redirect('issue_management:supervisor:issue_detail', issue_slug=self.work_task.issue.slug)


class WorkTaskDeleteView(View):
    """Delete a work task"""
    
    def post(self, request, work_task_slug):
        work_task = get_object_or_404(WorkTask, slug=work_task_slug)
        issue_slug = work_task.issue.slug
        task_title = work_task.title
        
        work_task.delete()
        messages.success(request, f'Work task "{task_title}" has been deleted.')

        return redirect('issue_management:supervisor:issue_detail', issue_slug=issue_slug)