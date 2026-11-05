from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Case, When, IntegerField
from ..models import Ticket, TicketImage, WorkTask, TicketComment, SiteVisit, SiteVisitImage, PurchaseRequest, TicketActivity
from ..forms import TicketForm, WorkTaskForm, WorkTaskUpdateForm, WorkTaskCompleteForm, TicketCommentForm, AdditionalImageUploadForm, VoiceUploadForm, TicketUpdateForm, TicketAssignmentForm, SiteVisitForm
from ..forms_reports import PerformanceReportForm
from ..utils.performance_report import PerformanceReportGenerator
from ..utils.ticket_filters import apply_ticket_list_filters, annotate_and_order, describe_filters
from ..utils.ticket_list_report import build_ticket_list_excel, build_ticket_list_pdf
from config.mixins.access_mixin import TicketManagementStaffAccessMixin as CentralAdminOnlyAccessMixin
from core.models import Space
from fleet_management.models import Vehicle
from fleet_management.models import Workshop


class TicketListView(CentralAdminOnlyAccessMixin, ListView):
    template_name = "central_admin/ticket_management/ticket_list.html"
    context_object_name = "tickets"
    model = Ticket
    
    def get_queryset(self):
        queryset = Ticket.objects.prefetch_related('images').select_related('org', 'space', 'reporter', 'assigned_to', 'vehicle', 'workshop').all()

        queryset = apply_ticket_list_filters(
            queryset,
            status_filter=self.request.GET.get('status'),
            space_filter=self.request.GET.get('space'),
            reporter_filter=self.request.GET.get('reporter'),
            assignee_filter=self.request.GET.get('assignee'),
        )

        return annotate_and_order(queryset)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_filter'] = self.request.GET.get('status', 'all')
        context['space_filter'] = self.request.GET.get('space', '')
        # Get all spaces for the filter dropdown
        context['spaces'] = Space.objects.select_related('org').all().order_by('org__name', 'name')
        return context


class VehicleTicketListView(CentralAdminOnlyAccessMixin, ListView):
    """List issues for a specific vehicle"""
    template_name = "central_admin/ticket_management/vehicle_ticket_list.html"
    context_object_name = "tickets"

    def dispatch(self, request, *args, **kwargs):
        self.vehicle = get_object_or_404(Vehicle, slug=kwargs.get('vehicle_slug'))
        # Ensure organization scoping
        if request.user.organization and self.vehicle.org != request.user.organization:
            return redirect(reverse('ticket_management:central_admin:ticket_list'))
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.vehicle.tickets.prefetch_related('images').select_related('reporter', 'assigned_to', 'org').all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['vehicle'] = self.vehicle
        return context


class TicketWorkshopTransferView(CentralAdminOnlyAccessMixin, UpdateView):
    """Allow transferring a ticket to a different workshop."""
    model = Ticket
    slug_field = 'slug'
    slug_url_kwarg = 'ticket_slug'
    fields = ['workshop']
    template_name = 'central_admin/ticket_management/ticket_change_workshop.html'

    def get_queryset(self):
        return Ticket.objects.select_related('org', 'vehicle').all()

    def form_valid(self, form):
        # Track who changed the workshop
        form.instance._changed_by = self.request.user
        old_workshop = None
        if self.object and self.object.workshop:
            old_workshop = self.object.workshop
        response = super().form_valid(form)
        # Log activity
        try:
            TicketActivity.objects.create(
                ticket=self.object,
                activity_type='workshop_changed',
                user=self.request.user,
                description=f'Workshop changed from {old_workshop.name if old_workshop else "None"} to {self.object.workshop.name if self.object.workshop else "None"}'
            )
        except Exception:
            pass
        messages.success(self.request, 'Workshop assignment updated.')
        return response

    def get_success_url(self):
        return reverse_lazy('ticket_management:central_admin:ticket_detail', kwargs={'ticket_slug': self.object.slug})

    
