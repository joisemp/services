from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from ..models import Issue, IssueImage, WorkTask, IssueComment
from ..forms import IssueForm, WorkTaskForm, WorkTaskUpdateForm, WorkTaskCompleteForm, IssueCommentForm, AdditionalImageUploadForm, VoiceUploadForm, IssueUpdateForm, IssueAssignmentForm


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
        work_tasks = self.object.work_tasks.all().order_by('-created_at')
        context['work_tasks'] = work_tasks
        # Check if there are any incomplete work tasks
        context['has_incomplete_tasks'] = work_tasks.filter(completed=False).exists()
        # Add comment form to context
        context['comment_form'] = IssueCommentForm()
        return context
    
    
class IssueUpdateView(UpdateView):
    template_name = "central_admin/issue_management/issue_update.html"
    form_class = IssueUpdateForm
    model = Issue
    slug_field = 'slug'
    slug_url_kwarg = 'issue_slug'
    
    def get_queryset(self):
        return Issue.objects.prefetch_related('images').select_related('org', 'space', 'reporter')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Issue "{form.instance.title}" updated successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('issue_management:central_admin:issue_detail', kwargs={'issue_slug': self.object.slug})


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


class IssueImageUploadView(View):
    """Upload additional images to an existing issue"""
    
    def get(self, request, issue_slug):
        # Get the issue
        issue = get_object_or_404(Issue, slug=issue_slug)
        form = AdditionalImageUploadForm()
        
        context = {
            'issue': issue,
            'form': form,
        }
        return render(request, 'central_admin/issue_management/image_upload.html', context)
    
    def post(self, request, issue_slug):
        # Get the issue
        issue = get_object_or_404(Issue, slug=issue_slug)
        form = AdditionalImageUploadForm(request.POST, request.FILES)
        
        if form.is_valid():
            # Get the list of uploaded images from cleaned_data
            images = form.cleaned_data.get('images')
            uploaded_count = 0
            
            # Ensure images is a list
            if not isinstance(images, list):
                images = [images] if images else []
            
            # Create IssueImage instances for each uploaded image
            for image_file in images:
                try:
                    IssueImage.objects.create(
                        issue=issue,
                        image=image_file
                    )
                    uploaded_count += 1
                except Exception as e:
                    messages.error(request, f'Failed to upload image "{image_file.name}": {str(e)}')
            
            if uploaded_count > 0:
                if uploaded_count == 1:
                    messages.success(request, f'Successfully uploaded {uploaded_count} image.')
                else:
                    messages.success(request, f'Successfully uploaded {uploaded_count} images.')
                
                # Redirect back to the issue detail page
                return redirect('issue_management:central_admin:issue_detail', issue_slug=issue.slug)
        
        # If form is not valid, show errors
        context = {
            'issue': issue,
            'form': form,
        }
        return render(request, 'central_admin/issue_management/image_upload.html', context)


class IssueVoiceDeleteView(View):
    """Delete the voice recording attached to an issue"""
    
    def post(self, request, issue_slug):
        # Get the issue
        issue = get_object_or_404(Issue, slug=issue_slug)
        
        # Check if issue has a voice recording
        if not issue.voice:
            messages.error(request, 'No voice recording found for this issue.')
            return redirect('issue_management:central_admin:issue_detail', issue_slug=issue.slug)
        
        # Delete the voice file from storage
        if issue.voice:
            issue.voice.delete(save=False)
        
        # Clear the voice field and save the issue
        issue.voice = None
        issue.save()
        
        messages.success(request, 'Voice recording successfully deleted.')
        
        # Redirect back to the issue detail page
        return redirect('issue_management:central_admin:issue_detail', issue_slug=issue.slug)


class IssueVoiceUploadView(View):
    """Upload a voice recording to an existing issue"""
    
    def get(self, request, issue_slug):
        # Get the issue
        issue = get_object_or_404(Issue, slug=issue_slug)
        
        # Check if issue already has a voice recording
        if issue.voice:
            messages.error(request, 'This issue already has a voice recording. Delete it first to upload a new one.')
            return redirect('issue_management:central_admin:issue_detail', issue_slug=issue.slug)
        
        form = VoiceUploadForm()
        
        context = {
            'issue': issue,
            'form': form,
        }
        return render(request, 'central_admin/issue_management/voice_upload.html', context)
    
    def post(self, request, issue_slug):
        # Get the issue
        issue = get_object_or_404(Issue, slug=issue_slug)
        
        # Check if issue already has a voice recording
        if issue.voice:
            messages.error(request, 'This issue already has a voice recording. Delete it first to upload a new one.')
            return redirect('issue_management:central_admin:issue_detail', issue_slug=issue.slug)
        
        form = VoiceUploadForm(request.POST, request.FILES)
        
        if form.is_valid():
            # Get the voice file from cleaned_data
            voice_file = form.cleaned_data.get('voice')
            
            if voice_file:
                try:
                    # Save the voice file to the issue
                    issue.voice = voice_file
                    issue.save()
                    
                    messages.success(request, 'Voice recording successfully uploaded.')
                    return redirect('issue_management:central_admin:issue_detail', issue_slug=issue.slug)
                    
                except Exception as e:
                    messages.error(request, f'Failed to upload voice recording: {str(e)}')
        
        # If form is not valid, show errors
        context = {
            'issue': issue,
            'form': form,
        }
        return render(request, 'central_admin/issue_management/voice_upload.html', context)


