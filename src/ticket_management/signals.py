from django.db.models.signals import post_save, pre_save, post_delete, pre_delete, m2m_changed
from django.dispatch import receiver
from .models import Ticket, WorkTask, TicketImage, SiteVisit, TicketActivity
from .utils.firebase_notifications import send_ticket_created_notification
from core.models import User


@receiver(post_save, sender=Ticket, dispatch_uid="assign_vehicle_to_workshop_on_issue")
def assign_vehicle_to_workshop_on_issue(sender, instance, created, **kwargs):
    """When a ticket related to a vehicle is created, mark the vehicle as in maintenance."""
    # Do NOT change vehicle.status here. Instead, log that a ticket was reported for the vehicle.
    if created and getattr(instance, 'vehicle', None):
        try:
            vehicle = instance.vehicle
            # Log that a ticket was reported for this vehicle (no status change)
            try:
                TicketActivity.objects.create(
                    ticket=instance,
                    activity_type='vehicle_ticket_reported',
                    user=instance.reporter,
                    description=f'Ticket reported for vehicle "{vehicle.registration_number}" (no status change)'
                )
            except Exception:
                pass
        except Exception:
            # Fail silently to avoid breaking ticket creation
            pass


# Dictionary to store old values of instances before saving
_ticket_pre_save_data = {}
_work_task_pre_save_data = {}
_site_visit_pre_save_data = {}


@receiver(pre_save, sender=Ticket)
def store_issue_old_values(sender, instance, **kwargs):
    """Store old values before saving to compare changes"""
    if instance.pk:
        try:
            old_instance = Ticket.objects.get(pk=instance.pk)
            _ticket_pre_save_data[instance.pk] = {
                'status': old_instance.status,
                'priority': old_instance.priority,
                'assigned_to': old_instance.assigned_to,
                'reviewed_by': old_instance.reviewed_by,
                'title': old_instance.title,
                'description': old_instance.description,
                'voice': old_instance.voice,
            }
        except Ticket.DoesNotExist:
            pass


