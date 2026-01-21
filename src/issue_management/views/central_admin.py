from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Case, When, IntegerField
from ..models import Issue, IssueImage, WorkTask, IssueComment, SiteVisit, SiteVisitImage, PurchaseRequest, IssueActivity
from ..forms import IssueForm, WorkTaskForm, WorkTaskUpdateForm, WorkTaskCompleteForm, IssueCommentForm, AdditionalImageUploadForm, VoiceUploadForm, IssueUpdateForm, IssueAssignmentForm, SiteVisitForm
from ..forms_reports import PerformanceReportForm
from ..utils.performance_report import PerformanceReportGenerator
from config.mixins.access_mixin import CentralAdminOnlyAccessMixin
from core.models import Space


class IssueListView(CentralAdminOnlyAccessMixin, ListView):
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
        
        # Filter by space if provided
        space_filter = self.request.GET.get('space')
        if space_filter:
            if space_filter == 'no_space':
                # Filter issues with no space assigned
                queryset = queryset.filter(space__isnull=True)
            else:
                # Filter by specific space slug
                queryset = queryset.filter(space__slug=space_filter)
        
        # Order by status (open/assigned/in_progress first, then resolved/escalated, then closed/cancelled)
        # Then by priority (criticalâ†’highâ†’mediumâ†’low), then by creation date
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
        context['space_filter'] = self.request.GET.get('space', '')
        # Get all spaces for the filter dropdown
        context['spaces'] = Space.objects.select_related('org').all().order_by('org__name', 'name')
        return context

    
class IssueCreateView(CentralAdminOnlyAccessMixin, CreateView):
    template_name = "central_admin/issue_management/issue_create.html"
    form_class = IssueForm
    success_url = reverse_lazy('issue_management:central_admin:issue_list')
    
    def get_form_kwargs(self):
        """Pass current_user to form"""
        kwargs = super().get_form_kwargs()
        kwargs['current_user'] = self.request.user
        return kwargs
    
    def get_form(self, form_class=None):
        """Filter spaces to only show those in the user's organization"""
        form = super().get_form(form_class)
        if self.request.user.organization:
            form.fields['space'].queryset = Space.objects.filter(
                org=self.request.user.organization
            ).order_by('name')
        return form
    
    def post(self, request, *args, **kwargs):
        """Override post to prevent duplicate submissions"""
        # Check if this form has already been submitted
        form_token = request.POST.get('form_token', '')
        if form_token:
            # Check if token was already used
            used_tokens = request.session.get('used_issue_create_tokens', [])
            if form_token in used_tokens:
                messages.warning(request, 'This issue has already been created. Please do not submit the form multiple times.')
                return redirect(self.success_url)
        
        return super().post(request, *args, **kwargs)
    
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
                issue_image = IssueImage(
                    issue=self.object,
                    image=image_file
                )
                # Set the user who uploaded the image for activity tracking
                issue_image._uploaded_by = self.request.user
                issue_image.save()
        
        # Mark this form as submitted to prevent duplicates
        form_token = self.request.POST.get('form_token', '')
        if form_token:
            used_tokens = self.request.session.get('used_issue_create_tokens', [])
            used_tokens.append(form_token)
            # Keep only the last 10 tokens to prevent session bloat
            self.request.session['used_issue_create_tokens'] = used_tokens[-10:]
        
        messages.success(self.request, f'Issue "{self.object.title}" created successfully!')
        return response
    

