from django.shortcuts import get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.urls import reverse_lazy
from django.db.models import Case, When, IntegerField
from .. forms import IssueCommentForm, WorkTaskForm, WorkTaskUpdateForm, WorkTaskCompleteForm
from django.contrib import messages
from .. models import Issue, WorkTask
from django.shortcuts import redirect
from config.mixins.access_mixin import SupervisorOnlyAccessMixin


class WorkTaskListView(SupervisorOnlyAccessMixin, ListView):
    """List all work tasks assigned to the supervisor"""
    model = WorkTask
    template_name = "supervisor/issue_management/work_task_list.html"
    context_object_name = "work_tasks"

    def get_queryset(self):
        queryset = WorkTask.objects.filter(assigned_to=self.request.user).select_related('issue', 'issue__org', 'issue__space')
        
        # Filter by status if provided
        status_filter = self.request.GET.get('status', None)
        if status_filter == 'pending':
            queryset = queryset.filter(completed=False)
        elif status_filter == 'completed':
            queryset = queryset.filter(completed=True)
        
        # Order by completion status, issue priority (critical first, low last), then due date
        return queryset.annotate(
            priority_order=Case(
                When(issue__priority='critical', then=1),
                When(issue__priority='high', then=2),
                When(issue__priority='medium', then=3),
                When(issue__priority='low', then=4),
                default=5,
                output_field=IntegerField(),
            )
        ).order_by('completed', 'priority_order', 'due_date')


class WorkTaskDetailView(SupervisorOnlyAccessMixin, DetailView):
    """View details of a specific work task"""
    model = WorkTask
    template_name = "supervisor/issue_management/work_task_detail.html"
    context_object_name = "work_task"
    slug_field = 'slug'
    slug_url_kwarg = 'work_task_slug'
    
    def get_queryset(self):
        return WorkTask.objects.filter(assigned_to=self.request.user).select_related(
            'issue', 
            'issue__org', 
            'issue__space',
            'issue__reporter'
        ).prefetch_related('issue__images')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['issue'] = self.object.issue
        return context


class SupervisorIssueListView(SupervisorOnlyAccessMixin, ListView):
    model = Issue
    template_name = "supervisor/issue_management/issue_list.html"
    context_object_name = "issues"

    def get_queryset(self):
        # Order by status (open/assigned/in_progress first), then priority (critical first, low last), then creation date
        return Issue.objects.filter(assigned_to=self.request.user).annotate(
            status_order=Case(
                When(status='open', then=1),
                When(status='assigned', then=2),
                When(status='in_progress', then=3),
                When(status='resolved', then=4),
                When(status='escalated', then=5),
                When(status='closed', then=6),
                When(status='cancelled', then=7),
                default=8,
                output_field=IntegerField(),
            ),
            priority_order=Case(
                When(priority='critical', then=1),
                When(priority='high', then=2),
                When(priority='medium', then=3),
                When(priority='low', then=4),
                default=5,
                output_field=IntegerField(),
            )
        ).order_by('status_order', 'priority_order', '-created_at')
    
    
class IssueDetailView(SupervisorOnlyAccessMixin, DetailView):
    template_name = "supervisor/issue_management/issue_detail.html"
    context_object_name = "issue"
    model = Issue
    slug_field = 'slug'
    slug_url_kwarg = 'issue_slug'
    
    def get_queryset(self):
        return Issue.objects.prefetch_related('images', 'comments', 'work_tasks__assigned_to').select_related('org', 'space')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add work tasks to context sorted by completion status and issue priority
        work_tasks = self.object.work_tasks.select_related('issue').all().annotate(
            priority_order=Case(
                When(issue__priority='critical', then=1),
                When(issue__priority='high', then=2),
                When(issue__priority='medium', then=3),
                When(issue__priority='low', then=4),
                default=5,
                output_field=IntegerField(),
            )
        ).order_by('completed', 'priority_order', 'due_date')
        context['work_tasks'] = work_tasks
        # Check if there are any incomplete work tasks
        context['has_incomplete_tasks'] = work_tasks.filter(completed=False).exists()
        # Add comment form to context
        context['comment_form'] = IssueCommentForm()
        return context
    

class IssueResolveView(SupervisorOnlyAccessMixin, View):
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

    

class WorkTaskCreateView(SupervisorOnlyAccessMixin, CreateView):
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


class WorkTaskUpdateView(SupervisorOnlyAccessMixin,UpdateView):
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


class WorkTaskCompleteView(SupervisorOnlyAccessMixin, UpdateView):
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
        # Check if 'next' parameter is set to redirect to task detail page
        next_param = self.request.GET.get('next', None)
        if next_param == 'task_detail':
            return reverse_lazy('issue_management:supervisor:work_task_detail', kwargs={'work_task_slug': self.work_task.slug})
        # Default redirect to issue detail page
        return reverse_lazy('issue_management:supervisor:issue_detail', kwargs={'issue_slug': self.work_task.issue.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['work_task'] = self.work_task
        context['issue'] = self.work_task.issue
        # Pass the next parameter to the template
        context['next_param'] = self.request.GET.get('next', None)
        return context


class WorkTaskToggleCompleteView(SupervisorOnlyAccessMixin, UpdateView):
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


class WorkTaskDeleteView(SupervisorOnlyAccessMixin, View):
    """Delete a work task"""
    
    def post(self, request, work_task_slug):
        work_task = get_object_or_404(WorkTask, slug=work_task_slug)
        issue_slug = work_task.issue.slug
        task_title = work_task.title
        
        work_task.delete()
        messages.success(request, f'Work task "{task_title}" has been deleted.')

        return redirect('issue_management:supervisor:issue_detail', issue_slug=issue_slug)
    

class IssueStartWorkView(SupervisorOnlyAccessMixin, View):
    """Start work on an issue by changing its status to in_progress"""
    
    def post(self, request, issue_slug):
        # Get the issue
        issue = get_object_or_404(Issue, slug=issue_slug)

        if issue.status == 'in_progress':
            messages.info(request, 'Work is already in progress on this issue.')
            return redirect('issue_management:supervisor:issue_detail', issue_slug=issue.slug)

        try:
            # Store the previous status for the message
            previous_status = issue.get_status_display()
            
            # Change status to in_progress
            issue.status = 'in_progress'
            issue.save()
            
            messages.success(request, f'Started work on issue "{issue.title}". Status changed from {previous_status.lower()} to in progress.')
            
        except Exception as e:
            messages.error(request, f'Failed to start work on issue: {str(e)}')
        
        # Redirect back to the issue detail page
        return redirect('issue_management:supervisor:issue_detail', issue_slug=issue.slug)
