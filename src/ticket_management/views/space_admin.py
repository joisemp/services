from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Case, When, IntegerField
from ..models import Ticket, TicketImage, WorkTask, TicketComment, SiteVisit, SiteVisitImage, PurchaseRequest, TicketActivity
from ..forms import TicketForm, SpaceAdminTicketForm, WorkTaskForm, WorkTaskUpdateForm, WorkTaskCompleteForm, TicketCommentForm, AdditionalImageUploadForm, VoiceUploadForm, TicketUpdateForm, TicketAssignmentForm, SiteVisitForm, PurchaseRequestForm
from config.mixins.access_mixin import SpaceAdminOnlyAccessMixin, SpaceAdminWithActiveSpaceMixin

class TicketListView(SpaceAdminWithActiveSpaceMixin, ListView):
    template_name = "space_admin/ticket_management/ticket_list.html"
    context_object_name = "tickets"
    model = Ticket
    
    def get_queryset(self):
        queryset = Ticket.objects.prefetch_related('images').select_related('org', 'space', 'reporter').all()
        
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
    

class TicketCreateView(SpaceAdminWithActiveSpaceMixin, CreateView):
    template_name = "space_admin/ticket_management/ticket_create.html"
    form_class = SpaceAdminTicketForm
    success_url = reverse_lazy('ticket_management:space_admin:ticket_list')
    
    def get_form_kwargs(self):
        """Pass current_user and active_space to form"""
        kwargs = super().get_form_kwargs()
        kwargs['current_user'] = self.request.user
        kwargs['active_space'] = self.request.user.active_space if self.request.user.is_space_admin else None
        return kwargs
    
    def post(self, request, *args, **kwargs):
        """Override post to prevent duplicate submissions"""
        # Check if this form has already been submitted
        form_token = request.POST.get('form_token', '')
        if form_token:
            # Check if token was already used
            used_tokens = request.session.get('used_ticket_create_tokens', [])
            if form_token in used_tokens:
                messages.warning(request, 'This ticket has already been created. Please do not submit the form multiple times.')
                return redirect(self.success_url)
        
        return super().post(request, *args, **kwargs)
    
    def form_valid(self, form):
        # Set the reporter and space BEFORE saving the instance
        form.instance.reporter = self.request.user
        
        # Ensure active space is assigned before save
        if self.request.user.is_space_admin and self.request.user.active_space:
            form.instance.space = self.request.user.active_space
        
        # Ensure organization is set before save
        if self.request.user.organization:
            form.instance.org = self.request.user.organization
        
        # Now save the ticket (super().form_valid() calls form.save())
        response = super().form_valid(form)
        
        # Handle image uploads after the ticket is saved
        image_fields = ['image1', 'image2', 'image3']
        for field_name in image_fields:
            image_file = form.cleaned_data.get(field_name)
            if image_file:
                issue_image = TicketImage(
                    ticket=self.object,
                    image=image_file
                )
                # Set the user who uploaded the image for activity tracking
                issue_image._uploaded_by = self.request.user
                issue_image.save()
        
        # Mark this form as submitted to prevent duplicates
        form_token = self.request.POST.get('form_token', '')
        if form_token:
            used_tokens = self.request.session.get('used_ticket_create_tokens', [])
            used_tokens.append(form_token)
            # Keep only the last 10 tokens to prevent session bloat
            self.request.session['used_ticket_create_tokens'] = used_tokens[-10:]
        
        messages.success(self.request, f'Ticket "{self.object.title}" created successfully!')
        return response    


