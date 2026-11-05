from django.shortcuts import get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.urls import reverse_lazy
from django.db.models import Case, When, IntegerField
from django.utils import timezone
from .. forms import TicketCommentForm, WorkTaskForm, WorkTaskUpdateForm, WorkTaskCompleteForm, SiteVisitForm, SiteVisitCompleteForm, TicketForm
from django.contrib import messages
from .. models import Ticket, WorkTask, SiteVisit, SiteVisitImage, TicketImage
from django.shortcuts import redirect
from config.mixins.access_mixin import SupervisorOnlyAccessMixin
from core.models import Space


class WorkTaskListView(SupervisorOnlyAccessMixin, ListView):
    """List all work tasks assigned to the supervisor"""
    model = WorkTask
    template_name = "supervisor/ticket_management/work_task_list.html"
    context_object_name = "work_tasks"

    def get_queryset(self):
        queryset = WorkTask.objects.filter(assigned_to=self.request.user).select_related('ticket', 'ticket__org', 'ticket__space')
        
        # Filter by status if provided
        status_filter = self.request.GET.get('status', None)
        if status_filter == 'pending':
            queryset = queryset.filter(completed=False)
        elif status_filter == 'completed':
            queryset = queryset.filter(completed=True)
        
        # Order by completion status, ticket priority (critical first, low last), then due date
        return queryset.annotate(
            priority_order=Case(
                When(ticket__priority='critical', then=1),
                When(ticket__priority='high', then=2),
                When(ticket__priority='medium', then=3),
                When(ticket__priority='low', then=4),
                default=5,
                output_field=IntegerField(),
            )
        ).order_by('completed', 'priority_order', 'due_date')


class WorkTaskDetailView(SupervisorOnlyAccessMixin, DetailView):
    """View details of a specific work task"""
    model = WorkTask
    template_name = "supervisor/ticket_management/work_task_detail.html"
    context_object_name = "work_task"
    slug_field = 'slug'
    slug_url_kwarg = 'work_task_slug'
    
    def get_queryset(self):
        return WorkTask.objects.filter(assigned_to=self.request.user).select_related(
            'ticket', 
            'ticket__org', 
            'ticket__space',
            'ticket__reporter'
        ).prefetch_related('ticket__images')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ticket'] = self.object.ticket
        return context


class SupervisorTicketListView(SupervisorOnlyAccessMixin, ListView):
    model = Ticket
    template_name = "supervisor/ticket_management/ticket_list.html"
    context_object_name = "tickets"

    def get_queryset(self):
        # Start with issues assigned to the supervisor
        queryset = Ticket.objects.filter(assigned_to=self.request.user)
        
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
        
        # Order by status (open/assigned/in_progress first), then priority (critical first, low last), then creation date
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
        # Get all spaces in the supervisor's organization
        if self.request.user.organization:
            context['spaces'] = Space.objects.filter(
                org=self.request.user.organization
            ).select_related('org').order_by('name')
        else:
            context['spaces'] = Space.objects.none()
        return context
    
    