class IssueDetailView(CentralAdminOnlyAccessMixin, DetailView):
    template_name = "central_admin/issue_management/issue_detail.html"
    context_object_name = "issue"
    model = Issue
    slug_field = 'slug'
    slug_url_kwarg = 'issue_slug'
    
    def get_queryset(self):
        return Issue.objects.prefetch_related(
            'images', 
            'comments', 
            'work_tasks__assigned_to',
            'work_tasks__resolution_images',
            'site_visits__created_by',
            'site_visits__assigned_to',
            'site_visits__images',
            'activities__user'
        ).select_related('org', 'space')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add work tasks to context sorted by completion status and issue priority
        work_tasks = self.object.work_tasks.select_related('issue').prefetch_related('resolution_images').all().annotate(
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
        # Add site visits to context
        site_visits = self.object.site_visits.select_related('created_by', 'assigned_to').prefetch_related('images').all()
        context['site_visits'] = site_visits
        # Add purchase requests to context
        purchase_requests = self.object.purchase_requests.select_related('requested_by', 'reviewed_by').all()
        context['purchase_requests'] = purchase_requests
        # Add activity history to context
        activities = self.object.activities.select_related('user').all()
        context['activities'] = activities
        return context
    
    
class IssueUpdateView(CentralAdminOnlyAccessMixin, UpdateView):
    template_name = "central_admin/issue_management/issue_update.html"
    form_class = IssueUpdateForm
    model = Issue
    slug_field = 'slug'
    slug_url_kwarg = 'issue_slug'
    
    def get_queryset(self):
        return Issue.objects.prefetch_related('images').select_related('org', 'space', 'reporter')
    
    def form_valid(self, form):
        # Set the user who updated the issue for activity tracking
        form.instance._changed_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Issue "{form.instance.title}" updated successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('issue_management:central_admin:issue_detail', kwargs={'issue_slug': self.object.slug})


class WorkTaskCreateView(CentralAdminOnlyAccessMixin, CreateView):
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
        # Set the user who created the task for activity tracking
        form.instance._created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Work task "{form.instance.title}" created successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('issue_management:central_admin:issue_detail', kwargs={'issue_slug': self.issue.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['issue'] = self.issue
        return context


class WorkTaskUpdateView(CentralAdminOnlyAccessMixin, UpdateView):
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
        # Set the user who updated the task for activity tracking
        form.instance._changed_by = self.request.user
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


class WorkTaskCompleteView(CentralAdminOnlyAccessMixin, UpdateView):
    """Complete a work task with resolution notes and images"""
    template_name = "central_admin/issue_management/work_task_complete.html"
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
        # Set the user who is completing the task for activity tracking
        form.instance._changed_by = self.request.user
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
        return reverse_lazy('issue_management:central_admin:issue_detail', kwargs={'issue_slug': self.work_task.issue.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['work_task'] = self.work_task
        context['issue'] = self.work_task.issue
        return context


class WorkTaskToggleCompleteView(CentralAdminOnlyAccessMixin, UpdateView):
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
            # Set the user who is reopening the task for activity tracking
            self.work_task._changed_by = self.request.user
            self.work_task.save()
            
            if image_count > 0:
                messages.success(
                    self.request, 
                    f'Work task "{self.work_task.title}" marked as pending. {image_count} resolution image(s) deleted.'
                )
            else:
                messages.success(self.request, f'Work task "{self.work_task.title}" marked as pending!')
        
        return redirect('issue_management:central_admin:issue_detail', issue_slug=self.work_task.issue.slug)


class WorkTaskDeleteView(CentralAdminOnlyAccessMixin, View):
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
        
        # Set the user who deleted the task for activity tracking
        work_task._deleted_by = request.user
        work_task.delete()
        messages.success(request, f'Work task "{task_title}" has been deleted.')
        
        return redirect('issue_management:central_admin:issue_detail', issue_slug=issue_slug)


class IssueDeleteView(CentralAdminOnlyAccessMixin, DeleteView):
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


class IssueImageDeleteView(CentralAdminOnlyAccessMixin, View):
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
        
        # Set the user who deleted the image for activity tracking
        image._deleted_by = request.user
        # Delete the image record
        image.delete()
        
        messages.success(request, f'Image successfully deleted.')
        
        # Redirect back to the issue detail page
        return redirect('issue_management:central_admin:issue_detail', issue_slug=issue.slug)


class WorkTaskResolutionImageDeleteView(CentralAdminOnlyAccessMixin, View):
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
        return redirect('issue_management:central_admin:issue_detail', issue_slug=work_task.issue.slug)


class IssueImageUploadView(CentralAdminOnlyAccessMixin, View):
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
                    issue_image = IssueImage(
                        issue=issue,
                        image=image_file
                    )
                    # Set the user who uploaded the image for activity tracking
                    issue_image._uploaded_by = request.user
                    issue_image.save()
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


class IssueVoiceDeleteView(CentralAdminOnlyAccessMixin, View):
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
        # Set the user who deleted the voice for activity tracking
        issue._changed_by = request.user
        issue.save()
        
        messages.success(request, 'Voice recording successfully deleted.')
        
        # Redirect back to the issue detail page
        return redirect('issue_management:central_admin:issue_detail', issue_slug=issue.slug)


class IssueVoiceUploadView(CentralAdminOnlyAccessMixin, View):
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
                    # Set the user who uploaded the voice for activity tracking
                    issue._changed_by = request.user
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


class IssueAssignmentView(CentralAdminOnlyAccessMixin, UpdateView):
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
        
        # Set the user who is assigning for activity tracking
        form.instance._changed_by = self.request.user
        
        # Save the form first (this saves the Issue instance)
        response = super().form_valid(form)
        
        # Check if review is required
        if form.instance.requires_review:
            # Redirect to reviewer selection page (Step 2)
            messages.info(
                self.request,
                'Issue assigned successfully. Now please select reviewers for this issue.'
            )
            return redirect('issue_management:central_admin:issue_select_reviewers', issue_slug=self.object.slug)
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
        return reverse_lazy('issue_management:central_admin:issue_detail', kwargs={'issue_slug': self.issue.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['issue'] = self.issue
        return context


class IssueReviewerSelectionView(CentralAdminOnlyAccessMixin, View):
    """Select reviewers for an issue that requires review (Step 2 after assignment)"""
    template_name = "central_admin/issue_management/issue_reviewer_selection.html"
    
    def dispatch(self, request, *args, **kwargs):
        self.issue = get_object_or_404(Issue, slug=kwargs['issue_slug'])
        
        # Redirect if issue doesn't require review
        if not self.issue.requires_review:
            messages.warning(request, 'This issue does not require review.')
            return redirect('issue_management:central_admin:issue_detail', issue_slug=self.issue.slug)
        
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
            # Set the user who is selecting reviewers for activity tracking
            self.issue._changed_by = request.user
            self.issue.reviewers.set(reviewers)
            
            # Create success message with reviewer names
            reviewer_names = ", ".join([r.get_full_name() or r.email for r in reviewers])
            assigned_to_name = self.issue.assigned_to.get_full_name() or self.issue.assigned_to.email
            
            messages.success(
                request,
                f'Issue "{self.issue.title}" has been assigned to {assigned_to_name} with review required by: {reviewer_names}.'
            )
            
            return redirect('issue_management:central_admin:issue_detail', issue_slug=self.issue.slug)
        
        return render(request, self.template_name, {
            'form': form,
            'issue': self.issue
        })


class IssueReopenView(CentralAdminOnlyAccessMixin, View):
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
            
            # Delete all resolution images
            issue.resolution_images.all().delete()
            
            # Clear review information when reopening
            issue.reviewed_by = None
            issue.reviewed_at = None
            issue.review_notes = None
            
            # Set the user who is reopening the issue for activity tracking
            issue._changed_by = request.user
            issue.save()
            
            messages.success(request, f'Issue "{issue.title}" has been reopened from {previous_status.lower()} status.')
            
        except Exception as e:
            messages.error(request, f'Failed to reopen issue: {str(e)}')
        
        # Redirect back to the issue detail page
        return redirect('issue_management:central_admin:issue_detail', issue_slug=issue.slug)


class IssueResolveView(CentralAdminOnlyAccessMixin, View):
    """Mark an issue as resolved with resolution notes and images"""
    
    def post(self, request, issue_slug):
        from ..models import IssueResolutionImage
        from ..forms import IssueResolveForm
        
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
        
        # Process the form
        form = IssueResolveForm(request.POST, request.FILES, instance=issue)
        
        if not form.is_valid():
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
            return redirect('issue_management:central_admin:issue_detail', issue_slug=issue.slug)
        
        try:
            # Update the issue status and resolution notes
            issue.status = 'resolved'
            issue.resolution_notes = form.cleaned_data['resolution_notes']
            # Set the user who is resolving the issue for activity tracking
            issue._changed_by = request.user
            issue.save()
            
            # Handle resolution images (up to 3)
            image_count = 0
            for i in range(1, 4):
                image_field = f'image{i}'
                image = form.cleaned_data.get(image_field)
                if image:
                    IssueResolutionImage.objects.create(
                        issue=issue,
                        image=image
                    )
                    image_count += 1
            
            if image_count > 0:
                messages.success(request, f'Issue "{issue.title}" has been successfully marked as resolved with {image_count} resolution image(s).')
            else:
                messages.success(request, f'Issue "{issue.title}" has been successfully marked as resolved.')
            
        except Exception as e:
            messages.error(request, f'Failed to resolve issue: {str(e)}')
        
        # Redirect back to the issue detail page
        return redirect('issue_management:central_admin:issue_detail', issue_slug=issue.slug)


class IssueStartWorkView(CentralAdminOnlyAccessMixin, View):
    """Start work on an issue by changing its status to in_progress"""
    
    def post(self, request, issue_slug):
        # Get the issue
        issue = get_object_or_404(Issue, slug=issue_slug)
        
        # Check if issue can be started
        if issue.status in ['resolved', 'closed', 'cancelled']:
            messages.error(request, f'Cannot start work on {issue.get_status_display().lower()} issues. Please reopen the issue first.')
            return redirect('issue_management:central_admin:issue_detail', issue_slug=issue.slug)
        
        if issue.status == 'in_progress':
            messages.info(request, 'Work is already in progress on this issue.')
            return redirect('issue_management:central_admin:issue_detail', issue_slug=issue.slug)
        
        try:
            # Store the previous status for the message
            previous_status = issue.get_status_display()
            
            # Change status to in_progress
            issue.status = 'in_progress'
            # Set the user who is starting work for activity tracking
            issue._changed_by = request.user
            issue.save()
            
            messages.success(request, f'Started work on issue "{issue.title}". Status changed from {previous_status.lower()} to in progress.')
            
        except Exception as e:
            messages.error(request, f'Failed to start work on issue: {str(e)}')
        
        # Redirect back to the issue detail page
        return redirect('issue_management:central_admin:issue_detail', issue_slug=issue.slug)


class SiteVisitCreateView(CentralAdminOnlyAccessMixin, CreateView):
    """Create a new site visit for an issue"""
    template_name = "central_admin/issue_management/site_visit_create.html"
    form_class = SiteVisitForm
    model = SiteVisit
    
    def dispatch(self, request, *args, **kwargs):
        # Get the issue this site visit belongs to
        self.issue = get_object_or_404(Issue, slug=kwargs['issue_slug'])
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['issue'] = self.issue
        return kwargs
    
    def form_valid(self, form):
        # Set the issue and created_by before saving
        form.instance.issue = self.issue
        form.instance.created_by = self.request.user
        
        # Save the site visit
        response = super().form_valid(form)
        
        messages.success(self.request, f'Site visit "{form.instance.title}" created successfully!')
        
        return response
    
    def get_success_url(self):
        return reverse_lazy('issue_management:central_admin:issue_detail', kwargs={'issue_slug': self.issue.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['issue'] = self.issue
        return context


class SiteVisitUpdateView(CentralAdminOnlyAccessMixin, UpdateView):
    """Update an existing site visit"""
    template_name = "central_admin/issue_management/site_visit_update.html"
    form_class = SiteVisitForm
    model = SiteVisit
    slug_field = 'slug'
    slug_url_kwarg = 'site_visit_slug'
    
    def dispatch(self, request, *args, **kwargs):
        # Get the site visit and its associated issue
        self.site_visit = get_object_or_404(SiteVisit, slug=kwargs['site_visit_slug'])
        self.issue = self.site_visit.issue
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['issue'] = self.issue
        return kwargs
    
    def form_valid(self, form):
        # Set the user who updated the site visit for activity tracking
        form.instance._changed_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Site visit "{form.instance.title}" updated successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('issue_management:central_admin:issue_detail', kwargs={'issue_slug': self.issue.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['issue'] = self.issue
        context['site_visit'] = self.site_visit
        return context


class SiteVisitDeleteView(CentralAdminOnlyAccessMixin, View):
    """Delete a site visit"""
    
    def post(self, request, site_visit_slug):
        site_visit = get_object_or_404(SiteVisit, slug=site_visit_slug)
        issue_slug = site_visit.issue.slug
        visit_title = site_visit.title
        
        # Delete all images associated with the site visit before deleting
        for image in site_visit.images.all():
            if image.image:
                image.image.delete(save=False)
            image.delete()
        
        site_visit.delete()
        messages.success(request, f'Site visit "{visit_title}" has been deleted.')
        
        return redirect('issue_management:central_admin:issue_detail', issue_slug=issue_slug)


class SiteVisitListView(CentralAdminOnlyAccessMixin, ListView):
    """List all site visits for central admin"""
    model = SiteVisit
    template_name = "central_admin/issue_management/site_visit_list.html"
    context_object_name = "site_visits"

    def get_queryset(self):
        # Get all site visits (central admin sees all)
        queryset = SiteVisit.objects.all().select_related(
            'issue', 'issue__org', 'issue__space', 'created_by', 'assigned_to'
        ).prefetch_related('images')
        
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


class SiteVisitDetailView(CentralAdminOnlyAccessMixin, DetailView):
    """View details of a specific site visit"""
    model = SiteVisit
    template_name = "central_admin/issue_management/site_visit_detail.html"
    context_object_name = "site_visit"
    slug_field = 'slug'
    slug_url_kwarg = 'site_visit_slug'
    
    def get_queryset(self):
        return SiteVisit.objects.select_related(
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


class PerformanceReportView(CentralAdminOnlyAccessMixin, View):
    """Generate and download PDF performance reports"""
    template_name = "central_admin/issue_management/performance_report.html"
    
    def get(self, request):
        """Display the report configuration form"""
        form = PerformanceReportForm(organization=request.user.organization)
        
        context = {
            'form': form,
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Generate and return the PDF report"""
        form = PerformanceReportForm(request.POST, organization=request.user.organization)
        
        if not form.is_valid():
            context = {
                'form': form,
            }
            return render(request, self.template_name, context)
        
        try:
            # Get date range from form
            start_date, end_date = form.get_date_range()
            
            # Get user filter (specific users or None for all)
            user_ids = form.get_user_filter()
            
            # Get role filters
            include_supervisors = form.cleaned_data.get('include_supervisors', True)
            include_maintainers = form.cleaned_data.get('include_maintainers', True)
            
            # Generate the report
            generator = PerformanceReportGenerator(
                organization=request.user.organization,
                start_date=start_date,
                end_date=end_date,
                user_ids=user_ids,
                include_supervisors=include_supervisors,
                include_maintainers=include_maintainers
            )
            
            pdf_buffer = generator.generate_report()
            
            # Create HTTP response with PDF
            response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
            
            # Generate filename with timestamp
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            filename = f"performance_report_{timestamp}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            messages.error(request, f'Failed to generate report: {str(e)}')
            context = {
                'form': form,
            }
            return render(request, self.template_name, context)


class PurchaseRequestListView(CentralAdminOnlyAccessMixin, ListView):
    """List all purchase requests for central admin"""
    model = PurchaseRequest
    template_name = "central_admin/issue_management/purchase_request_list.html"
    context_object_name = "purchase_requests"
    paginate_by = 20
    
    def get_queryset(self):
        queryset = PurchaseRequest.objects.select_related(
            'issue', 'issue__space', 'org', 'space', 'requested_by', 'reviewed_by'
        ).all()
        
        # Filter by status if provided
        status_filter = self.request.GET.get('status')
        if status_filter and status_filter in ['pending', 'approved', 'rejected']:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by space if provided
        space_filter = self.request.GET.get('space')
        if space_filter:
            queryset = queryset.filter(space__slug=space_filter)
        
        # Order by status (pending first), then by request date
        return queryset.annotate(
            status_order=Case(
                When(status='pending', then=1),
                When(status='approved', then=2),
                When(status='rejected', then=3),
                default=4,
                output_field=IntegerField(),
            )
        ).order_by('status_order', '-requested_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all spaces for filter dropdown
        context['spaces'] = Space.objects.filter(org=self.request.user.organization).order_by('name')
        
        # Get filter values
        context['current_status_filter'] = self.request.GET.get('status', '')
        context['current_space_filter'] = self.request.GET.get('space', '')
        
        # Get counts by status for display
        all_requests = PurchaseRequest.objects.filter(org=self.request.user.organization)
        context['pending_count'] = all_requests.filter(status='pending').count()
        context['approved_count'] = all_requests.filter(status='approved').count()
        context['rejected_count'] = all_requests.filter(status='rejected').count()
        
        return context


class PurchaseRequestDetailView(CentralAdminOnlyAccessMixin, DetailView):
    """View details of a specific purchase request"""
    model = PurchaseRequest
    template_name = "central_admin/issue_management/purchase_request_detail.html"
    context_object_name = "purchase_request"
    slug_field = 'slug'
    slug_url_kwarg = 'purchase_request_slug'
    
    def get_queryset(self):
        return PurchaseRequest.objects.select_related(
            'issue', 'issue__space', 'issue__reporter', 'org', 'space', 'requested_by', 'reviewed_by'
        ).prefetch_related('issue__images')


class PurchaseRequestApproveView(CentralAdminOnlyAccessMixin, View):
    """Approve a purchase request"""
    
    def post(self, request, purchase_request_slug):
        purchase_request = get_object_or_404(PurchaseRequest, slug=purchase_request_slug)
        
        # Get review notes from form
        review_notes = request.POST.get('review_notes', '')
        
        # Update purchase request
        purchase_request.status = 'approved'
        purchase_request.reviewed_by = request.user
        purchase_request.reviewed_at = timezone.now()
        purchase_request.review_notes = review_notes
        purchase_request.save()
        
        # Track activity
        IssueActivity.objects.create(
            issue=purchase_request.issue,
            activity_type='purchase_request_approved',
            user=request.user,
            description=f'Purchase request for "{purchase_request.item}" (Qty: {purchase_request.quantity}) approved{f" - ${purchase_request.estimated_amount}" if purchase_request.estimated_amount else ""}'
        )
        
        messages.success(request, f"Purchase request for '{purchase_request.item}' has been approved.")
        return redirect('issue_management:central_admin:purchase_request_detail', purchase_request_slug=purchase_request.slug)


class PurchaseRequestRejectView(CentralAdminOnlyAccessMixin, View):
    """Reject a purchase request"""
    
    def post(self, request, purchase_request_slug):
        purchase_request = get_object_or_404(PurchaseRequest, slug=purchase_request_slug)
        
        # Get review notes from form (required for rejection)
        review_notes = request.POST.get('review_notes', '')
        
        if not review_notes:
            messages.error(request, "Please provide a reason for rejecting this purchase request.")
            return redirect('issue_management:central_admin:purchase_request_detail', purchase_request_slug=purchase_request.slug)
        
        # Update purchase request
        purchase_request.status = 'rejected'
        purchase_request.reviewed_by = request.user
        purchase_request.reviewed_at = timezone.now()
        purchase_request.review_notes = review_notes
        purchase_request.save()
        
        # Track activity
        IssueActivity.objects.create(
            issue=purchase_request.issue,
            activity_type='purchase_request_rejected',
            user=request.user,
            description=f'Purchase request for "{purchase_request.item}" (Qty: {purchase_request.quantity}) rejected - Reason: {review_notes[:100]}'
        )
        
        messages.success(request, f"Purchase request for '{purchase_request.item}' has been rejected.")
        return redirect('issue_management:central_admin:purchase_request_detail', purchase_request_slug=purchase_request.slug)


class PurchaseRequestDeleteView(CentralAdminOnlyAccessMixin, View):
    """Delete a pending purchase request"""
    
    def post(self, request, purchase_request_slug):
        purchase_request = get_object_or_404(PurchaseRequest, slug=purchase_request_slug)
        
        # Only allow deletion if status is pending
        if purchase_request.status != 'pending':
            messages.error(request, "Only pending purchase requests can be deleted.")
            return redirect('issue_management:central_admin:purchase_request_detail', purchase_request_slug=purchase_request.slug)
        
        item_name = purchase_request.item
        issue_slug = purchase_request.issue.slug
        issue = purchase_request.issue
        
        # Track activity before deletion
        IssueActivity.objects.create(
            issue=issue,
            activity_type='purchase_request_deleted',
            user=request.user,
            description=f'Purchase request for "{item_name}" was deleted'
        )
        
        # Delete the purchase request
        purchase_request.delete()
        
        messages.success(request, f"Purchase request for '{item_name}' has been deleted.")
        return redirect('issue_management:central_admin:issue_detail', issue_slug=issue_slug)