class TicketDetailView(SpaceAdminWithActiveSpaceMixin, DetailView):
    template_name = "space_admin/ticket_management/ticket_detail.html"
    context_object_name = "ticket"
    model = Ticket
    slug_field = 'slug'
    slug_url_kwarg = 'ticket_slug'
    
    def get_queryset(self):
        queryset = Ticket.objects.prefetch_related(
            'images', 
            'comments', 
            'work_tasks__assigned_to',
            'site_visits__created_by',
            'site_visits__assigned_to',
            'site_visits__images'
        ).select_related('org', 'space')
        
        # Filter by active space for space admins
        if self.request.user.is_space_admin and self.request.user.active_space:
            queryset = queryset.filter(space=self.request.user.active_space)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add work tasks to context sorted by completion status, then by ticket priority
        # Incomplete tasks first, ordered by ticket's priority (critical to low)
        issue_priority_order = Case(
            When(ticket__priority='critical', then=1),
            When(ticket__priority='high', then=2),
            When(ticket__priority='medium', then=3),
            When(ticket__priority='low', then=4),
            default=5,
            output_field=IntegerField(),
        )
        work_tasks = self.object.work_tasks.select_related('ticket').annotate(
            priority_order=issue_priority_order
        ).order_by('completed', 'priority_order', 'due_date')
        context['work_tasks'] = work_tasks
        # Check if there are any incomplete work tasks
        context['has_incomplete_tasks'] = work_tasks.filter(completed=False).exists()
        # Add comment form to context
        context['comment_form'] = TicketCommentForm()
        # Add site visits to context
        site_visits = self.object.site_visits.select_related('created_by', 'assigned_to').prefetch_related('images').all()
        context['site_visits'] = site_visits
        # Add purchase requests to context
        purchase_requests = self.object.purchase_requests.select_related('requested_by', 'reviewed_by').all()
        context['purchase_requests'] = purchase_requests
        # Add purchase request form to context
        context['purchase_request_form'] = PurchaseRequestForm()
        return context


class TicketImageDeleteView(SpaceAdminWithActiveSpaceMixin, View):
    """Delete a specific image attached to a ticket"""
    
    def post(self, request, ticket_slug, image_slug):
        # Get the ticket and image
        ticket= get_object_or_404(Ticket, slug=ticket_slug)
        image = get_object_or_404(TicketImage, slug=image_slug, ticket=ticket)
        
        # Store the image filename for the success message
        image_name = image.image.name
        
        # Delete the image file from storage
        if image.image:
            image.image.delete(save=False)
        
        # Delete the image record
        image.delete()
        
        messages.success(request, f'Image successfully deleted.')
        
        # Redirect back to the ticket detail page
        return redirect('ticket_management:space_admin:ticket_detail', ticket_slug=ticket.slug)