class TicketDetailView(SupervisorOnlyAccessMixin, DetailView):
    template_name = "supervisor/ticket_management/ticket_detail.html"
    context_object_name = "ticket"
    model = Ticket
    slug_field = 'slug'
    slug_url_kwarg = 'ticket_slug'
    
    def get_queryset(self):
        return Ticket.objects.prefetch_related(
            'images', 
            'comments', 
            'work_tasks__assigned_to',
            'site_visits__created_by',
            'site_visits__assigned_to',
            'site_visits__images'
        ).select_related('org', 'space')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add work tasks to context sorted by completion status and ticket priority
        work_tasks = self.object.work_tasks.select_related('ticket').all().annotate(
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
        return context


class TicketCreateView(SupervisorOnlyAccessMixin, CreateView):
    """Create a new ticket as supervisor"""
    template_name = "supervisor/ticket_management/ticket_create.html"
    form_class = TicketForm
    success_url = reverse_lazy('ticket_management:supervisor:ticket_list')
    
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
            used_tokens = request.session.get('used_ticket_create_tokens', [])
            if form_token in used_tokens:
                messages.warning(request, 'This ticket has already been created. Please do not submit the form multiple times.')
                return redirect(self.success_url)
        
        return super().post(request, *args, **kwargs)
    
    def form_valid(self, form):
        # Set the reporter to the current user before saving
        form.instance.reporter = self.request.user
        
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
    

class TicketResolveView(SupervisorOnlyAccessMixin, View):
    """Mark a ticket as resolved with resolution notes and images"""
    
    def post(self, request, ticket_slug):
        from ..models import TicketResolutionImage
        from ..forms import TicketResolveForm
        
        # Get the ticket
        ticket= get_object_or_404(Ticket, slug=ticket_slug)
        
        # Check if ticket is already resolved, closed, or cancelled
        if ticket.status in ['resolved', 'closed', 'cancelled']:
            messages.error(request, f'This ticket is already {ticket.get_status_display().lower()} and cannot be resolved again.')
            return redirect('ticket_management:supervisor:ticket_detail', ticket_slug=ticket.slug)
        
        # Check if there are any incomplete work tasks
        incomplete_tasks = ticket.work_tasks.filter(completed=False)
        if incomplete_tasks.exists():
            incomplete_count = incomplete_tasks.count()
            task_word = 'task' if incomplete_count == 1 else 'tasks'
            messages.error(request, f'Cannot resolve ticket while {incomplete_count} work {task_word} remain incomplete. Please complete all work tasks before marking the ticket as resolved.')
            return redirect('ticket_management:supervisor:ticket_detail', ticket_slug=ticket.slug)

        # Process the form
        form = TicketResolveForm(request.POST, request.FILES, instance=ticket)
        
        if not form.is_valid():
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
            return redirect('ticket_management:supervisor:ticket_detail', ticket_slug=ticket.slug)
        
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
        return redirect('ticket_management:supervisor:ticket_detail', ticket_slug=ticket.slug)

    

class WorkTaskCreateView(SupervisorOnlyAccessMixin, CreateView):
    template_name = "supervisor/ticket_management/work_task_create.html"
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
        return reverse_lazy('ticket_management:supervisor:ticket_detail', kwargs={'ticket_slug': self.ticket.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ticket'] = self.ticket
        return context


class WorkTaskUpdateView(SupervisorOnlyAccessMixin,UpdateView):
    template_name = "supervisor/ticket_management/work_task_update.html"
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
        return reverse_lazy('ticket_management:supervisor:ticket_detail', kwargs={'ticket_slug': self.ticket.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ticket'] = self.ticket
        context['work_task'] = self.work_task
        return context


class WorkTaskCompleteView(SupervisorOnlyAccessMixin, UpdateView):
    """Complete a work task with resolution notes and images"""
    template_name = "supervisor/ticket_management/work_task_complete.html"
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
        # Check if 'next' parameter is set to redirect to task detail page
        next_param = self.request.GET.get('next', None)
        if next_param == 'task_detail':
            return reverse_lazy('ticket_management:supervisor:work_task_detail', kwargs={'work_task_slug': self.work_task.slug})
        # Default redirect to ticket detail page
        return reverse_lazy('ticket_management:supervisor:ticket_detail', kwargs={'ticket_slug': self.work_task.ticket.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['work_task'] = self.work_task
        context['ticket'] = self.work_task.ticket
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
        
        return redirect('ticket_management:supervisor:ticket_detail', ticket_slug=self.work_task.ticket.slug)


class WorkTaskDeleteView(SupervisorOnlyAccessMixin, View):
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

        return redirect('ticket_management:supervisor:ticket_detail', ticket_slug=ticket_slug)


class WorkTaskResolutionImageDeleteView(SupervisorOnlyAccessMixin, View):
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
        return redirect('ticket_management:supervisor:ticket_detail', ticket_slug=work_task.ticket.slug)
    

class TicketStartWorkView(SupervisorOnlyAccessMixin, View):
    """Start work on a ticket by changing its status to in_progress"""
    
    def post(self, request, ticket_slug):
        # Get the ticket
        ticket= get_object_or_404(Ticket, slug=ticket_slug)

        if ticket.status == 'in_progress':
            messages.info(request, 'Work is already in progress on this ticket.')
            return redirect('ticket_management:supervisor:ticket_detail', ticket_slug=ticket.slug)

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
        return redirect('ticket_management:supervisor:ticket_detail', ticket_slug=ticket.slug)


class SiteVisitCreateView(SupervisorOnlyAccessMixin, CreateView):
    """Create a new site visit for a ticket"""
    template_name = "supervisor/ticket_management/site_visit_create.html"
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
        return reverse_lazy('ticket_management:supervisor:ticket_detail', kwargs={'ticket_slug': self.ticket.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ticket'] = self.ticket
        return context


class SiteVisitUpdateView(SupervisorOnlyAccessMixin, UpdateView):
    """Update an existing site visit"""
    template_name = "supervisor/ticket_management/site_visit_update.html"
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
        return reverse_lazy('ticket_management:supervisor:ticket_detail', kwargs={'ticket_slug': self.ticket.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ticket'] = self.ticket
        context['site_visit'] = self.site_visit
        return context


class SiteVisitDeleteView(SupervisorOnlyAccessMixin, View):
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
        
        return redirect('ticket_management:supervisor:ticket_detail', ticket_slug=ticket_slug)


class SiteVisitListView(SupervisorOnlyAccessMixin, ListView):
    """List all site visits assigned to the supervisor"""
    model = SiteVisit
    template_name = "supervisor/ticket_management/site_visit_list.html"
    context_object_name = "site_visits"

    def get_queryset(self):
        # Get site visits where the supervisor is either the creator or assigned to them
        queryset = SiteVisit.objects.filter(
            assigned_to=self.request.user
        ).select_related('ticket', 'ticket__org', 'ticket__space', 'created_by', 'assigned_to').prefetch_related('images')
        
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


class SiteVisitDetailView(SupervisorOnlyAccessMixin, DetailView):
    """View details of a specific site visit"""
    model = SiteVisit
    template_name = "supervisor/ticket_management/site_visit_detail.html"
    context_object_name = "site_visit"
    slug_field = 'slug'
    slug_url_kwarg = 'site_visit_slug'
    
    def get_queryset(self):
        return SiteVisit.objects.filter(
            assigned_to=self.request.user
        ).select_related(
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
        context['complete_form'] = SiteVisitCompleteForm()
        return context


class SiteVisitStartView(SupervisorOnlyAccessMixin, View):
    """Start a site visit by changing status to in_progress"""
    
    def post(self, request, site_visit_slug):
        site_visit = get_object_or_404(
            SiteVisit,
            slug=site_visit_slug,
            assigned_to=request.user
        )
        
        # Only allow starting if status is scheduled
        if site_visit.status == 'scheduled':
            site_visit.mark_in_progress()
            messages.success(
                request,
                f'Site visit "{site_visit.title}" has been started!'
            )
        else:
            messages.error(
                request,
                'Only scheduled site visits can be started.'
            )
        
        return redirect(
            'ticket_management:supervisor:site_visit_detail',
            site_visit_slug=site_visit.slug
        )


class SiteVisitCancelView(SupervisorOnlyAccessMixin, View):
    """Cancel a site visit"""
    
    def post(self, request, site_visit_slug):
        site_visit = get_object_or_404(
            SiteVisit,
            slug=site_visit_slug,
            assigned_to=request.user
        )
        
        # Only allow canceling if status is scheduled or in_progress
        if site_visit.status in ['scheduled', 'in_progress']:
            site_visit.cancel()
            messages.success(
                request,
                f'Site visit "{site_visit.title}" has been cancelled.'
            )
        else:
            messages.error(
                request,
                'Only scheduled or in-progress site visits can be cancelled.'
            )
        
        return redirect(
            'ticket_management:supervisor:site_visit_detail',
            site_visit_slug=site_visit.slug
        )


class SiteVisitCompleteView(SupervisorOnlyAccessMixin, View):
    """Complete a site visit with findings, actions, and recommendations"""
    
    def post(self, request, site_visit_slug):
        site_visit = get_object_or_404(
            SiteVisit,
            slug=site_visit_slug,
            assigned_to=request.user
        )
        
        # Only allow completing if status is scheduled or in_progress
        if site_visit.status not in ['scheduled', 'in_progress']:
            messages.error(
                request,
                'Only scheduled or in-progress site visits can be completed.'
            )
            return redirect(
                'ticket_management:supervisor:site_visit_detail',
                site_visit_slug=site_visit.slug
            )
        
        form = SiteVisitCompleteForm(request.POST, request.FILES, instance=site_visit)
        
        if form.is_valid():
            # Save the site visit with findings, actions, and recommendations
            site_visit = form.save(commit=False)
            site_visit.mark_completed()
            site_visit.save()
            
            # Handle image uploads (up to 3 images)
            for i in range(1, 4):
                image_field_name = f'image{i}'
                image = request.FILES.get(image_field_name)
                
                if image:
                    SiteVisitImage.objects.create(
                        site_visit=site_visit,
                        image=image
                    )
            
            messages.success(
                request,
                f'Site visit "{site_visit.title}" has been marked as completed!'
            )
            
            return redirect(
                'ticket_management:supervisor:site_visit_detail',
                site_visit_slug=site_visit.slug
            )
        else:
            # Form is invalid, return to detail page with errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
            
            return redirect(
                'ticket_management:supervisor:site_visit_detail',
                site_visit_slug=site_visit.slug
            )