@receiver(post_save, sender=Ticket, dispatch_uid="track_issue_creation_and_changes")
def track_issue_creation_and_changes(sender, instance, created, **kwargs):
    """Track ticket creation and various field changes"""
    
    if created:
        # Track ticket creation
        TicketActivity.objects.create(
            ticket=instance,
            activity_type='created',
            user=instance.reporter,
            description=f'Ticket "{instance.title}" was created by {instance.reporter.get_full_name() or instance.reporter}'
        )
        
        # Send push notifications to central admins in the same organization
        central_admins = User.objects.filter(
            user_type='central_admin',
            organization=instance.org,
            is_active=True
        )
        
        if central_admins.exists():
            send_ticket_created_notification(instance, central_admins)
    else:
        # Track changes to existing ticket
        old_data = _ticket_pre_save_data.get(instance.pk)
        if not old_data:
            return
        
        # Track status changes
        if old_data['status'] != instance.status:
            # Get display values
            old_status_display = dict(Ticket.STATUS_CHOICES).get(old_data['status'], old_data['status'])
            new_status_display = instance.get_status_display()
            
            # Special handling for specific status changes
            if instance.status == 'resolved':
                TicketActivity.objects.create(
                    ticket=instance,
                    activity_type='resolved',
                    user=getattr(instance, '_changed_by', None),
                    description=f'Ticket marked as resolved',
                    old_value=old_status_display,
                    new_value=new_status_display
                )
            elif instance.status == 'closed':
                TicketActivity.objects.create(
                    ticket=instance,
                    activity_type='closed',
                    user=getattr(instance, '_changed_by', None),
                    description=f'Ticket closed',
                    old_value=old_status_display,
                    new_value=new_status_display
                )
            elif instance.status == 'cancelled':
                TicketActivity.objects.create(
                    ticket=instance,
                    activity_type='cancelled',
                    user=getattr(instance, '_changed_by', None),
                    description=f'Ticket cancelled',
                    old_value=old_status_display,
                    new_value=new_status_display
                )
            elif instance.status == 'escalated':
                TicketActivity.objects.create(
                    ticket=instance,
                    activity_type='escalated',
                    user=getattr(instance, '_changed_by', None),
                    description=f'Ticket escalated',
                    old_value=old_status_display,
                    new_value=new_status_display
                )
            elif old_data['status'] in ['resolved', 'closed', 'cancelled'] and instance.status in ['open', 'assigned', 'in_progress']:
                # Ticket reopened
                TicketActivity.objects.create(
                    ticket=instance,
                    activity_type='reopened',
                    user=getattr(instance, '_changed_by', None),
                    description=f'Ticket reopened',
                    old_value=old_status_display,
                    new_value=new_status_display
                )
            else:
                # Generic status change
                TicketActivity.objects.create(
                    ticket=instance,
                    activity_type='status_changed',
                    user=getattr(instance, '_changed_by', None),
                    description=f'Status changed from {old_status_display} to {new_status_display}',
                    old_value=old_status_display,
                    new_value=new_status_display
                )
        
        # Track priority changes
        if old_data['priority'] != instance.priority:
            old_priority_display = dict(Ticket.PRIORITY_CHOICES).get(old_data['priority'], old_data['priority'])
            new_priority_display = instance.get_priority_display()
            TicketActivity.objects.create(
                ticket=instance,
                activity_type='priority_changed',
                user=getattr(instance, '_changed_by', None),
                description=f'Priority changed from {old_priority_display} to {new_priority_display}',
                old_value=old_priority_display,
                new_value=new_priority_display
            )
        
        # Track assignment changes
        if old_data['assigned_to'] != instance.assigned_to:
            if instance.assigned_to and not old_data['assigned_to']:
                # New assignment
                TicketActivity.objects.create(
                    ticket=instance,
                    activity_type='assigned',
                    user=instance.assigned_by or getattr(instance, '_changed_by', None),
                    description=f'Ticket assigned to {instance.assigned_to.get_full_name() or instance.assigned_to}',
                    new_value=str(instance.assigned_to)
                )
            elif not instance.assigned_to and old_data['assigned_to']:
                # Unassigned
                old_assignee = old_data['assigned_to']
                TicketActivity.objects.create(
                    ticket=instance,
                    activity_type='unassigned',
                    user=getattr(instance, '_changed_by', None),
                    description=f'Ticket unassigned from {old_assignee.get_full_name() or old_assignee}',
                    old_value=str(old_assignee)
                )
            else:
                # Reassigned
                old_assignee = old_data['assigned_to']
                TicketActivity.objects.create(
                    ticket=instance,
                    activity_type='reassigned',
                    user=instance.assigned_by or getattr(instance, '_changed_by', None),
                    description=f'Ticket reassigned from {old_assignee.get_full_name() or old_assignee} to {instance.assigned_to.get_full_name() or instance.assigned_to}',
                    old_value=str(old_assignee),
                    new_value=str(instance.assigned_to)
                )
        
        # Track review changes
        if old_data['reviewed_by'] != instance.reviewed_by and instance.reviewed_by:
            TicketActivity.objects.create(
                ticket=instance,
                activity_type='reviewed',
                user=instance.reviewed_by,
                description=f'Ticket reviewed by {instance.reviewed_by.get_full_name() or instance.reviewed_by}',
                new_value=str(instance.reviewed_by)
            )
        
        # Track title or description changes
        if old_data['title'] != instance.title or old_data['description'] != instance.description:
            changes = []
            if old_data['title'] != instance.title:
                changes.append('title')
            if old_data['description'] != instance.description:
                changes.append('description')
            
            TicketActivity.objects.create(
                ticket=instance,
                activity_type='updated',
                user=getattr(instance, '_changed_by', None),
                description=f'Ticket {", ".join(changes)} updated'
            )
        
        # Track voice recording changes
        if old_data['voice'] != instance.voice:
            if instance.voice and not old_data['voice']:
                TicketActivity.objects.create(
                    ticket=instance,
                    activity_type='voice_added',
                    user=getattr(instance, '_changed_by', None),
                    description='Voice recording added'
                )
            elif not instance.voice and old_data['voice']:
                TicketActivity.objects.create(
                    ticket=instance,
                    activity_type='voice_deleted',
                    user=getattr(instance, '_changed_by', None),
                    description='Voice recording deleted'
                )
        
        # Clean up old data after processing
        if instance.pk in _ticket_pre_save_data:
            del _ticket_pre_save_data[instance.pk]