class IssueAssignmentView(UpdateView):
    """Assign an issue to a supervisor with optional review requirement"""
    template_name = "central_admin/issue_management/issue_assignment.html"
    form_class = IssueAssignmentForm
    model = Issue
    slug_field = 'slug'
    slug_url_kwarg = 'issue_slug'
    
    def dispatch(self, request, *args, **kwargs):
        self.issue = get_object_or_404(Issue, slug=kwargs['issue_slug'])
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['issue'] = self.issue
        return kwargs
    
    def form_valid(self, form):
        # Set assignment metadata
        form.instance.assigned_by = self.request.user
        form.instance.assigned_at = timezone.now()
        
        # Update status to assigned when a supervisor is assigned
        # Only change status if it's not already resolved, closed, or cancelled
        if form.instance.status not in ['resolved', 'closed', 'cancelled']:
            form.instance.status = 'assigned'
        
        response = super().form_valid(form)
        
        assigned_to_name = form.instance.assigned_to.get_full_name() or form.instance.assigned_to.email
        review_text = " (with review required)" if form.instance.requires_review else ""
        
        messages.success(
            self.request, 
            f'Issue "{form.instance.title}" has been assigned to {assigned_to_name}{review_text}.'
        )
        
        return response
    
    def get_success_url(self):
        return reverse_lazy('issue_management:central_admin:issue_detail', kwargs={'issue_slug': self.issue.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['issue'] = self.issue
        return context


class IssueReopenView(View):
    """Reopen a resolved, closed, or cancelled issue"""
    
    def post(self, request, issue_slug):
        # Get the issue
        issue = get_object_or_404(Issue, slug=issue_slug)
        
        # Check if issue can be reopened
        if issue.status not in ['resolved', 'closed', 'cancelled']:
            messages.error(request, f'Only resolved, closed, or cancelled issues can be reopened. This issue is currently {issue.get_status_display().lower()}.')
            return redirect('issue_management:central_admin:issue_detail', issue_slug=issue.slug)
        
        try:
            # Store the previous status for the message
            previous_status = issue.get_status_display()
            
            # Reopen the issue
            if issue.assigned_to:
                issue.status = 'assigned'
            else:
                issue.status = 'open'
            
            # Clear resolution notes when reopening
            issue.resolution_notes = None
            
            # Clear review information when reopening
            issue.reviewed_by = None
            issue.reviewed_at = None
            issue.review_notes = None
            
            issue.save()
            
            messages.success(request, f'Issue "{issue.title}" has been reopened from {previous_status.lower()} status.')
            
        except Exception as e:
            messages.error(request, f'Failed to reopen issue: {str(e)}')
        
        # Redirect back to the issue detail page
        return redirect('issue_management:central_admin:issue_detail', issue_slug=issue.slug)


class IssueResolveView(View):
    """Mark an issue as resolved with resolution notes"""
    
    def post(self, request, issue_slug):
        # Get the issue
        issue = get_object_or_404(Issue, slug=issue_slug)
        
        # Check if issue is already resolved, closed, or cancelled
        if issue.status in ['resolved', 'closed', 'cancelled']:
            messages.error(request, f'This issue is already {issue.get_status_display().lower()} and cannot be resolved again.')
            return redirect('issue_management:central_admin:issue_detail', issue_slug=issue.slug)
        
        # Check if there are any incomplete work tasks
        incomplete_tasks = issue.work_tasks.filter(completed=False)
        if incomplete_tasks.exists():
            incomplete_count = incomplete_tasks.count()
            task_word = 'task' if incomplete_count == 1 else 'tasks'
            messages.error(request, f'Cannot resolve issue while {incomplete_count} work {task_word} remain incomplete. Please complete all work tasks before marking the issue as resolved.')
            return redirect('issue_management:central_admin:issue_detail', issue_slug=issue.slug)
        
        # Get resolution notes from the form
        resolution_notes = request.POST.get('resolution_notes', '').strip()
        
        if not resolution_notes:
            messages.error(request, 'Resolution notes are required to mark an issue as resolved.')
            return redirect('issue_management:central_admin:issue_detail', issue_slug=issue.slug)
        
        try:
            # Update the issue status and resolution notes
            issue.status = 'resolved'
            issue.resolution_notes = resolution_notes
            issue.save()
            
            messages.success(request, f'Issue "{issue.title}" has been successfully marked as resolved.')
            
        except Exception as e:
            messages.error(request, f'Failed to resolve issue: {str(e)}')
        
        # Redirect back to the issue detail page
        return redirect('issue_management:central_admin:issue_detail', issue_slug=issue.slug)