class TicketCreateView(CentralAdminOnlyAccessMixin, CreateView):
    template_name = "central_admin/ticket_management/ticket_create.html"
    form_class = TicketForm
    success_url = reverse_lazy('ticket_management:central_admin:ticket_list')

    def _get_vehicle_from_query(self):
        vehicle_slug = self.request.GET.get('vehicle')
        if not vehicle_slug or not self.request.user.organization:
            return None

        try:
            return Vehicle.objects.get(slug=vehicle_slug, org=self.request.user.organization)
        except Vehicle.DoesNotExist:
            return None
    
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

        vehicle = self._get_vehicle_from_query()
        self.vehicle_context = vehicle

        if 'vehicle' in form.fields:
            form.fields['vehicle'].required = False
            form.fields['vehicle'].queryset = Vehicle.objects.filter(
                org=self.request.user.organization
            ).order_by('registration_number')
            if vehicle:
                form.initial['vehicle'] = vehicle.pk

        if 'workshop' in form.fields:
            form.fields['workshop'].required = bool(vehicle)
            form.fields['workshop'].queryset = Workshop.objects.filter(
                org=self.request.user.organization
            ).order_by('name')
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['show_workshop_field'] = bool(self._get_vehicle_from_query())
        return context
    
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
        # Set the reporter to the current user before saving
        form.instance.reporter = self.request.user
        vehicle = self._get_vehicle_from_query()
        if vehicle:
            form.instance.vehicle = vehicle
        
        # Save the ticket first
        response = super().form_valid(form)
        
        # Handle image uploads
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
    