@receiver(m2m_changed, sender=Ticket.reviewers.through)
def track_reviewer_changes(sender, instance, action, pk_set, **kwargs):
    """Track when reviewers are added or removed"""
    if action == 'post_add':
        from core.models import User
        reviewers = User.objects.filter(pk__in=pk_set)
        reviewer_names = ', '.join([r.get_full_name() or str(r) for r in reviewers])
        TicketActivity.objects.create(
            ticket=instance,
            activity_type='review_requested',
            user=getattr(instance, '_changed_by', None),
            description=f'Review requested from: {reviewer_names}'
        )


@receiver(pre_save, sender=WorkTask)
def store_work_task_old_values(sender, instance, **kwargs):
    """Store old values before saving to compare changes"""
    if instance.pk:
        try:
            old_instance = WorkTask.objects.get(pk=instance.pk)
            _work_task_pre_save_data[instance.pk] = {
                'completed': old_instance.completed,
                'title': old_instance.title,
                'description': old_instance.description,
                'assigned_to': old_instance.assigned_to,
            }
        except WorkTask.DoesNotExist:
            pass


@receiver(post_save, sender=WorkTask)
def track_work_task_changes(sender, instance, created, **kwargs):
    """Track work task creation and changes"""
    
    if created:
        TicketActivity.objects.create(
            ticket=instance.ticket,
            activity_type='work_task_created',
            user=getattr(instance, '_created_by', None),
            description=f'Work task "{instance.title}" created and assigned to {instance.assigned_to.get_full_name() or instance.assigned_to}'
        )
    else:
        # Track completion status changes
        old_data = _work_task_pre_save_data.get(instance.pk)
        if not old_data:
            return
        
        if old_data['completed'] != instance.completed:
            if instance.completed:
                TicketActivity.objects.create(
                    ticket=instance.ticket,
                    activity_type='work_task_completed',
                    user=getattr(instance, '_changed_by', None),
                    description=f'Work task "{instance.title}" marked as completed'
                )
            else:
                TicketActivity.objects.create(
                    ticket=instance.ticket,
                    activity_type='work_task_reopened',
                    user=getattr(instance, '_changed_by', None),
                    description=f'Work task "{instance.title}" reopened'
                )
        elif old_data['title'] != instance.title or old_data['description'] != instance.description or old_data['assigned_to'] != instance.assigned_to:
            # Track other changes
            changes = []
            if old_data['title'] != instance.title:
                changes.append('title')
            if old_data['description'] != instance.description:
                changes.append('description')
            if old_data['assigned_to'] != instance.assigned_to:
                changes.append(f'assignee (now {instance.assigned_to.get_full_name() or instance.assigned_to})')
            
            TicketActivity.objects.create(
                ticket=instance.ticket,
                activity_type='work_task_updated',
                user=getattr(instance, '_changed_by', None),
                description=f'Work task "{instance.title}" updated: {", ".join(changes)}'
            )
        
        # Clean up old data after processing
        if instance.pk in _work_task_pre_save_data:
            del _work_task_pre_save_data[instance.pk]