class TicketImageUploadView(SpaceAdminWithActiveSpaceMixin, View):
    """Upload additional images to an existing ticket"""
    
    def get(self, request, ticket_slug):
        # Get the ticket
        ticket= get_object_or_404(Ticket, slug=ticket_slug)
        form = AdditionalImageUploadForm()
        
        context = {
            'ticket': ticket,
            'form': form,
        }
        return render(request, 'space_admin/ticket_management/image_upload.html', context)
    
    def post(self, request, ticket_slug):
        # Get the ticket
        ticket= get_object_or_404(Ticket, slug=ticket_slug)
        form = AdditionalImageUploadForm(request.POST, request.FILES)
        
        if form.is_valid():
            # Get the list of uploaded images from cleaned_data
            images = form.cleaned_data.get('images')
            uploaded_count = 0
            
            # Ensure images is a list
            if not isinstance(images, list):
                images = [images] if images else []
            
            # Create TicketImage instances for each uploaded image
            for image_file in images:
                try:
                    TicketImage.objects.create(
                        ticket=ticket,
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
                
                # Redirect back to the ticket detail page
                return redirect('ticket_management:space_admin:ticket_detail', ticket_slug=ticket.slug)
        
        # If form is not valid, show errors
        context = {
            'ticket': ticket,
            'form': form,
        }
        return render(request, 'space_admin/ticket_management/image_upload.html', context)


class TicketVoiceDeleteView(SpaceAdminWithActiveSpaceMixin, View):
    """Delete the voice recording attached to a ticket"""
    
    def post(self, request, ticket_slug):
        # Get the ticket
        ticket= get_object_or_404(Ticket, slug=ticket_slug)
        
        # Check if ticket has a voice recording
        if not ticket.voice:
            messages.error(request, 'No voice recording found for this ticket.')
            return redirect('ticket_management:space_admin:ticket_detail', ticket_slug=ticket.slug)
        
        # Delete the voice file from storage
        if ticket.voice:
            ticket.voice.delete(save=False)
        
        # Clear the voice field and save the ticket
        ticket.voice = None
        ticket.save()
        
        messages.success(request, 'Voice recording successfully deleted.')
        
        # Redirect back to the ticket detail page
        return redirect('ticket_management:space_admin:ticket_detail', ticket_slug=ticket.slug)


class TicketVoiceUploadView(SpaceAdminWithActiveSpaceMixin, View):
    """Upload a voice recording to an existing ticket"""
    
    def get(self, request, ticket_slug):
        # Get the ticket
        ticket= get_object_or_404(Ticket, slug=ticket_slug)
        
        # Check if ticket already has a voice recording
        if ticket.voice:
            messages.error(request, 'This ticket already has a voice recording. Delete it first to upload a new one.')
            return redirect('ticket_management:space_admin:ticket_detail', ticket_slug=ticket.slug)
        
        form = VoiceUploadForm()
        
        context = {
            'ticket': ticket,
            'form': form,
        }
        return render(request, 'space_admin/ticket_management/voice_upload.html', context)
    
    def post(self, request, ticket_slug):
        # Get the ticket
        ticket= get_object_or_404(Ticket, slug=ticket_slug)
        
        # Check if ticket already has a voice recording
        if ticket.voice:
            messages.error(request, 'This ticket already has a voice recording. Delete it first to upload a new one.')
            return redirect('ticket_management:space_admin:ticket_detail', ticket_slug=ticket.slug)
        
        form = VoiceUploadForm(request.POST, request.FILES)
        
        if form.is_valid():
            # Get the voice file from cleaned_data
            voice_file = form.cleaned_data.get('voice')
            
            if voice_file:
                try:
                    # Save the voice file to the ticket
                    ticket.voice = voice_file
                    ticket.save()
                    
                    messages.success(request, 'Voice recording successfully uploaded.')
                    return redirect('ticket_management:space_admin:ticket_detail', ticket_slug=ticket.slug)
                    
                except Exception as e:
                    messages.error(request, f'Failed to upload voice recording: {str(e)}')
        
        # If form is not valid, show errors
        context = {
            'ticket': ticket,
            'form': form,
        }
        return render(request, 'space_admin/ticket_management/voice_upload.html', context)


class TicketResolveView(SpaceAdminWithActiveSpaceMixin, View):
    """Mark a ticket as resolved with resolution notes and images"""
    
    def post(self, request, ticket_slug):
        from ..models import TicketResolutionImage
        from ..forms import TicketResolveForm
        
        # Get the ticket
        ticket= get_object_or_404(Ticket, slug=ticket_slug)
        
        # Check if ticket is already resolved, closed, or cancelled
        if ticket.status in ['resolved', 'closed', 'cancelled']:
            messages.error(request, f'This ticket is already {ticket.get_status_display().lower()} and cannot be resolved again.')
            return redirect('ticket_management:space_admin:ticket_detail', ticket_slug=ticket.slug)
        
        # Check if there are any incomplete work tasks
        incomplete_tasks = ticket.work_tasks.filter(completed=False)
        if incomplete_tasks.exists():
            incomplete_count = incomplete_tasks.count()
            task_word = 'task' if incomplete_count == 1 else 'tasks'
            messages.error(request, f'Cannot resolve ticket while {incomplete_count} work {task_word} remain incomplete. Please complete all work tasks before marking the ticket as resolved.')
            return redirect('ticket_management:space_admin:ticket_detail', ticket_slug=ticket.slug)
        
        # Process the form
        form = TicketResolveForm(request.POST, request.FILES, instance=ticket)
        
        if not form.is_valid():
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
            return redirect('ticket_management:space_admin:ticket_detail', ticket_slug=ticket.slug)
        
        try:
            # Update the ticket status and resolution notes
            ticket.status = 'resolved'
            ticket.resolution_notes = form.cleaned_data['resolution_notes']
            ticket.save()
            
            # Handle resolution images (up to 3)
            image_count = 0
            for i in range(1, 4):
                image_field = f'image{i}'
                image = form.cleaned_data.get(image_field)
                if image:
                    TicketResolutionImage.objects.create(
                        ticket=ticket,
                        image=image
                    )
                    image_count += 1
            
            if image_count > 0:
                messages.success(request, f'Ticket "{ticket.title}" has been successfully marked as resolved with {image_count} resolution image(s).')
            else:
                messages.success(request, f'Ticket "{ticket.title}" has been successfully marked as resolved.')
            
        except Exception as e:
            messages.error(request, f'Failed to resolve ticket: {str(e)}')
        
        # Redirect back to the ticket detail page
        return redirect('ticket_management:space_admin:ticket_detail', ticket_slug=ticket.slug)


class TicketUpdateView(SpaceAdminWithActiveSpaceMixin, UpdateView):
    template_name = "space_admin/ticket_management/ticket_update.html"
    form_class = TicketUpdateForm
    model = Ticket
    slug_field = 'slug'
    slug_url_kwarg = 'ticket_slug'
    
    def get_queryset(self):
        return Ticket.objects.prefetch_related('images').select_related('org', 'space', 'reporter')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Ticket "{form.instance.title}" updated successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('ticket_management:space_admin:ticket_detail', kwargs={'ticket_slug': self.object.slug})


class WorkTaskCreateView(SpaceAdminWithActiveSpaceMixin, CreateView):
    template_name = "space_admin/ticket_management/work_task_create.html"
    form_class = WorkTaskForm
    model = WorkTask
    
    def dispatch(self, request, *args, **kwargs):
        # Get the ticket this work task belongs to
        self.ticket = get_object_or_404(Ticket, slug=kwargs['ticket_slug'])
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['ticket'] = self.ticket
        return kwargs
    
    def form_valid(self, form):
        # Set the ticket before saving
        form.instance.ticket = self.ticket
        response = super().form_valid(form)
        messages.success(self.request, f'Work task "{form.instance.title}" created successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('ticket_management:space_admin:ticket_detail', kwargs={'ticket_slug': self.ticket.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ticket'] = self.ticket
        return context


class WorkTaskUpdateView(SpaceAdminWithActiveSpaceMixin, UpdateView):
    template_name = "space_admin/ticket_management/work_task_update.html"
    form_class = WorkTaskUpdateForm
    model = WorkTask
    slug_field = 'slug'
    slug_url_kwarg = 'work_task_slug'
    
    def dispatch(self, request, *args, **kwargs):
        # Get the work task and its associated ticket
        self.work_task = get_object_or_404(WorkTask, slug=kwargs['work_task_slug'])
        self.ticket = self.work_task.ticket
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['ticket'] = self.ticket
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Work task "{form.instance.title}" updated successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('ticket_management:space_admin:ticket_detail', kwargs={'ticket_slug': self.ticket.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ticket'] = self.ticket
        context['work_task'] = self.work_task
        return context


class WorkTaskCompleteView(SpaceAdminWithActiveSpaceMixin, UpdateView):
    """Complete a work task with resolution notes and images"""
    template_name = "space_admin/ticket_management/work_task_complete.html"
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
        return reverse_lazy('ticket_management:space_admin:ticket_detail', kwargs={'ticket_slug': self.work_task.ticket.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['work_task'] = self.work_task
        context['ticket'] = self.work_task.ticket
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
        
        return redirect('ticket_management:space_admin:ticket_detail', ticket_slug=self.work_task.ticket.slug)


class WorkTaskDeleteView(SpaceAdminWithActiveSpaceMixin, View):
    """Delete a work task and its resolution images"""
    
    def post(self, request, work_task_slug):
        from ..models import WorkTaskResolutionImage
        
        work_task = get_object_or_404(WorkTask, slug=work_task_slug)
        ticket_slug = work_task.ticket.slug
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
        
        return redirect('ticket_management:space_admin:ticket_detail', ticket_slug=ticket_slug)


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
        
        # Redirect back to the ticket detail page
        return redirect('ticket_management:space_admin:ticket_detail', ticket_slug=work_task.ticket.slug)


class TicketDeleteView(SpaceAdminWithActiveSpaceMixin, DeleteView):
    """Delete a ticket and all its related data"""
    template_name = "space_admin/ticket_management/ticket_delete.html"
    model = Ticket
    slug_field = 'slug'
    slug_url_kwarg = 'ticket_slug'
    success_url = reverse_lazy('ticket_management:space_admin:ticket_list')
    
    def get_queryset(self):
        return Ticket.objects.prefetch_related('images', 'comments', 'work_tasks__shares').select_related('org', 'space', 'reporter')
    
    def delete(self, request, *args, **kwargs):
        """Override delete to add success message"""
        self.object = self.get_object()
        ticket_title = self.object.title
        
        # Django's CASCADE will automatically delete:
        # - TicketImage instances (related via images)
        # - TicketComment instances (related via comments) 
        # - WorkTask instances (related via work_tasks)
        # - WorkTaskShare instances (related via work_tasks__shares)
        
        success_url = self.get_success_url()
        self.object.delete()
        
        messages.success(request, f'Ticket "{ticket_title}" and all its related data have been permanently deleted.')
        
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


class TicketAssignmentView(SpaceAdminWithActiveSpaceMixin, UpdateView):
    """Assign a ticket to a supervisor with optional review requirement"""
    template_name = "space_admin/ticket_management/ticket_assignment.html"
    form_class = TicketAssignmentForm
    model = Ticket
    slug_field = 'slug'
    slug_url_kwarg = 'ticket_slug'
    
    def dispatch(self, request, *args, **kwargs):
        self.ticket = get_object_or_404(Ticket, slug=kwargs['ticket_slug'])
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['ticket'] = self.ticket
        return kwargs
    
    def form_valid(self, form):
        # Set assignment metadata
        form.instance.assigned_by = self.request.user
        form.instance.assigned_at = timezone.now()
        
        # Update status to assigned when a supervisor is assigned
        # Only change status if it's not already resolved, closed, or cancelled
        if form.instance.status not in ['resolved', 'closed', 'cancelled']:
            form.instance.status = 'assigned'
        
        # Save the form first (this saves the Ticket instance)
        response = super().form_valid(form)
        
        # Check if review is required
        if form.instance.requires_review:
            # Redirect to reviewer selection page (Step 2)
            messages.info(
                self.request,
                'Ticket assigned successfully. Now please select reviewers for this ticket.'
            )
            return redirect('ticket_management:space_admin:ticket_select_reviewers', ticket_slug=self.object.slug)
        else:
            # No review required, clear any existing reviewers and show success message
            self.object.reviewers.clear()
            
            assigned_to_name = form.instance.assigned_to.get_full_name() or form.instance.assigned_to.email
            
            messages.success(
                self.request, 
                f'Ticket "{form.instance.title}" has been assigned to {assigned_to_name}.'
            )
            
            return response
    
    def get_success_url(self):
        return reverse_lazy('ticket_management:space_admin:ticket_detail', kwargs={'ticket_slug': self.ticket.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ticket'] = self.ticket
        return context


class TicketReviewerSelectionView(SpaceAdminWithActiveSpaceMixin, View):
    """Select reviewers for a ticket that requires review (Step 2 after assignment)"""
    template_name = "space_admin/ticket_management/ticket_reviewer_selection.html"
    
    def dispatch(self, request, *args, **kwargs):
        self.ticket = get_object_or_404(Ticket, slug=kwargs['ticket_slug'])
        
        # Redirect if ticket doesn't require review
        if not self.ticket.requires_review:
            messages.warning(request, 'This ticket does not require review.')
            return redirect('ticket_management:space_admin:ticket_detail', ticket_slug=self.ticket.slug)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, ticket_slug):
        from ..forms import TicketReviewerSelectionForm
        form = TicketReviewerSelectionForm(ticket=self.ticket)
        return render(request, self.template_name, {
            'form': form,
            'ticket': self.ticket
        })
    
    def post(self, request, ticket_slug):
        from ..forms import TicketReviewerSelectionForm
        form = TicketReviewerSelectionForm(request.POST, ticket=self.ticket)
        
        if form.is_valid():
            # Save the selected reviewers
            reviewers = form.cleaned_data['reviewers']
            self.ticket.reviewers.set(reviewers)
            
            # Create success message with reviewer names
            reviewer_names = ", ".join([r.get_full_name() or r.email for r in reviewers])
            assigned_to_name = self.ticket.assigned_to.get_full_name() or self.ticket.assigned_to.email
            
            messages.success(
                request,
                f'Ticket "{self.ticket.title}" has been assigned to {assigned_to_name} with review required by: {reviewer_names}.'
            )
            
            return redirect('ticket_management:space_admin:ticket_detail', ticket_slug=self.ticket.slug)
        
        return render(request, self.template_name, {
            'form': form,
            'ticket': self.ticket
        })


class TicketReopenView(SpaceAdminWithActiveSpaceMixin, View):
    """Reopen a resolved, closed, or cancelled ticket"""
    
    def post(self, request, ticket_slug):
        # Get the ticket
        ticket= get_object_or_404(Ticket, slug=ticket_slug)
        
        # Check if ticket can be reopened
        if ticket.status not in ['resolved', 'closed', 'cancelled']:
            messages.error(request, f'Only resolved, closed, or cancelled issues can be reopened. This ticket is currently {ticket.get_status_display().lower()}.')
            return redirect('ticket_management:space_admin:ticket_detail', ticket_slug=ticket.slug)
        
        try:
            # Store the previous status for the message
            previous_status = ticket.get_status_display()
            
            # Reopen the ticket
            if ticket.assigned_to:
                ticket.status = 'assigned'
            else:
                ticket.status = 'open'
            
            # Clear resolution notes when reopening
            ticket.resolution_notes = None
            
            # Delete all resolution images
            ticket.resolution_images.all().delete()
            
            # Clear review information when reopening
            ticket.reviewed_by = None
            ticket.reviewed_at = None
            ticket.review_notes = None
            
            ticket.save()
            
            messages.success(request, f'Ticket "{ticket.title}" has been reopened from {previous_status.lower()} status.')
            
        except Exception as e:
            messages.error(request, f'Failed to reopen ticket: {str(e)}')
        
        # Redirect back to the ticket detail page
        return redirect('ticket_management:space_admin:ticket_detail', ticket_slug=ticket.slug)


class TicketStartWorkView(SpaceAdminWithActiveSpaceMixin, View):
    """Start work on a ticket by changing its status to in_progress"""
    
    def post(self, request, ticket_slug):
        # Get the ticket
        ticket= get_object_or_404(Ticket, slug=ticket_slug)
        
        # Check if ticket can be started
        if ticket.status in ['resolved', 'closed', 'cancelled']:
            messages.error(request, f'Cannot start work on {ticket.get_status_display().lower()} issues. Please reopen the ticket first.')
            return redirect('ticket_management:space_admin:ticket_detail', ticket_slug=ticket.slug)
        
        if ticket.status == 'in_progress':
            messages.info(request, 'Work is already in progress on this ticket.')
            return redirect('ticket_management:space_admin:ticket_detail', ticket_slug=ticket.slug)
        
        try:
            # Store the previous status for the message
            previous_status = ticket.get_status_display()
            
            # Change status to in_progress
            ticket.status = 'in_progress'
            ticket.save()
            
            messages.success(request, f'Started work on ticket "{ticket.title}". Status changed from {previous_status.lower()} to in progress.')
            
        except Exception as e:
            messages.error(request, f'Failed to start work on ticket: {str(e)}')
        
        # Redirect back to the ticket detail page
        return redirect('ticket_management:space_admin:ticket_detail', ticket_slug=ticket.slug)


class SiteVisitCreateView(SpaceAdminWithActiveSpaceMixin, CreateView):
    """Create a new site visit for a ticket"""
    template_name = "space_admin/ticket_management/site_visit_create.html"
    form_class = SiteVisitForm
    model = SiteVisit
    
    def dispatch(self, request, *args, **kwargs):
        # Get the ticket this site visit belongs to
        self.ticket = get_object_or_404(Ticket, slug=kwargs['ticket_slug'])
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['ticket'] = self.ticket
        return kwargs
    
    def form_valid(self, form):
        # Set the ticket and created_by before saving
        form.instance.ticket = self.ticket
        form.instance.created_by = self.request.user
        
        # Save the site visit
        response = super().form_valid(form)
        
        messages.success(self.request, f'Site visit "{form.instance.title}" created successfully!')
        
        return response
    
    def get_success_url(self):
        return reverse_lazy('ticket_management:space_admin:ticket_detail', kwargs={'ticket_slug': self.ticket.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ticket'] = self.ticket
        return context


class SiteVisitUpdateView(SpaceAdminWithActiveSpaceMixin, UpdateView):
    """Update an existing site visit"""
    template_name = "space_admin/ticket_management/site_visit_update.html"
    form_class = SiteVisitForm
    model = SiteVisit
    slug_field = 'slug'
    slug_url_kwarg = 'site_visit_slug'
    
    def dispatch(self, request, *args, **kwargs):
        # Get the site visit and its associated ticket
        self.site_visit = get_object_or_404(SiteVisit, slug=kwargs['site_visit_slug'])
        self.ticket = self.site_visit.ticket
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['ticket'] = self.ticket
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Site visit "{form.instance.title}" updated successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('ticket_management:space_admin:ticket_detail', kwargs={'ticket_slug': self.ticket.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ticket'] = self.ticket
        context['site_visit'] = self.site_visit
        return context


class SiteVisitDeleteView(SpaceAdminWithActiveSpaceMixin, View):
    """Delete a site visit"""
    
    def post(self, request, site_visit_slug):
        site_visit = get_object_or_404(SiteVisit, slug=site_visit_slug)
        ticket_slug = site_visit.ticket.slug
        visit_title = site_visit.title
        
        # Delete all images associated with the site visit before deleting
        for image in site_visit.images.all():
            if image.image:
                image.image.delete(save=False)
            image.delete()
        
        site_visit.delete()
        messages.success(request, f'Site visit "{visit_title}" has been deleted.')
        
        return redirect('ticket_management:space_admin:ticket_detail', ticket_slug=ticket_slug)


class SiteVisitListView(SpaceAdminWithActiveSpaceMixin, ListView):
    """List all site visits for space admin"""
    model = SiteVisit
    template_name = "space_admin/ticket_management/site_visit_list.html"
    context_object_name = "site_visits"

    def get_queryset(self):
        # Get site visits for issues in the active space
        queryset = SiteVisit.objects.all().select_related(
            'ticket', 'ticket__org', 'ticket__space', 'created_by', 'assigned_to'
        ).prefetch_related('images')
        
        # Filter by active space
        if self.request.user.active_space:
            queryset = queryset.filter(ticket__space=self.request.user.active_space)
        
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


class SiteVisitDetailView(SpaceAdminWithActiveSpaceMixin, DetailView):
    """View details of a specific site visit"""
    model = SiteVisit
    template_name = "space_admin/ticket_management/site_visit_detail.html"
    context_object_name = "site_visit"
    slug_field = 'slug'
    slug_url_kwarg = 'site_visit_slug'
    
    def get_queryset(self):
        queryset = SiteVisit.objects.select_related(
            'ticket',
            'ticket__org',
            'ticket__space',
            'ticket__reporter',
            'created_by',
            'assigned_to'
        ).prefetch_related('images', 'ticket__images')
        
        # Filter by active space
        if self.request.user.active_space:
            queryset = queryset.filter(ticket__space=self.request.user.active_space)
        
        return queryset


class PurchaseRequestCreateView(SpaceAdminWithActiveSpaceMixin, CreateView):
    """Create a purchase request for a ticket"""
    model = PurchaseRequest
    form_class = PurchaseRequestForm
    template_name = "space_admin/ticket_management/purchase_request_create.html"
    
    def dispatch(self, request, *args, **kwargs):
        # Get the ticket
        self.ticket = get_object_or_404(Ticket, slug=self.kwargs['ticket_slug'])
        
        # Ensure ticket belongs to space admin's active space
        if request.user.active_space and self.ticket.space != request.user.active_space:
            messages.error(request, "You don't have permission to create purchase requests for this ticket.")
            return redirect('ticket_management:space_admin:ticket_detail', ticket_slug=self.ticket.slug)
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        purchase_request = form.save(commit=False)
        purchase_request.ticket = self.ticket
        purchase_request.org = self.request.user.organization
        purchase_request.space = self.request.user.active_space
        purchase_request.requested_by = self.request.user
        purchase_request.save()
        
        # Track activity
        TicketActivity.objects.create(
            ticket=self.ticket,
            activity_type='purchase_request_created',
            user=self.request.user,
            description=f'Purchase request for "{purchase_request.item}" (Qty: {purchase_request.quantity}) created{f" - Estimated: ${purchase_request.estimated_amount}" if purchase_request.estimated_amount else ""}'
        )
        
        messages.success(self.request, f"Purchase request for '{purchase_request.item}' has been created successfully.")
        return redirect('ticket_management:space_admin:ticket_detail', ticket_slug=self.ticket.slug)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ticket'] = self.ticket
        return context
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ticket'] = self.object.ticket
        return context

class PurchaseRequestDeleteView(SpaceAdminWithActiveSpaceMixin, View):
    """Delete a pending purchase request"""
    
    def post(self, request, purchase_request_slug):
        purchase_request = get_object_or_404(PurchaseRequest, slug=purchase_request_slug)
        
        # Ensure purchase request belongs to space admin's active space
        if request.user.active_space and purchase_request.space != request.user.active_space:
            messages.error(request, "You don't have permission to delete this purchase request.")
            return redirect('ticket_management:space_admin:ticket_detail', ticket_slug=purchase_request.ticket.slug)
        
        # Only allow deletion if status is pending
        if purchase_request.status != 'pending':
            messages.error(request, "Only pending purchase requests can be deleted.")
            return redirect('ticket_management:space_admin:ticket_detail', ticket_slug=purchase_request.ticket.slug)
        
        item_name = purchase_request.item
        ticket_slug = purchase_request.ticket.slug
        ticket= purchase_request.ticket
        
        # Track activity before deletion
        TicketActivity.objects.create(
            ticket=ticket,
            activity_type='purchase_request_deleted',
            user=request.user,
            description=f'Purchase request for "{item_name}" was deleted'
        )
        
        # Delete the purchase request
        purchase_request.delete()
        
        messages.success(request, f"Purchase request for '{item_name}' has been deleted.")
        return redirect('ticket_management:space_admin:ticket_detail', ticket_slug=ticket_slug)