class TicketDetailView(CentralAdminOnlyAccessMixin, DetailView):
    template_name = "central_admin/ticket_management/ticket_detail.html"
    context_object_name = "ticket"
    model = Ticket
    slug_field = 'slug'
    slug_url_kwarg = 'ticket_slug'
    
    def get_queryset(self):
        return Ticket.objects.prefetch_related(
            'images', 
            'comments', 
            'work_tasks__assigned_to',
            'work_tasks__resolution_images',
            'site_visits__created_by',
            'site_visits__assigned_to',
            'site_visits__images',
            'activities__user',
            'purchase_requests__requested_by',
            'purchase_requests__reviewed_by',
        ).select_related('org', 'space', 'reporter', 'assigned_to', 'assigned_by', 'reviewed_by', 'vehicle', 'workshop')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sidebar_template'] = 'central_admin/sidebar.html'
        context['back_url'] = reverse('ticket_management:central_admin:ticket_list')
        # Add work tasks to context sorted by completion status and ticket priority
        work_tasks = self.object.work_tasks.select_related('ticket').prefetch_related('resolution_images').all().annotate(
            priority_order=Case(
                When(ticket__priority='critical', then=1),
                When(ticket__priority='high', then=2),
                When(ticket__priority='medium', then=3),
                When(ticket__priority='low', then=4),
                default=5,
                output_field=IntegerField(),
            )
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
        # Add activity history to context
        activities = self.object.activities.select_related('user').all()
        context['activities'] = activities
        return context
    
    
class TicketUpdateView(CentralAdminOnlyAccessMixin, UpdateView):
    template_name = "central_admin/ticket_management/ticket_update.html"
    form_class = TicketUpdateForm
    model = Ticket
    slug_field = 'slug'
    slug_url_kwarg = 'ticket_slug'
    
    def get_queryset(self):
        return Ticket.objects.prefetch_related('images').select_related('org', 'space', 'reporter')
    
    def form_valid(self, form):
        # Set the user who updated the ticket for activity tracking
        form.instance._changed_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Ticket "{form.instance.title}" updated successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('ticket_management:central_admin:ticket_detail', kwargs={'ticket_slug': self.object.slug})


class WorkTaskCreateView(CentralAdminOnlyAccessMixin, CreateView):
    template_name = "central_admin/ticket_management/work_task_create.html"
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
        # Set the user who created the task for activity tracking
        form.instance._created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Work task "{form.instance.title}" created successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('ticket_management:central_admin:ticket_detail', kwargs={'ticket_slug': self.ticket.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ticket'] = self.ticket
        return context


class WorkTaskUpdateView(CentralAdminOnlyAccessMixin, UpdateView):
    template_name = "central_admin/ticket_management/work_task_update.html"
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
        # Set the user who updated the task for activity tracking
        form.instance._changed_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Work task "{form.instance.title}" updated successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('ticket_management:central_admin:ticket_detail', kwargs={'ticket_slug': self.ticket.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ticket'] = self.ticket
        context['work_task'] = self.work_task
        return context


class WorkTaskCompleteView(CentralAdminOnlyAccessMixin, UpdateView):
    """Complete a work task with resolution notes and images"""
    template_name = "central_admin/ticket_management/work_task_complete.html"
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
        return reverse_lazy('ticket_management:central_admin:ticket_detail', kwargs={'ticket_slug': self.work_task.ticket.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['work_task'] = self.work_task
        context['ticket'] = self.work_task.ticket
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
        
        return redirect('ticket_management:central_admin:ticket_detail', ticket_slug=self.work_task.ticket.slug)


class WorkTaskDeleteView(CentralAdminOnlyAccessMixin, View):
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
        
        # Set the user who deleted the task for activity tracking
        work_task._deleted_by = request.user
        work_task.delete()
        messages.success(request, f'Work task "{task_title}" has been deleted.')
        
        return redirect('ticket_management:central_admin:ticket_detail', ticket_slug=ticket_slug)


class TicketDeleteView(CentralAdminOnlyAccessMixin, DeleteView):
    """Delete a ticket and all its related data"""
    template_name = "central_admin/ticket_management/ticket_delete.html"
    model = Ticket
    slug_field = 'slug'
    slug_url_kwarg = 'ticket_slug'
    success_url = reverse_lazy('ticket_management:central_admin:ticket_list')
    
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


class TicketImageDeleteView(CentralAdminOnlyAccessMixin, View):
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
        
        # Set the user who deleted the image for activity tracking
        image._deleted_by = request.user
        # Delete the image record
        image.delete()
        
        messages.success(request, f'Image successfully deleted.')
        
        # Redirect back to the ticket detail page
        return redirect('ticket_management:central_admin:ticket_detail', ticket_slug=ticket.slug)


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
        
        # Redirect back to the ticket detail page
        return redirect('ticket_management:central_admin:ticket_detail', ticket_slug=work_task.ticket.slug)


class TicketImageUploadView(CentralAdminOnlyAccessMixin, View):
    """Upload additional images to an existing ticket"""
    
    def get(self, request, ticket_slug):
        # Get the ticket
        ticket= get_object_or_404(Ticket, slug=ticket_slug)
        form = AdditionalImageUploadForm()
        
        context = {
            'ticket': ticket,
            'form': form,
        }
        return render(request, 'central_admin/ticket_management/image_upload.html', context)
    
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
                    issue_image = TicketImage(
                        ticket=ticket,
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
                
                # Redirect back to the ticket detail page
                return redirect('ticket_management:central_admin:ticket_detail', ticket_slug=ticket.slug)
        
        # If form is not valid, show errors
        context = {
            'ticket': ticket,
            'form': form,
        }
        return render(request, 'central_admin/ticket_management/image_upload.html', context)


class TicketVoiceDeleteView(CentralAdminOnlyAccessMixin, View):
    """Delete the voice recording attached to a ticket"""
    
    def post(self, request, ticket_slug):
        # Get the ticket
        ticket= get_object_or_404(Ticket, slug=ticket_slug)
        
        # Check if ticket has a voice recording
        if not ticket.voice:
            messages.error(request, 'No voice recording found for this ticket.')
            return redirect('ticket_management:central_admin:ticket_detail', ticket_slug=ticket.slug)
        
        # Delete the voice file from storage
        if ticket.voice:
            ticket.voice.delete(save=False)
        
        # Clear the voice field and save the ticket
        ticket.voice = None
        # Set the user who deleted the voice for activity tracking
        ticket._changed_by = request.user
        ticket.save()
        
        messages.success(request, 'Voice recording successfully deleted.')
        
        # Redirect back to the ticket detail page
        return redirect('ticket_management:central_admin:ticket_detail', ticket_slug=ticket.slug)


class TicketVoiceUploadView(CentralAdminOnlyAccessMixin, View):
    """Upload a voice recording to an existing ticket"""
    
    def get(self, request, ticket_slug):
        # Get the ticket
        ticket= get_object_or_404(Ticket, slug=ticket_slug)
        
        # Check if ticket already has a voice recording
        if ticket.voice:
            messages.error(request, 'This ticket already has a voice recording. Delete it first to upload a new one.')
            return redirect('ticket_management:central_admin:ticket_detail', ticket_slug=ticket.slug)
        
        form = VoiceUploadForm()
        
        context = {
            'ticket': ticket,
            'form': form,
        }
        return render(request, 'central_admin/ticket_management/voice_upload.html', context)
    
    def post(self, request, ticket_slug):
        # Get the ticket
        ticket= get_object_or_404(Ticket, slug=ticket_slug)
        
        # Check if ticket already has a voice recording
        if ticket.voice:
            messages.error(request, 'This ticket already has a voice recording. Delete it first to upload a new one.')
            return redirect('ticket_management:central_admin:ticket_detail', ticket_slug=ticket.slug)
        
        form = VoiceUploadForm(request.POST, request.FILES)
        
        if form.is_valid():
            # Get the voice file from cleaned_data
            voice_file = form.cleaned_data.get('voice')
            
            if voice_file:
                try:
                    # Save the voice file to the ticket
                    ticket.voice = voice_file
                    # Set the user who uploaded the voice for activity tracking
                    ticket._changed_by = request.user
                    ticket.save()
                    
                    messages.success(request, 'Voice recording successfully uploaded.')
                    return redirect('ticket_management:central_admin:ticket_detail', ticket_slug=ticket.slug)
                    
                except Exception as e:
                    messages.error(request, f'Failed to upload voice recording: {str(e)}')
        
        # If form is not valid, show errors
        context = {
            'ticket': ticket,
            'form': form,
        }
        return render(request, 'central_admin/ticket_management/voice_upload.html', context)


class TicketAssignmentView(CentralAdminOnlyAccessMixin, UpdateView):
    """Assign a ticket to a supervisor with optional review requirement"""
    template_name = "central_admin/ticket_management/ticket_assignment.html"
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
        
        # Set the user who is assigning for activity tracking
        form.instance._changed_by = self.request.user
        
        # Save the form first (this saves the Ticket instance)
        response = super().form_valid(form)
        
        # Check if review is required
        if form.instance.requires_review:
            # Redirect to reviewer selection page (Step 2)
            messages.info(
                self.request,
                'Ticket assigned successfully. Now please select reviewers for this ticket.'
            )
            return redirect('ticket_management:central_admin:ticket_select_reviewers', ticket_slug=self.object.slug)
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
        return reverse_lazy('ticket_management:central_admin:ticket_detail', kwargs={'ticket_slug': self.ticket.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ticket'] = self.ticket
        return context


class TicketReviewerSelectionView(CentralAdminOnlyAccessMixin, View):
    """Select reviewers for a ticket that requires review (Step 2 after assignment)"""
    template_name = "central_admin/ticket_management/ticket_reviewer_selection.html"
    
    def dispatch(self, request, *args, **kwargs):
        self.ticket = get_object_or_404(Ticket, slug=kwargs['ticket_slug'])
        
        # Redirect if ticket doesn't require review
        if not self.ticket.requires_review:
            messages.warning(request, 'This ticket does not require review.')
            return redirect('ticket_management:central_admin:ticket_detail', ticket_slug=self.ticket.slug)
        
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
            # Set the user who is selecting reviewers for activity tracking
            self.ticket._changed_by = request.user
            self.ticket.reviewers.set(reviewers)
            
            # Create success message with reviewer names
            reviewer_names = ", ".join([r.get_full_name() or r.email for r in reviewers])
            assigned_to_name = self.ticket.assigned_to.get_full_name() or self.ticket.assigned_to.email
            
            messages.success(
                request,
                f'Ticket "{self.ticket.title}" has been assigned to {assigned_to_name} with review required by: {reviewer_names}.'
            )
            
            return redirect('ticket_management:central_admin:ticket_detail', ticket_slug=self.ticket.slug)
        
        return render(request, self.template_name, {
            'form': form,
            'ticket': self.ticket
        })


class TicketReopenView(CentralAdminOnlyAccessMixin, View):
    """Reopen a resolved, closed, or cancelled ticket"""
    
    def post(self, request, ticket_slug):
        # Get the ticket
        ticket= get_object_or_404(Ticket, slug=ticket_slug)
        
        # Check if ticket can be reopened
        if ticket.status not in ['resolved', 'closed', 'cancelled']:
            messages.error(request, f'Only resolved, closed, or cancelled issues can be reopened. This ticket is currently {ticket.get_status_display().lower()}.')
            return redirect('ticket_management:central_admin:ticket_detail', ticket_slug=ticket.slug)
        
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
            
            # Set the user who is reopening the ticket for activity tracking
            ticket._changed_by = request.user
            ticket.save()
            
            messages.success(request, f'Ticket "{ticket.title}" has been reopened from {previous_status.lower()} status.')
            
        except Exception as e:
            messages.error(request, f'Failed to reopen ticket: {str(e)}')
        
        # Redirect back to the ticket detail page
        return redirect('ticket_management:central_admin:ticket_detail', ticket_slug=ticket.slug)


class TicketResolveView(CentralAdminOnlyAccessMixin, View):
    """Mark a ticket as resolved with resolution notes and images"""
    
    def post(self, request, ticket_slug):
        from ..models import TicketResolutionImage
        from ..forms import TicketResolveForm
        
        # Get the ticket
        ticket= get_object_or_404(Ticket, slug=ticket_slug)
        
        # Check if ticket is already resolved, closed, or cancelled
        if ticket.status in ['resolved', 'closed', 'cancelled']:
            messages.error(request, f'This ticket is already {ticket.get_status_display().lower()} and cannot be resolved again.')
            return redirect('ticket_management:central_admin:ticket_detail', ticket_slug=ticket.slug)
        
        # Check if there are any incomplete work tasks
        incomplete_tasks = ticket.work_tasks.filter(completed=False)
        if incomplete_tasks.exists():
            incomplete_count = incomplete_tasks.count()
            task_word = 'task' if incomplete_count == 1 else 'tasks'
            messages.error(request, f'Cannot resolve ticket while {incomplete_count} work {task_word} remain incomplete. Please complete all work tasks before marking the ticket as resolved.')
            return redirect('ticket_management:central_admin:ticket_detail', ticket_slug=ticket.slug)
        
        # Process the form
        form = TicketResolveForm(request.POST, request.FILES, instance=ticket)
        
        if not form.is_valid():
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
            return redirect('ticket_management:central_admin:ticket_detail', ticket_slug=ticket.slug)
        
        try:
            # Update the ticket status and resolution notes
            ticket.status = 'resolved'
            ticket.resolution_notes = form.cleaned_data['resolution_notes']
            # Set the user who is resolving the ticket for activity tracking
            ticket._changed_by = request.user
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
        return redirect('ticket_management:central_admin:ticket_detail', ticket_slug=ticket.slug)


class TicketStartWorkView(CentralAdminOnlyAccessMixin, View):
    """Start work on a ticket by changing its status to in_progress"""
    
    def post(self, request, ticket_slug):
        # Get the ticket
        ticket= get_object_or_404(Ticket, slug=ticket_slug)
        
        # Check if ticket can be started
        if ticket.status in ['resolved', 'closed', 'cancelled']:
            messages.error(request, f'Cannot start work on {ticket.get_status_display().lower()} issues. Please reopen the ticket first.')
            return redirect('ticket_management:central_admin:ticket_detail', ticket_slug=ticket.slug)
        
        if ticket.status == 'in_progress':
            messages.info(request, 'Work is already in progress on this ticket.')
            return redirect('ticket_management:central_admin:ticket_detail', ticket_slug=ticket.slug)
        
        try:
            # Store the previous status for the message
            previous_status = ticket.get_status_display()
            
            # Change status to in_progress
            ticket.status = 'in_progress'
            # Set the user who is starting work for activity tracking
            ticket._changed_by = request.user
            ticket.save()
            
            messages.success(request, f'Started work on ticket "{ticket.title}". Status changed from {previous_status.lower()} to in progress.')
            
        except Exception as e:
            messages.error(request, f'Failed to start work on ticket: {str(e)}')
        
        # Redirect back to the ticket detail page
        return redirect('ticket_management:central_admin:ticket_detail', ticket_slug=ticket.slug)


class SiteVisitCreateView(CentralAdminOnlyAccessMixin, CreateView):
    """Create a new site visit for a ticket"""
    template_name = "central_admin/ticket_management/site_visit_create.html"
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
        return reverse_lazy('ticket_management:central_admin:ticket_detail', kwargs={'ticket_slug': self.ticket.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ticket'] = self.ticket
        return context


class SiteVisitUpdateView(CentralAdminOnlyAccessMixin, UpdateView):
    """Update an existing site visit"""
    template_name = "central_admin/ticket_management/site_visit_update.html"
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
        # Set the user who updated the site visit for activity tracking
        form.instance._changed_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Site visit "{form.instance.title}" updated successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('ticket_management:central_admin:ticket_detail', kwargs={'ticket_slug': self.ticket.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ticket'] = self.ticket
        context['site_visit'] = self.site_visit
        return context


class SiteVisitDeleteView(CentralAdminOnlyAccessMixin, View):
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
        
        return redirect('ticket_management:central_admin:ticket_detail', ticket_slug=ticket_slug)


class SiteVisitListView(CentralAdminOnlyAccessMixin, ListView):
    """List all site visits for central admin"""
    model = SiteVisit
    template_name = "central_admin/ticket_management/site_visit_list.html"
    context_object_name = "site_visits"

    def get_queryset(self):
        # Get all site visits (central admin sees all)
        queryset = SiteVisit.objects.all().select_related(
            'ticket', 'ticket__org', 'ticket__space', 'created_by', 'assigned_to'
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
    template_name = "central_admin/ticket_management/site_visit_detail.html"
    context_object_name = "site_visit"
    slug_field = 'slug'
    slug_url_kwarg = 'site_visit_slug'
    
    def get_queryset(self):
        return SiteVisit.objects.select_related(
            'ticket',
            'ticket__org',
            'ticket__space',
            'ticket__reporter',
            'created_by',
            'assigned_to'
        ).prefetch_related('images', 'ticket__images')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ticket'] = self.object.ticket
        return context


class PerformanceReportView(CentralAdminOnlyAccessMixin, View):
    """Generate and download PDF performance reports"""
    template_name = "central_admin/ticket_management/performance_report.html"
    
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




class TicketListReportView(CentralAdminOnlyAccessMixin, View):
    """Download a PDF or Excel report of issues matching the current list filters."""

    def get(self, request):
        report_format = request.GET.get('format', 'xlsx')

        # Build filtered queryset (same logic as TicketListView)
        queryset = Ticket.objects.select_related(
            'org', 'space', 'reporter', 'assigned_to'
        ).prefetch_related('images')

        status_filter = request.GET.get('status')
        space_filter = request.GET.get('space')
        reporter_filter = request.GET.get('reporter')
        assignee_filter = request.GET.get('assignee')

        queryset = apply_ticket_list_filters(
            queryset,
            status_filter=status_filter,
            space_filter=space_filter,
            reporter_filter=reporter_filter,
            assignee_filter=assignee_filter,
        )
        queryset = annotate_and_order(queryset)

        filter_descriptions = describe_filters(
            status_filter=status_filter,
            space_filter=space_filter,
            reporter_filter=reporter_filter,
            assignee_filter=assignee_filter,
        )

        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')

        if report_format == 'pdf':
            try:
                buf = build_ticket_list_pdf(queryset, filter_descriptions)
                response = HttpResponse(buf.getvalue(), content_type='application/pdf')
                response['Content-Disposition'] = (
                    f'attachment; filename="ticket_report_{timestamp}.pdf"'
                )
                return response
            except Exception as e:
                messages.error(request, f'Failed to generate PDF report: {str(e)}')
                return redirect('ticket_management:central_admin:ticket_list')
        else:
            try:
                buf = build_ticket_list_excel(queryset, filter_descriptions)
                response = HttpResponse(
                    buf.getvalue(),
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                )
                response['Content-Disposition'] = (
                    f'attachment; filename="ticket_report_{timestamp}.xlsx"'
                )
                return response
            except Exception as e:
                messages.error(request, f'Failed to generate Excel report: {str(e)}')
                return redirect('ticket_management:central_admin:ticket_list')

class PurchaseRequestListView(CentralAdminOnlyAccessMixin, ListView):
    """List all purchase requests for central admin"""
    model = PurchaseRequest
    template_name = "central_admin/ticket_management/purchase_request_list.html"
    context_object_name = "purchase_requests"
    paginate_by = 20
    
    def get_queryset(self):
        queryset = PurchaseRequest.objects.select_related(
            'ticket', 'ticket__space', 'org', 'space', 'requested_by', 'reviewed_by'
        ).prefetch_related('shopping_list_items__shopping_list').all()
        
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
    template_name = "central_admin/ticket_management/purchase_request_detail.html"
    context_object_name = "purchase_request"
    slug_field = 'slug'
    slug_url_kwarg = 'purchase_request_slug'
    
    def get_queryset(self):
        return PurchaseRequest.objects.select_related(
            'ticket', 'ticket__space', 'ticket__reporter', 'org', 'space', 'requested_by', 'reviewed_by'
        ).prefetch_related('ticket__images')


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
        TicketActivity.objects.create(
            ticket=purchase_request.ticket,
            activity_type='purchase_request_approved',
            user=request.user,
            description=f'Purchase request for "{purchase_request.item}" (Qty: {purchase_request.quantity}) approved{f" - ${purchase_request.estimated_amount}" if purchase_request.estimated_amount else ""}'
        )
        
        messages.success(request, f"Purchase request for '{purchase_request.item}' has been approved.")
        return redirect('ticket_management:central_admin:purchase_request_detail', purchase_request_slug=purchase_request.slug)


class PurchaseRequestRejectView(CentralAdminOnlyAccessMixin, View):
    """Reject a purchase request"""
    
    def post(self, request, purchase_request_slug):
        purchase_request = get_object_or_404(PurchaseRequest, slug=purchase_request_slug)
        
        # Get review notes from form (required for rejection)
        review_notes = request.POST.get('review_notes', '')
        
        if not review_notes:
            messages.error(request, "Please provide a reason for rejecting this purchase request.")
            return redirect('ticket_management:central_admin:purchase_request_detail', purchase_request_slug=purchase_request.slug)
        
        # Update purchase request
        purchase_request.status = 'rejected'
        purchase_request.reviewed_by = request.user
        purchase_request.reviewed_at = timezone.now()
        purchase_request.review_notes = review_notes
        purchase_request.save()
        
        # Track activity
        TicketActivity.objects.create(
            ticket=purchase_request.ticket,
            activity_type='purchase_request_rejected',
            user=request.user,
            description=f'Purchase request for "{purchase_request.item}" (Qty: {purchase_request.quantity}) rejected - Reason: {review_notes[:100]}'
        )
        
        messages.success(request, f"Purchase request for '{purchase_request.item}' has been rejected.")
        return redirect('ticket_management:central_admin:purchase_request_detail', purchase_request_slug=purchase_request.slug)


class PurchaseRequestDeleteView(CentralAdminOnlyAccessMixin, View):
    """Delete a pending purchase request"""
    
    def post(self, request, purchase_request_slug):
        purchase_request = get_object_or_404(PurchaseRequest, slug=purchase_request_slug)
        
        # Only allow deletion if status is pending
        if purchase_request.status != 'pending':
            messages.error(request, "Only pending purchase requests can be deleted.")
            return redirect('ticket_management:central_admin:purchase_request_detail', purchase_request_slug=purchase_request.slug)
        
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
        return redirect('ticket_management:central_admin:ticket_detail', ticket_slug=ticket_slug)


class GenerateShoppingListView(CentralAdminOnlyAccessMixin, View):
    """Generate and display a shopping list from selected approved purchase requests"""
    
    def post(self, request):
        selected_slugs = request.POST.getlist('selected_requests')
        
        if not selected_slugs:
            messages.error(request, "Please select at least one purchase request.")
            return redirect('ticket_management:central_admin:purchase_request_list')
        
        # Get selected purchase requests
        purchase_requests = PurchaseRequest.objects.filter(
            slug__in=selected_slugs,
            status='approved'
        ).select_related('ticket', 'space', 'requested_by', 'reviewed_by').order_by('space__name', 'item')
        
        if not purchase_requests.exists():
            messages.error(request, "No approved purchase requests found.")
            return redirect('ticket_management:central_admin:purchase_request_list')
        
        # Calculate total
        total_amount = sum(pr.estimated_amount for pr in purchase_requests if pr.estimated_amount)
        
        # Group by space
        from itertools import groupby
        grouped_requests = {}
        for space, items in groupby(purchase_requests, key=lambda x: x.space):
            grouped_requests[space] = list(items)
        
        context = {
            'purchase_requests': purchase_requests,
            'grouped_requests': grouped_requests,
            'total_amount': total_amount,
            'generated_by': request.user,
            'generated_at': timezone.now(),
            'selected_slugs': selected_slugs,  # Pass for saving later
        }
        
        return render(request, 'central_admin/ticket_management/shopping_list.html', context)


class SaveShoppingListView(CentralAdminOnlyAccessMixin, View):
    """Save a generated shopping list to database"""
    
    def post(self, request):
        selected_slugs = request.POST.getlist('selected_requests')
        custom_title = request.POST.get('title', '').strip()
        
        if not selected_slugs:
            messages.error(request, "No purchase requests to save.")
            return redirect('ticket_management:central_admin:purchase_request_list')
        
        # Get selected purchase requests
        purchase_requests = PurchaseRequest.objects.filter(
            slug__in=selected_slugs,
            status='approved'
        ).select_related('ticket', 'space', 'requested_by', 'reviewed_by').order_by('space__name', 'item')
        
        if not purchase_requests.exists():
            messages.error(request, "No approved purchase requests found.")
            return redirect('ticket_management:central_admin:purchase_request_list')
        
        # Calculate total
        total_amount = sum(pr.estimated_amount for pr in purchase_requests if pr.estimated_amount)
        
        # Create shopping list in database
        from ticket_management.models import ShoppingList, ShoppingListItem
        
        # Use custom title if provided, otherwise use default
        if custom_title:
            title = custom_title
        else:
            title = f"Shopping List - {timezone.now().strftime('%B %d, %Y')}"
        
        shopping_list = ShoppingList.objects.create(
            title=title,
            org=request.user.organization,
            generated_by=request.user,
            total_amount=total_amount if total_amount else None,
            item_count=purchase_requests.count()
        )
        
        # Create shopping list items
        for pr in purchase_requests:
            ShoppingListItem.objects.create(
                shopping_list=shopping_list,
                purchase_request=pr,
                item_snapshot=pr.item,
                quantity_snapshot=pr.quantity,
                amount_snapshot=pr.estimated_amount,
                space_name=pr.space.name if pr.space else "No Space",
                ticket_title=pr.ticket.title
            )
        
        messages.success(request, f"Shopping list '{title}' saved successfully with {purchase_requests.count()} items.")
        
        # Redirect to the saved shopping list detail view
        return redirect('ticket_management:central_admin:shopping_list_detail', shopping_list_slug=shopping_list.slug)


class ShoppingListListView(CentralAdminOnlyAccessMixin, ListView):
    """List all shopping lists for the organization"""
    model = None  # Will use get_queryset
    template_name = 'central_admin/ticket_management/shopping_list_list.html'
    context_object_name = 'shopping_lists'
    paginate_by = 20
    
    def get_queryset(self):
        from ticket_management.models import ShoppingList
        return ShoppingList.objects.filter(
            org=self.request.user.organization
        ).select_related('generated_by').prefetch_related('items').order_by('-generated_at')


class ShoppingListDetailView(CentralAdminOnlyAccessMixin, View):
    """Display a saved shopping list"""
    
    def get(self, request, shopping_list_slug):
        from ticket_management.models import ShoppingList
        shopping_list = get_object_or_404(
            ShoppingList.objects.select_related('generated_by').prefetch_related(
                'items__purchase_request__ticket',
                'items__purchase_request__space'
            ),
            slug=shopping_list_slug,
            org=request.user.organization
        )
        
        # Group items by space
        from itertools import groupby
        items = shopping_list.items.all().order_by('space_name', 'item_snapshot')
        grouped_items = {}
        for space_name, space_items in groupby(items, key=lambda x: x.space_name):
            grouped_items[space_name] = list(space_items)
        
        context = {
            'shopping_list': shopping_list,
            'grouped_items': grouped_items,
        }
        
        return render(request, 'central_admin/ticket_management/shopping_list_detail.html', context)


class ShoppingListDeleteView(CentralAdminOnlyAccessMixin, View):
    """Delete a shopping list"""
    
    def post(self, request, shopping_list_slug):
        from ticket_management.models import ShoppingList
        shopping_list = get_object_or_404(
            ShoppingList,
            slug=shopping_list_slug,
            org=request.user.organization
        )
        
        title = shopping_list.title
        shopping_list.delete()
        
        messages.success(request, f"Shopping list '{title}' deleted successfully.")
        return redirect('ticket_management:central_admin:shopping_list_list')

