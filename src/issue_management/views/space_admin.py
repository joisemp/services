from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Case, When, IntegerField
from ..models import Issue, IssueImage, WorkTask, IssueComment
from ..forms import IssueForm, SpaceAdminIssueForm, WorkTaskForm, WorkTaskUpdateForm, WorkTaskCompleteForm, IssueCommentForm, AdditionalImageUploadForm, VoiceUploadForm, IssueUpdateForm, IssueAssignmentForm
from config.mixins.access_mixin import SpaceAdminOnlyAccessMixin, SpaceAdminWithActiveSpaceMixin

class IssueListView(SpaceAdminWithActiveSpaceMixin, ListView):
    template_name = "space_admin/issue_management/issue_list.html"
    context_object_name = "issues"
    model = Issue
    
    def get_queryset(self):
        queryset = Issue.objects.prefetch_related('images').select_related('org', 'space', 'reporter').all()
        
        # Filter by active space for space admins
        if self.request.user.is_space_admin and self.request.user.active_space:
            queryset = queryset.filter(space=self.request.user.active_space)
        
        # Filter by status if provided
        status_filter = self.request.GET.get('status')
        if status_filter and status_filter in ['open', 'assigned', 'in_progress', 'critical']:
            if status_filter == 'critical':
                queryset = queryset.filter(priority='critical')
            else:
                queryset = queryset.filter(status=status_filter)
        
        # Order by status groups, then priority, then creation date
        # Active issues (open/assigned/in_progress) first, then resolved/escalated, then closed/cancelled
        return queryset.annotate(
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
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_filter'] = self.request.GET.get('status', 'all')
        return context
    

class IssueCreateView(SpaceAdminWithActiveSpaceMixin, CreateView):
    template_name = "space_admin/issue_management/issue_create.html"
    form_class = SpaceAdminIssueForm
    success_url = reverse_lazy('issue_management:space_admin:issue_list')
    
    def get_form_kwargs(self):
        """Pass current_user and active_space to form"""
        kwargs = super().get_form_kwargs()
        kwargs['current_user'] = self.request.user
        kwargs['active_space'] = self.request.user.active_space if self.request.user.is_space_admin else None
        return kwargs
    
    def form_valid(self, form):
        # Set the reporter and space BEFORE saving the instance
        form.instance.reporter = self.request.user
        
        # Ensure active space is assigned before save
        if self.request.user.is_space_admin and self.request.user.active_space:
            form.instance.space = self.request.user.active_space
        
        # Ensure organization is set before save
        if self.request.user.organization:
            form.instance.org = self.request.user.organization
        
        # Now save the issue (super().form_valid() calls form.save())
        response = super().form_valid(form)
        
        # Handle image uploads after the issue is saved
        image_fields = ['image1', 'image2', 'image3']
        for field_name in image_fields:
            image_file = form.cleaned_data.get(field_name)
            if image_file:
                IssueImage.objects.create(
                    issue=self.object,
                    image=image_file
                )
        
        return response    


class IssueDetailView(SpaceAdminWithActiveSpaceMixin, DetailView):
    template_name = "space_admin/issue_management/issue_detail.html"
    context_object_name = "issue"
    model = Issue
    slug_field = 'slug'
    slug_url_kwarg = 'issue_slug'
    
    def get_queryset(self):
        queryset = Issue.objects.prefetch_related('images', 'comments', 'work_tasks__assigned_to').select_related('org', 'space')
        
        # Filter by active space for space admins
        if self.request.user.is_space_admin and self.request.user.active_space:
            queryset = queryset.filter(space=self.request.user.active_space)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add work tasks to context sorted by completion status, then by issue priority
        # Incomplete tasks first, ordered by issue's priority (critical to low)
        issue_priority_order = Case(
            When(issue__priority='critical', then=1),
            When(issue__priority='high', then=2),
            When(issue__priority='medium', then=3),
            When(issue__priority='low', then=4),
            default=5,
            output_field=IntegerField(),
        )
        work_tasks = self.object.work_tasks.select_related('issue').annotate(
            priority_order=issue_priority_order
        ).order_by('completed', 'priority_order', 'due_date')
        context['work_tasks'] = work_tasks
        # Check if there are any incomplete work tasks
        context['has_incomplete_tasks'] = work_tasks.filter(completed=False).exists()
        # Add comment form to context
        context['comment_form'] = IssueCommentForm()
        return context


class IssueImageDeleteView(SpaceAdminWithActiveSpaceMixin, View):
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
        return redirect('issue_management:space_admin:issue_detail', issue_slug=issue.slug)


class IssueImageUploadView(SpaceAdminWithActiveSpaceMixin, View):
    """Upload additional images to an existing issue"""
    
    def get(self, request, issue_slug):
        # Get the issue
        issue = get_object_or_404(Issue, slug=issue_slug)
        form = AdditionalImageUploadForm()
        
        context = {
            'issue': issue,
            'form': form,
        }
        return render(request, 'space_admin/issue_management/image_upload.html', context)
    
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
                return redirect('issue_management:space_admin:issue_detail', issue_slug=issue.slug)
        
        # If form is not valid, show errors
        context = {
            'issue': issue,
            'form': form,
        }
        return render(request, 'space_admin/issue_management/image_upload.html', context)


class IssueVoiceDeleteView(SpaceAdminWithActiveSpaceMixin, View):
    """Delete the voice recording attached to an issue"""
    
    def post(self, request, issue_slug):
        # Get the issue
        issue = get_object_or_404(Issue, slug=issue_slug)
        
        # Check if issue has a voice recording
        if not issue.voice:
            messages.error(request, 'No voice recording found for this issue.')
            return redirect('issue_management:space_admin:issue_detail', issue_slug=issue.slug)
        
        # Delete the voice file from storage
        if issue.voice:
            issue.voice.delete(save=False)
        
        # Clear the voice field and save the issue
        issue.voice = None
        issue.save()
        
        messages.success(request, 'Voice recording successfully deleted.')
        
        # Redirect back to the issue detail page
        return redirect('issue_management:space_admin:issue_detail', issue_slug=issue.slug)


class IssueVoiceUploadView(SpaceAdminWithActiveSpaceMixin, View):
    """Upload a voice recording to an existing issue"""
    
    def get(self, request, issue_slug):
        # Get the issue
        issue = get_object_or_404(Issue, slug=issue_slug)
        
        # Check if issue already has a voice recording
        if issue.voice:
            messages.error(request, 'This issue already has a voice recording. Delete it first to upload a new one.')
            return redirect('issue_management:space_admin:issue_detail', issue_slug=issue.slug)
        
        form = VoiceUploadForm()
        
        context = {
            'issue': issue,
            'form': form,
        }
        return render(request, 'space_admin/issue_management/voice_upload.html', context)
    
    def post(self, request, issue_slug):
        # Get the issue
        issue = get_object_or_404(Issue, slug=issue_slug)
        
        # Check if issue already has a voice recording
        if issue.voice:
            messages.error(request, 'This issue already has a voice recording. Delete it first to upload a new one.')
            return redirect('issue_management:space_admin:issue_detail', issue_slug=issue.slug)
        
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
                    return redirect('issue_management:space_admin:issue_detail', issue_slug=issue.slug)
                    
                except Exception as e:
                    messages.error(request, f'Failed to upload voice recording: {str(e)}')
        
        # If form is not valid, show errors
        context = {
            'issue': issue,
            'form': form,
        }
        return render(request, 'space_admin/issue_management/voice_upload.html', context)


class IssueResolveView(SpaceAdminWithActiveSpaceMixin, View):
    """Mark an issue as resolved with resolution notes"""
    
    def post(self, request, issue_slug):
        # Get the issue
        issue = get_object_or_404(Issue, slug=issue_slug)
        
        # Check if issue is already resolved, closed, or cancelled
        if issue.status in ['resolved', 'closed', 'cancelled']:
            messages.error(request, f'This issue is already {issue.get_status_display().lower()} and cannot be resolved again.')
            return redirect('issue_management:space_admin:issue_detail', issue_slug=issue.slug)
        
        # Check if there are any incomplete work tasks
        incomplete_tasks = issue.work_tasks.filter(completed=False)
        if incomplete_tasks.exists():
            incomplete_count = incomplete_tasks.count()
            task_word = 'task' if incomplete_count == 1 else 'tasks'
            messages.error(request, f'Cannot resolve issue while {incomplete_count} work {task_word} remain incomplete. Please complete all work tasks before marking the issue as resolved.')
            return redirect('issue_management:space_admin:issue_detail', issue_slug=issue.slug)
        
        # Get resolution notes from the form
        resolution_notes = request.POST.get('resolution_notes', '').strip()
        
        if not resolution_notes:
            messages.error(request, 'Resolution notes are required to mark an issue as resolved.')
            return redirect('issue_management:space_admin:issue_detail', issue_slug=issue.slug)
        
        try:
            # Update the issue status and resolution notes
            issue.status = 'resolved'
            issue.resolution_notes = resolution_notes
            issue.save()
            
            messages.success(request, f'Issue "{issue.title}" has been successfully marked as resolved.')
            
        except Exception as e:
            messages.error(request, f'Failed to resolve issue: {str(e)}')
        
        # Redirect back to the issue detail page
        return redirect('issue_management:space_admin:issue_detail', issue_slug=issue.slug)


class IssueUpdateView(SpaceAdminWithActiveSpaceMixin, UpdateView):
    template_name = "space_admin/issue_management/issue_update.html"
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
        return reverse_lazy('issue_management:space_admin:issue_detail', kwargs={'issue_slug': self.object.slug})


class WorkTaskCreateView(SpaceAdminWithActiveSpaceMixin, CreateView):
    template_name = "space_admin/issue_management/work_task_create.html"
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
        return reverse_lazy('issue_management:space_admin:issue_detail', kwargs={'issue_slug': self.issue.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['issue'] = self.issue
        return context


class WorkTaskUpdateView(SpaceAdminWithActiveSpaceMixin, UpdateView):
    template_name = "space_admin/issue_management/work_task_update.html"
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
        return reverse_lazy('issue_management:space_admin:issue_detail', kwargs={'issue_slug': self.issue.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['issue'] = self.issue
        context['work_task'] = self.work_task
        return context


class WorkTaskCompleteView(SpaceAdminWithActiveSpaceMixin, UpdateView):
    """Complete a work task with resolution notes and images"""
    template_name = "space_admin/issue_management/work_task_complete.html"
    form_class = WorkTaskCompleteForm
    model = WorkTask
    slug_field = 'slug'
    slug_url_kwarg = 'work_task_slug'
    
    def dispatch(self, request, *args, **kwargs):
        self.work_task = get_object_or_404(WorkTask, slug=kwargs['work_task_slug'])
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        from ..models import WorkTaskResolutionImage
        
        # Mark the task as completed and save resolution notes
        form.instance.completed = True
        response = super().form_valid(form)
        
        # Handle resolution images (up to 3)
        image_count = 0
        for i in range(1, 4):
            image_field = f'image{i}'
            image = form.cleaned_data.get(image_field)
            if image:
                WorkTaskResolutionImage.objects.create(
                    work_task=form.instance,
                    image=image
                )
                image_count += 1
        
        if image_count > 0:
            messages.success(
                self.request, 
                f'Work task "{form.instance.title}" marked as completed with {image_count} resolution image(s)!'
            )
        else:
            messages.success(self.request, f'Work task "{form.instance.title}" marked as completed!')
        
        return response
    
    def get_success_url(self):
        return reverse_lazy('issue_management:space_admin:issue_detail', kwargs={'issue_slug': self.work_task.issue.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['work_task'] = self.work_task
        context['issue'] = self.work_task.issue
        return context


class WorkTaskToggleCompleteView(SpaceAdminWithActiveSpaceMixin, UpdateView):
    """Toggle the completion status of a work task"""
    model = WorkTask
    slug_field = 'slug'
    slug_url_kwarg = 'work_task_slug'
    fields = ['completed']
    
    def dispatch(self, request, *args, **kwargs):
        self.work_task = get_object_or_404(WorkTask, slug=kwargs['work_task_slug'])
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        from ..models import WorkTaskResolutionImage
        
        # Toggle the completion status (only for reopening)
        if self.work_task.completed:
            # Delete all resolution images when marking as pending
            resolution_images = self.work_task.resolution_images.all()
            image_count = resolution_images.count()
            
            # Delete image files and database records
            for res_image in resolution_images:
                # Delete the actual file from storage
                if res_image.image:
                    res_image.image.delete(save=False)
                # Delete the database record
                res_image.delete()
            
            # Mark task as pending
            self.work_task.completed = False
            self.work_task.resolution_notes = None  # Clear resolution notes
            self.work_task.save()
            
            if image_count > 0:
                messages.success(
                    self.request, 
                    f'Work task "{self.work_task.title}" marked as pending. {image_count} resolution image(s) deleted.'
                )
            else:
                messages.success(self.request, f'Work task "{self.work_task.title}" marked as pending!')
        
        return redirect('issue_management:space_admin:issue_detail', issue_slug=self.work_task.issue.slug)


class WorkTaskDeleteView(SpaceAdminWithActiveSpaceMixin, View):
    """Delete a work task and its resolution images"""
    
    def post(self, request, work_task_slug):
        from ..models import WorkTaskResolutionImage
        
        work_task = get_object_or_404(WorkTask, slug=work_task_slug)
        issue_slug = work_task.issue.slug
        task_title = work_task.title
        
        # Delete all resolution images before deleting the work task
        resolution_images = work_task.resolution_images.all()
        for res_image in resolution_images:
            # Delete the actual file from storage
            if res_image.image:
                res_image.image.delete(save=False)
            # Delete the database record
            res_image.delete()
        
        work_task.delete()
        messages.success(request, f'Work task "{task_title}" has been deleted.')
        
        return redirect('issue_management:space_admin:issue_detail', issue_slug=issue_slug)


class WorkTaskResolutionImageDeleteView(SpaceAdminWithActiveSpaceMixin, View):
    """Delete a specific resolution image attached to a work task"""
    
    def post(self, request, work_task_slug, image_slug):
        from ..models import WorkTaskResolutionImage
        
        # Get the work task and resolution image
        work_task = get_object_or_404(WorkTask, slug=work_task_slug)
        res_image = get_object_or_404(WorkTaskResolutionImage, slug=image_slug, work_task=work_task)
        
        # Delete the image file from storage
        if res_image.image:
            res_image.image.delete(save=False)
        
        # Delete the image record
        res_image.delete()
        
        messages.success(request, f'Resolution image successfully deleted.')
        
        # Redirect back to the issue detail page
        return redirect('issue_management:space_admin:issue_detail', issue_slug=work_task.issue.slug)


class IssueDeleteView(SpaceAdminWithActiveSpaceMixin, DeleteView):
    """Delete an issue and all its related data"""
    template_name = "space_admin/issue_management/issue_delete.html"
    model = Issue
    slug_field = 'slug'
    slug_url_kwarg = 'issue_slug'
    success_url = reverse_lazy('issue_management:space_admin:issue_list')
    
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


class IssueAssignmentView(SpaceAdminWithActiveSpaceMixin, UpdateView):
    """Assign an issue to a supervisor with optional review requirement"""
    template_name = "space_admin/issue_management/issue_assignment.html"
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
        
        # Save the form first (this saves the Issue instance)
        response = super().form_valid(form)
        
        # Check if review is required
        if form.instance.requires_review:
            # Redirect to reviewer selection page (Step 2)
            messages.info(
                self.request,
                'Issue assigned successfully. Now please select reviewers for this issue.'
            )
            return redirect('issue_management:space_admin:issue_select_reviewers', issue_slug=self.object.slug)
        else:
            # No review required, clear any existing reviewers and show success message
            self.object.reviewers.clear()
            
            assigned_to_name = form.instance.assigned_to.get_full_name() or form.instance.assigned_to.email
            
            messages.success(
                self.request, 
                f'Issue "{form.instance.title}" has been assigned to {assigned_to_name}.'
            )
            
            return response
    
    def get_success_url(self):
        return reverse_lazy('issue_management:space_admin:issue_detail', kwargs={'issue_slug': self.issue.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['issue'] = self.issue
        return context


class IssueReviewerSelectionView(SpaceAdminWithActiveSpaceMixin, View):
    """Select reviewers for an issue that requires review (Step 2 after assignment)"""
    template_name = "space_admin/issue_management/issue_reviewer_selection.html"
    
    def dispatch(self, request, *args, **kwargs):
        self.issue = get_object_or_404(Issue, slug=kwargs['issue_slug'])
        
        # Redirect if issue doesn't require review
        if not self.issue.requires_review:
            messages.warning(request, 'This issue does not require review.')
            return redirect('issue_management:space_admin:issue_detail', issue_slug=self.issue.slug)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, issue_slug):
        from ..forms import IssueReviewerSelectionForm
        form = IssueReviewerSelectionForm(issue=self.issue)
        return render(request, self.template_name, {
            'form': form,
            'issue': self.issue
        })
    
    def post(self, request, issue_slug):
        from ..forms import IssueReviewerSelectionForm
        form = IssueReviewerSelectionForm(request.POST, issue=self.issue)
        
        if form.is_valid():
            # Save the selected reviewers
            reviewers = form.cleaned_data['reviewers']
            self.issue.reviewers.set(reviewers)
            
            # Create success message with reviewer names
            reviewer_names = ", ".join([r.get_full_name() or r.email for r in reviewers])
            assigned_to_name = self.issue.assigned_to.get_full_name() or self.issue.assigned_to.email
            
            messages.success(
                request,
                f'Issue "{self.issue.title}" has been assigned to {assigned_to_name} with review required by: {reviewer_names}.'
            )
            
            return redirect('issue_management:space_admin:issue_detail', issue_slug=self.issue.slug)
        
        return render(request, self.template_name, {
            'form': form,
            'issue': self.issue
        })


class IssueReopenView(SpaceAdminWithActiveSpaceMixin, View):
    """Reopen a resolved, closed, or cancelled issue"""
    
    def post(self, request, issue_slug):
        # Get the issue
        issue = get_object_or_404(Issue, slug=issue_slug)
        
        # Check if issue can be reopened
        if issue.status not in ['resolved', 'closed', 'cancelled']:
            messages.error(request, f'Only resolved, closed, or cancelled issues can be reopened. This issue is currently {issue.get_status_display().lower()}.')
            return redirect('issue_management:space_admin:issue_detail', issue_slug=issue.slug)
        
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
        return redirect('issue_management:space_admin:issue_detail', issue_slug=issue.slug)


class IssueStartWorkView(SpaceAdminWithActiveSpaceMixin, View):
    """Start work on an issue by changing its status to in_progress"""
    
    def post(self, request, issue_slug):
        # Get the issue
        issue = get_object_or_404(Issue, slug=issue_slug)
        
        # Check if issue can be started
        if issue.status in ['resolved', 'closed', 'cancelled']:
            messages.error(request, f'Cannot start work on {issue.get_status_display().lower()} issues. Please reopen the issue first.')
            return redirect('issue_management:space_admin:issue_detail', issue_slug=issue.slug)
        
        if issue.status == 'in_progress':
            messages.info(request, 'Work is already in progress on this issue.')
            return redirect('issue_management:space_admin:issue_detail', issue_slug=issue.slug)
        
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
        return redirect('issue_management:space_admin:issue_detail', issue_slug=issue.slug)