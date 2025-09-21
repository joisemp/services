from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from ..models import Issue, IssueImage, WorkTask, IssueComment
from ..forms import IssueForm, WorkTaskForm, WorkTaskUpdateForm, WorkTaskCompleteForm, IssueCommentForm


class IssueListView(ListView):
    template_name = "central_admin/issue_management/issue_list.html"
    context_object_name = "issues"
    model = Issue
    
    def get_queryset(self):
        queryset = Issue.objects.prefetch_related('images').select_related('org', 'space', 'reporter').all()
        
        # Filter by status if provided
        status_filter = self.request.GET.get('status')
        if status_filter and status_filter in ['open', 'assigned', 'in_progress', 'critical']:
            if status_filter == 'critical':
                queryset = queryset.filter(priority='critical')
            else:
                queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_filter'] = self.request.GET.get('status', 'all')
        return context

    
class IssueCreateView(CreateView):
    template_name = "central_admin/issue_management/issue_create.html"
    form_class = IssueForm
    success_url = reverse_lazy('issue_management:central_admin:issue_list')
    
    def form_valid(self, form):
        # Set the reporter to the current user before saving
        form.instance.reporter = self.request.user
        
        # Save the issue first
        response = super().form_valid(form)
        
        # Handle image uploads
        image_fields = ['image1', 'image2', 'image3']
        for field_name in image_fields:
            image_file = form.cleaned_data.get(field_name)
            if image_file:
                IssueImage.objects.create(
                    issue=self.object,
                    image=image_file
                )
        
        return response
    

class IssueDetailView(DetailView):
    template_name = "central_admin/issue_management/issue_detail.html"
    context_object_name = "issue"
    model = Issue
    slug_field = 'slug'
    slug_url_kwarg = 'issue_slug'
    
    def get_queryset(self):
        return Issue.objects.prefetch_related('images', 'comments', 'work_tasks__assigned_to').select_related('org', 'space')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add work tasks to context
        context['work_tasks'] = self.object.work_tasks.all().order_by('-created_at')
        # Add comment form to context
        context['comment_form'] = IssueCommentForm()
        return context


class WorkTaskCreateView(CreateView):
    template_name = "central_admin/issue_management/work_task_create.html"
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
        return reverse_lazy('issue_management:central_admin:issue_detail', kwargs={'issue_slug': self.issue.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['issue'] = self.issue
        return context


class WorkTaskUpdateView(UpdateView):
    template_name = "central_admin/issue_management/work_task_update.html"
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
        return reverse_lazy('issue_management:central_admin:issue_detail', kwargs={'issue_slug': self.issue.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['issue'] = self.issue
        context['work_task'] = self.work_task
        return context


class WorkTaskCompleteView(UpdateView):
    """Complete a work task with resolution notes"""
    template_name = "central_admin/issue_management/work_task_complete.html"
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
        return reverse_lazy('issue_management:central_admin:issue_detail', kwargs={'issue_slug': self.work_task.issue.slug})
    
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
        
        return redirect('issue_management:central_admin:issue_detail', issue_slug=self.work_task.issue.slug)


class WorkTaskDeleteView(View):
    """Delete a work task"""
    
    def post(self, request, work_task_slug):
        work_task = get_object_or_404(WorkTask, slug=work_task_slug)
        issue_slug = work_task.issue.slug
        task_title = work_task.title
        
        work_task.delete()
        messages.success(request, f'Work task "{task_title}" has been deleted.')
        
        return redirect('issue_management:central_admin:issue_detail', issue_slug=issue_slug)


class IssueCommentListView(View):
    """HTMX endpoint to return the list of comments for an issue"""
    
    def get(self, request, issue_slug):
        issue = get_object_or_404(Issue, slug=issue_slug)
        comments = issue.comments.select_related('user').all()
        
        return render(request, 'central_admin/issue_management/partials/comment_list.html', {
            'comments': comments,
            'issue': issue
        })


class IssueCommentCreateView(View):
    """HTMX endpoint to create a new comment"""
    
    def post(self, request, issue_slug):
        issue = get_object_or_404(Issue, slug=issue_slug)
        form = IssueCommentForm(request.POST)
        
        if form.is_valid():
            comment = form.save(commit=False)
            comment.issue = issue
            comment.user = request.user
            comment.save()
            
            # Return the updated comment list
            comments = issue.comments.select_related('user').all()
            return render(request, 'central_admin/issue_management/partials/comment_list.html', {
                'comments': comments,
                'issue': issue
            })
        else:
            # Return form errors
            return render(request, 'central_admin/issue_management/partials/comment_form.html', {
                'form': form,
                'issue': issue
            }, status=400)
    
    def get(self, request, issue_slug):
        """Return empty form for HTMX to display"""
        issue = get_object_or_404(Issue, slug=issue_slug)
        form = IssueCommentForm()
        
        return render(request, 'central_admin/issue_management/partials/comment_form.html', {
            'form': form,
            'issue': issue
        })


class IssueDeleteView(DeleteView):
    """Delete an issue and all its related data"""
    template_name = "central_admin/issue_management/issue_delete.html"
    model = Issue
    slug_field = 'slug'
    slug_url_kwarg = 'issue_slug'
    success_url = reverse_lazy('issue_management:central_admin:issue_list')
    
    def get_queryset(self):
        return Issue.objects.prefetch_related('images', 'comments', 'work_tasks__shares').select_related('org', 'space', 'reporter')
    
    def delete(self, request, *args, **kwargs):
        """Override delete to add success message"""
        self.object = self.get_object()
        issue_title = self.object.title
        
        # Django's CASCADE will automatically delete:
        # - IssueImage instances (related via images)
        # - IssueComment instances (related via comments) 
        # - WorkTask instances (related via work_tasks)
        # - WorkTaskShare instances (related via work_tasks__shares)
        
        success_url = self.get_success_url()
        self.object.delete()
        
        messages.success(request, f'Issue "{issue_title}" and all its related data have been permanently deleted.')
        
        return redirect(success_url)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add counts of related objects that will be deleted
        context['related_counts'] = {
            'images': self.object.images.count(),
            'comments': self.object.comments.count(),
            'work_tasks': self.object.work_tasks.count(),
            'work_task_shares': sum(task.shares.count() for task in self.object.work_tasks.all()),
        }
        return context


class IssueImageDeleteView(View):
    """Delete a specific image attached to an issue"""
    
    def post(self, request, issue_slug, image_slug):
        # Get the issue and image
        issue = get_object_or_404(Issue, slug=issue_slug)
        image = get_object_or_404(IssueImage, slug=image_slug, issue=issue)
        
        # Store the image filename for the success message
        image_name = image.image.name
        
        # Delete the image file from storage
        if image.image:
            image.image.delete(save=False)
        
        # Delete the image record
        image.delete()
        
        messages.success(request, f'Image successfully deleted.')
        
        # Redirect back to the issue detail page
        return redirect('issue_management:central_admin:issue_detail', issue_slug=issue.slug)