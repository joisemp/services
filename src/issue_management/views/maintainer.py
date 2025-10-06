from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View
from django.contrib import messages
from ..models import WorkTask
from config.mixins.access_mixin import MaintainerOnlyAccessMixin


class WorkTaskListView(MaintainerOnlyAccessMixin, ListView):
    """List all work tasks assigned to the maintainer"""
    model = WorkTask
    template_name = "maintainer/issue_management/work_task_list.html"
    context_object_name = "work_tasks"

    def get_queryset(self):
        queryset = WorkTask.objects.filter(
            assigned_to=self.request.user
        ).select_related(
            'issue', 
            'issue__org', 
            'issue__space'
        ).order_by('-created_at')
        
        # Filter by status if provided
        status_filter = self.request.GET.get('status', None)
        if status_filter == 'pending':
            queryset = queryset.filter(completed=False)
        elif status_filter == 'completed':
            queryset = queryset.filter(completed=True)
        
        return queryset


class WorkTaskDetailView(MaintainerOnlyAccessMixin, DetailView):
    """View details of a specific work task"""
    model = WorkTask
    template_name = "maintainer/issue_management/work_task_detail.html"
    context_object_name = "work_task"
    slug_field = 'slug'
    slug_url_kwarg = 'work_task_slug'
    
    def get_queryset(self):
        return WorkTask.objects.filter(
            assigned_to=self.request.user
        ).select_related(
            'issue', 
            'issue__org', 
            'issue__space',
            'issue__reporter'
        ).prefetch_related('issue__images')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['issue'] = self.object.issue
        return context


class WorkTaskToggleCompleteView(MaintainerOnlyAccessMixin, View):
    """Toggle the completion status of a work task with resolution notes"""
    
    def post(self, request, work_task_slug):
        work_task = get_object_or_404(
            WorkTask, 
            slug=work_task_slug,
            assigned_to=request.user
        )
        
        # Get resolution notes from the form if marking as complete
        resolution_notes = request.POST.get('resolution_notes', '').strip()
        
        if not work_task.completed:
            # Marking task as complete
            if not resolution_notes:
                messages.error(
                    request, 
                    'Resolution notes are required to mark the task as completed.'
                )
                return redirect(
                    'issue_management:maintainer:work_task_detail', 
                    work_task_slug=work_task.slug
                )
            
            work_task.completed = True
            work_task.resolution_notes = resolution_notes
            work_task.save()
            messages.success(
                request, 
                f'Work task "{work_task.title}" marked as completed!'
            )
        else:
            # Reopening completed task
            work_task.completed = False
            work_task.save()
            messages.success(
                request, 
                f'Work task "{work_task.title}" marked as pending!'
            )
        
        return redirect(
            'issue_management:maintainer:work_task_detail', 
            work_task_slug=work_task.slug
        )