@receiver(pre_delete, sender=WorkTask)
def track_work_task_deletion(sender, instance, **kwargs):
    """Track when work tasks are deleted"""
    # Use pre_delete to ensure the ticket still exists when creating activity
    try:
        TicketActivity.objects.create(
            ticket=instance.ticket,
            activity_type='work_task_deleted',
            user=getattr(instance, '_deleted_by', None),
            description=f'Work task "{instance.title}" deleted'
        )
    except Ticket.DoesNotExist:
        # Ticket is being deleted too, so skip creating activity
        pass


@receiver(post_save, sender=TicketImage)
def track_image_addition(sender, instance, created, **kwargs):
    """Track when images are added"""
    if created:
        TicketActivity.objects.create(
            ticket=instance.ticket,
            activity_type='image_added',
            user=getattr(instance, '_uploaded_by', None),
            description='Image added to ticket'
        )


@receiver(pre_delete, sender=TicketImage)
def track_image_deletion(sender, instance, **kwargs):
    """Track when images are deleted"""
    # Use pre_delete to ensure the ticket still exists when creating activity
    try:
        TicketActivity.objects.create(
            ticket=instance.ticket,
            activity_type='image_deleted',
            user=getattr(instance, '_deleted_by', None),
            description='Image deleted from ticket'
        )
    except Ticket.DoesNotExist:
        # Ticket is being deleted too, so skip creating activity
        pass


@receiver(pre_save, sender=SiteVisit)
def store_site_visit_old_values(sender, instance, **kwargs):
    """Store old values before saving to compare changes"""
    if instance.pk:
        try:
            old_instance = SiteVisit.objects.get(pk=instance.pk)
            _site_visit_pre_save_data[instance.pk] = {
                'status': old_instance.status,
                'title': old_instance.title,
                'scheduled_date': old_instance.scheduled_date,
                'assigned_to': old_instance.assigned_to,
            }
        except SiteVisit.DoesNotExist:
            pass


@receiver(post_save, sender=SiteVisit)
def track_site_visit_changes(sender, instance, created, **kwargs):
    """Track site visit creation and changes"""
    
    if created:
        TicketActivity.objects.create(
            ticket=instance.ticket,
            activity_type='site_visit_created',
            user=instance.created_by,
            description=f'Site visit "{instance.title}" scheduled for {instance.scheduled_date.strftime("%b %d, %Y at %I:%M %p") if instance.scheduled_date else "TBD"}'
        )
    else:
        old_data = _site_visit_pre_save_data.get(instance.pk)
        if not old_data:
            return
        
        if old_data['status'] != instance.status:
            if instance.status == 'completed':
                TicketActivity.objects.create(
                    ticket=instance.ticket,
                    activity_type='site_visit_completed',
                    user=getattr(instance, '_changed_by', None),
                    description=f'Site visit "{instance.title}" marked as completed'
                )
            elif instance.status == 'cancelled':
                TicketActivity.objects.create(
                    ticket=instance.ticket,
                    activity_type='site_visit_cancelled',
                    user=getattr(instance, '_changed_by', None),
                    description=f'Site visit "{instance.title}" cancelled'
                )
            else:
                TicketActivity.objects.create(
                    ticket=instance.ticket,
                    activity_type='site_visit_updated',
                    user=getattr(instance, '_changed_by', None),
                    description=f'Site visit "{instance.title}" status changed to {instance.get_status_display()}'
                )
        elif old_data['title'] != instance.title or old_data['scheduled_date'] != instance.scheduled_date or old_data['assigned_to'] != instance.assigned_to:
            TicketActivity.objects.create(
                ticket=instance.ticket,
                activity_type='site_visit_updated',
                user=getattr(instance, '_changed_by', None),
                description=f'Site visit "{instance.title}" updated'
            )
        
        # Clean up old data after processing
        if instance.pk in _site_visit_pre_save_data:
            del _site_visit_pre_save_data[instance.pk]
