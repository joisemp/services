from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View
from django.contrib import messages
from django.db.models import Case, When, IntegerField
from ..models import WorkTask, SiteVisit
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
        )
        
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
            from ..models import WorkTaskResolutionImage
            
            # Delete all resolution images when marking as pending
            resolution_images = work_task.resolution_images.all()
            image_count = resolution_images.count()
            
            # Delete image files and database records
            for res_image in resolution_images:
                # Delete the actual file from storage
                if res_image.image:
                    res_image.image.delete(save=False)
                # Delete the database record
                res_image.delete()
            
            # Mark task as pending
            work_task.completed = False
            work_task.resolution_notes = None  # Clear resolution notes
            work_task.save()
            
            if image_count > 0:
                messages.success(
                    request, 
                    f'Work task "{work_task.title}" marked as pending. {image_count} resolution image(s) deleted.'
                )
            else:
                messages.success(
                    request, 
                    f'Work task "{work_task.title}" marked as pending!'
                )
        
        return redirect(
            'issue_management:maintainer:work_task_detail', 
            work_task_slug=work_task.slug
        )


class SiteVisitListView(MaintainerOnlyAccessMixin, ListView):
    """List all site visits assigned to the maintainer"""
    model = SiteVisit
    template_name = "maintainer/issue_management/site_visit_list.html"
    context_object_name = "site_visits"

    def get_queryset(self):
        # Get site visits where the maintainer is assigned
        queryset = SiteVisit.objects.filter(
            assigned_to=self.request.user
        ).select_related('issue', 'issue__org', 'issue__space', 'created_by', 'assigned_to').prefetch_related('images')
        
        # Filter by status if provided
        status_filter = self.request.GET.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Order by status (scheduled first, then in_progress, completed last), then by scheduled date
        return queryset.annotate(
            status_order=Case(
                When(status='scheduled', then=1),
                When(status='in_progress', then=2),
                When(status='completed', then=3),
                When(status='cancelled', then=4),
                default=5,
                output_field=IntegerField(),
            )
        ).order_by('status_order', 'scheduled_date')


class SiteVisitDetailView(MaintainerOnlyAccessMixin, DetailView):
    """View details of a specific site visit"""
    model = SiteVisit
    template_name = "maintainer/issue_management/site_visit_detail.html"
    context_object_name = "site_visit"
    slug_field = 'slug'
    slug_url_kwarg = 'site_visit_slug'
    
    def get_queryset(self):
        return SiteVisit.objects.filter(
            assigned_to=self.request.user
        ).select_related(
            'issue',
            'issue__org',
            'issue__space',
            'issue__reporter',
            'created_by',
            'assigned_to'
        ).prefetch_related('images', 'issue__images')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['issue'] = self.object.issue
        return context
