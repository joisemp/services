from django.db import models
from django.conf import settings
from core.models import Organisation
from django.utils.text import slugify
from django.utils import timezone
from datetime import timedelta
from config.utils import generate_unique_slug


def format_duration_detailed(duration):
    """Format duration with detailed seconds, minutes, hours"""
    if not duration:
        return "0 seconds"
    
    total_seconds = int(duration.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds > 0 or not parts:  # Show seconds if nothing else or if there are seconds
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    
    return ", ".join(parts)


def format_duration_compact(duration):
    """Format duration in H:MM:SS format"""
    if not duration:
        return "0:00:00"
    
    total_seconds = int(duration.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    return f"{hours}:{minutes:02d}:{seconds:02d}"


# Create your models here.

class IssueCategory(models.Model):
    """Categories for organizing issues"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#007bff', help_text="Hex color code for category")
    org = models.ForeignKey(Organisation, related_name='issue_categories', on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(max_length=100, unique=True, db_index=True, blank=True)
    
    class Meta:
        verbose_name_plural = "Issue Categories"
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.org}-{self.name}")
            self.slug = generate_unique_slug(self, base_slug, max_length=100)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} ({self.org.name})"

class Issue(models.Model):
    # Status choices
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('escalated', 'Escalated'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Priority choices
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    voice = models.FileField(upload_to='public/issue_voices/', blank=True, null=True)
    
    # New fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    category = models.ForeignKey(IssueCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='issues')
    
    # Due date and resolution
    due_date = models.DateTimeField(null=True, blank=True, help_text="Expected resolution date")
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True, help_text="Notes about how the issue was resolved")
    escalated_at = models.DateTimeField(null=True, blank=True)
    escalation_reason = models.TextField(blank=True, help_text="Reason for escalating the issue")
    escalation_count = models.PositiveIntegerField(default=0, help_text="Number of times this issue has been escalated")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Relationships
    org = models.ForeignKey(Organisation, related_name='issues', on_delete=models.CASCADE, null=True, blank=True)
    space = models.ForeignKey('service_management.Spaces', related_name='issues', on_delete=models.CASCADE, null=True, blank=True, help_text="Space where this issue was reported")
    created_by = models.ForeignKey('core.User', related_name='created_issues', on_delete=models.SET_NULL, null=True, blank=True)
    maintainer = models.ForeignKey('core.User', related_name='assigned_issues', on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'profile__user_type': 'maintainer'})
    escalated_by = models.ForeignKey('core.User', related_name='escalated_issues', on_delete=models.SET_NULL, null=True, blank=True, help_text="Maintainer who escalated the issue")
    
    # Slug for URLs
    slug = models.SlugField(max_length=100, unique=True, db_index=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        
    @property
    def is_overdue(self):
        """Check if issue is overdue"""
        from django.utils import timezone
        return self.due_date and self.due_date < timezone.now() and self.status in ['open', 'assigned', 'in_progress']
    
    @property
    def can_be_escalated(self):
        """Check if issue can be escalated by maintainer"""
        return self.status in ['assigned', 'in_progress'] and self.maintainer is not None
    
    @property
    def is_escalated(self):
        """Check if issue has been escalated"""
        return self.status == 'escalated'
    
    @property
    def was_previously_escalated(self):
        """Check if issue has escalation history (even if reassigned)"""
        return self.escalation_count > 0 or self.is_escalated
    
    @property
    def escalation_history(self):
        """Get all escalation events from status history"""
        return self.status_history.filter(new_status='escalated').order_by('-created_at')
    
    @property
    def status_color(self):
        """Get color for status badge"""
        colors = {
            'open': 'danger',
            'assigned': 'info',
            'in_progress': 'warning', 
            'resolved': 'success',
            'escalated': 'danger',
            'closed': 'secondary',
            'cancelled': 'dark'
        }
        return colors.get(self.status, 'secondary')
    
    @property
    def priority_color(self):
        """Get color for priority badge"""
        colors = {
            'low': 'success',
            'medium': 'info',
            'high': 'warning',
            'critical': 'danger'
        }
        return colors.get(self.priority, 'info')
    
    @property
    def total_work_time(self):
        """Calculate total time spent working on this issue"""
        total_time = timedelta()
        for session in self.work_sessions.all():
            if session.net_work_time:
                total_time += session.net_work_time
        return total_time
    
    @property
    def total_work_time_detailed(self):
        """Total work time in detailed format"""
        return format_duration_detailed(self.total_work_time)
    
    @property
    def total_work_time_compact(self):
        """Total work time in H:MM:SS format"""
        return format_duration_compact(self.total_work_time)
    
    @property
    def total_break_time(self):
        """Calculate total break time across all work sessions"""
        total_time = timedelta()
        for session in self.work_sessions.all():
            total_time += session.total_break_time
        return total_time
    
    @property
    def total_break_time_detailed(self):
        """Total break time in detailed format"""
        return format_duration_detailed(self.total_break_time)
    
    @property
    def total_break_time_compact(self):
        """Total break time in H:MM:SS format"""
        return format_duration_compact(self.total_break_time)
    
    @property
    def resolution_time(self):
        """Calculate time from creation to resolution"""
        if self.resolved_at:
            return self.resolved_at - self.created_at
        return None
    
    @property
    def resolution_time_detailed(self):
        """Resolution time in detailed format"""
        return format_duration_detailed(self.resolution_time)
    
    @property
    def resolution_time_compact(self):
        """Resolution time in H:MM:SS format"""
        return format_duration_compact(self.resolution_time)
    
    @property
    def current_work_session(self):
        """Get current active work session if any"""
        return self.work_sessions.filter(ended_at__isnull=True).first()
    
    @property
    def work_sessions_count(self):
        """Get total number of work sessions"""
        return self.work_sessions.count()
    
    @property
    def average_session_time(self):
        """Calculate average work session time"""
        sessions = self.work_sessions.filter(ended_at__isnull=False)
        if sessions.exists():
            total_time = sum([session.net_work_time for session in sessions], timedelta())
            return total_time / sessions.count()
        return timedelta()

    def save(self, *args, **kwargs):
        import logging
        logger = logging.getLogger(__name__)
        
        # Track if this is a new instance or if maintainer changed
        is_new = self.pk is None
        old_maintainer = None
        
        if not is_new:
            # Get the current state from database
            try:
                old_instance = Issue.objects.get(pk=self.pk)
                old_maintainer = old_instance.maintainer
            except Issue.DoesNotExist:
                old_instance = None
                
        # Auto-assign status when maintainer is assigned
        if self.maintainer and (is_new or old_maintainer != self.maintainer):
            # Only auto-change status if it's currently 'open' or if being reassigned
            if self.status == 'open' or (old_maintainer != self.maintainer and self.status in ['open', 'assigned']):
                self.status = 'assigned'
        elif not self.maintainer and old_maintainer and self.status == 'assigned':
            # If maintainer is removed and status is 'assigned', revert to 'open'
            self.status = 'open'
        
        # Set resolved_at when status changes to resolved
        if self.status == 'resolved' and not self.resolved_at:
            from django.utils import timezone
            self.resolved_at = timezone.now()
        elif self.status != 'resolved':
            self.resolved_at = None
        
        # Set escalated_at when status changes to escalated
        if self.status == 'escalated' and not self.escalated_at:
            from django.utils import timezone
            self.escalated_at = timezone.now()
        elif self.status != 'escalated':
            self.escalated_at = None
            
        # Generate slug if not exists
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = generate_unique_slug(self, base_slug, max_length=100)
        
        # Handle voice file validation before saving
        if self.voice:
            try:
                # Ensure voice file is accessible
                voice_size = self.voice.size
                logger.info(f"Voice file validated for issue: {self.title}, size: {voice_size}")
            except Exception as e:
                logger.error(f"Voice file validation failed for issue {self.title}: {str(e)}")
                # Don't raise error, just log it to avoid breaking the save
        
        try:
            super().save(*args, **kwargs)
            logger.info(f"Issue saved successfully: {self.title} (ID: {self.id})")
        except Exception as e:
            logger.error(f"Failed to save issue {self.title}: {str(e)}")
            raise e

    def __str__(self):
        return self.title

class IssueComment(models.Model):
    """Comments on issues for communication and activity tracking"""
    issue = models.ForeignKey(Issue, related_name='comments', on_delete=models.CASCADE)
    author = models.ForeignKey('core.User', on_delete=models.CASCADE)
    content = models.TextField()
    is_internal = models.BooleanField(default=False, help_text="Internal comments only visible to maintainers and admins")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(max_length=100, unique=True, db_index=True, blank=True)
    
    class Meta:
        ordering = ['created_at']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.issue.slug}-comment-{self.created_at}")
            self.slug = generate_unique_slug(self, base_slug, max_length=100)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Comment on {self.issue.title} by {self.author.profile.first_name}"

class IssueStatusHistory(models.Model):
    """Track status changes for issues"""
    issue = models.ForeignKey(Issue, related_name='status_history', on_delete=models.CASCADE)
    changed_by = models.ForeignKey('core.User', on_delete=models.CASCADE)
    old_status = models.CharField(max_length=20, choices=Issue.STATUS_CHOICES)
    new_status = models.CharField(max_length=20, choices=Issue.STATUS_CHOICES)
    old_priority = models.CharField(max_length=20, choices=Issue.PRIORITY_CHOICES, null=True, blank=True)
    new_priority = models.CharField(max_length=20, choices=Issue.PRIORITY_CHOICES, null=True, blank=True)
    old_maintainer = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='old_maintainer_history')
    new_maintainer = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='new_maintainer_history')
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(max_length=100, unique=True, db_index=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Issue Status Histories"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.issue.slug}-{self.old_status}-{self.new_status}")
            self.slug = generate_unique_slug(self, base_slug, max_length=100)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.issue.title} - {self.old_status} to {self.new_status}"
    
    def get_resolution_images(self):
        """Get resolution images associated with this status change"""
        if self.new_status == 'resolved':
            # Get images created around the same time as this status change (within 1 minute)
            from django.utils import timezone
            time_window = timezone.timedelta(minutes=1)
            start_time = self.created_at - time_window
            end_time = self.created_at + time_window
            
            return IssueResolutionImage.objects.filter(
                issue=self.issue,
                uploaded_at__gte=start_time,
                uploaded_at__lte=end_time
            )
        return IssueResolutionImage.objects.none()

class IssueImage(models.Model):
    issue = models.ForeignKey(Issue, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='public/issue_images/')
    slug = models.SlugField(max_length=100, unique=True, db_index=True, blank=True)

    def save(self, *args, **kwargs):
        from io import BytesIO
        from PIL import Image
        from django.core.files.base import ContentFile
        import logging

        logger = logging.getLogger(__name__)

        # Compress image if it's newly uploaded
        if self.image and not self.image.closed:
            try:
                logger.info(f"Processing image: {self.image.name}")
                img = Image.open(self.image)
                img_format = img.format if img.format else 'JPEG'
                
                # Convert to RGB if not already (for JPEG)
                if img_format == 'JPEG' and img.mode != 'RGB':
                    img = img.convert('RGB')
                
                buffer = BytesIO()
                img.save(buffer, format=img_format, quality=70, optimize=True)
                buffer.seek(0)
                
                # Replace the image with compressed version
                compressed_content = ContentFile(buffer.read(), name=self.image.name)
                self.image = compressed_content
                
                logger.info(f"Image compressed successfully: {self.image.name}")
                
            except Exception as e:
                logger.warning(f"Image compression failed for {self.image.name}: {str(e)}")
                # If compression fails, save original

        if not self.slug:
            base_slug = slugify(f"{self.issue.title}-image")
            self.slug = generate_unique_slug(self, base_slug, max_length=100)
        
        # Call the parent save method and ensure it completes
        try:
            super().save(*args, **kwargs)
            logger.info(f"IssueImage saved successfully: {self.slug}")
        except Exception as e:
            logger.error(f"Failed to save IssueImage {self.slug}: {str(e)}")
            raise e

    def __str__(self):
        return f"Image for {self.issue.title}"


class IssueResolutionImage(models.Model):
    """Images attached by maintainers when resolving issues"""
    issue = models.ForeignKey(Issue, related_name='resolution_images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='public/issue_resolution_images/')
    uploaded_by = models.ForeignKey('core.User', on_delete=models.CASCADE, limit_choices_to={'profile__user_type': 'maintainer'})
    description = models.CharField(max_length=255, blank=True, help_text="Optional description of the resolution image")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(max_length=100, unique=True, db_index=True, blank=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = "Issue Resolution Image"
        verbose_name_plural = "Issue Resolution Images"

    def save(self, *args, **kwargs):
        from io import BytesIO
        from PIL import Image
        from django.core.files.base import ContentFile

        # Compress image if it's newly uploaded
        if self.image and not self.image.closed:
            try:
                img = Image.open(self.image)
                img_format = img.format if img.format else 'JPEG'
                # Convert to RGB if not already (for JPEG)
                if img_format == 'JPEG' and img.mode != 'RGB':
                    img = img.convert('RGB')
                buffer = BytesIO()
                img.save(buffer, format=img_format, quality=70, optimize=True)
                buffer.seek(0)
                self.image = ContentFile(buffer.read(), name=self.image.name)
            except Exception as e:
                pass  # If compression fails, save original

        if not self.slug:
            base_slug = slugify(f"{self.issue.title}-resolution-image")
            self.slug = generate_unique_slug(self, base_slug, max_length=100)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Resolution image for {self.issue.title} by {self.uploaded_by.profile.first_name}"


class IssueWorkSession(models.Model):
    """Track individual work sessions on issues"""
    issue = models.ForeignKey(Issue, related_name='work_sessions', on_delete=models.CASCADE)
    maintainer = models.ForeignKey('core.User', on_delete=models.CASCADE, limit_choices_to={'profile__user_type': 'maintainer'})
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    total_work_time = models.DurationField(null=True, blank=True, help_text="Total time worked excluding breaks")
    total_break_time = models.DurationField(default=timedelta, help_text="Total time spent on breaks")
    session_notes = models.TextField(blank=True, help_text="Notes about work done in this session")
    is_focus_mode = models.BooleanField(default=False, help_text="Whether this session was in focus mode")
    slug = models.SlugField(max_length=100, unique=True, db_index=True, blank=True)
    
    class Meta:
        ordering = ['-started_at']
        verbose_name_plural = "Issue Work Sessions"
    
    @property
    def session_duration(self):
        """Total duration of the session including breaks"""
        if self.ended_at:
            return self.ended_at - self.started_at
        return timezone.now() - self.started_at
    
    @property
    def session_duration_detailed(self):
        """Total duration in detailed format"""
        return format_duration_detailed(self.session_duration)
    
    @property
    def session_duration_compact(self):
        """Total duration in H:MM:SS format"""
        return format_duration_compact(self.session_duration)
    
    @property
    def net_work_time(self):
        """Actual work time excluding breaks"""
        if self.total_work_time:
            return self.total_work_time
        return self.session_duration - self.total_break_time
    
    @property
    def net_work_time_detailed(self):
        """Actual work time in detailed format"""
        return format_duration_detailed(self.net_work_time)
    
    @property
    def net_work_time_compact(self):
        """Actual work time in H:MM:SS format"""
        return format_duration_compact(self.net_work_time)
    
    @property
    def total_break_time_detailed(self):
        """Total break time in detailed format"""
        return format_duration_detailed(self.total_break_time)
    
    @property
    def total_break_time_compact(self):
        """Total break time in H:MM:SS format"""
        return format_duration_compact(self.total_break_time)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.issue.slug}-session-{self.started_at}")
            self.slug = generate_unique_slug(self, base_slug, max_length=100)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Work session on {self.issue.title} by {self.maintainer.profile.first_name}"


class IssueBreakSession(models.Model):
    """Track individual break sessions during work"""
    work_session = models.ForeignKey(IssueWorkSession, related_name='breaks', on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)
    break_type = models.CharField(max_length=20, choices=[
        ('short', 'Short Break (5-15 min)'),
        ('medium', 'Medium Break (15-30 min)'),
        ('long', 'Long Break (30+ min)'),
        ('manual', 'Manual Break'),
    ], default='manual')
    slug = models.SlugField(max_length=100, unique=True, db_index=True, blank=True)
    
    class Meta:
        ordering = ['-started_at']
        verbose_name_plural = "Issue Break Sessions"
    
    @property
    def break_duration(self):
        """Calculate break duration"""
        if self.ended_at:
            return self.ended_at - self.started_at
        return timezone.now() - self.started_at
    
    @property
    def break_duration_detailed(self):
        """Break duration in detailed format"""
        return format_duration_detailed(self.break_duration)
    
    @property
    def break_duration_compact(self):
        """Break duration in H:MM:SS format"""
        return format_duration_compact(self.break_duration)
    
    def save(self, *args, **kwargs):
        # Set duration when break ends
        if self.ended_at and not self.duration:
            self.duration = self.ended_at - self.started_at
        
        if not self.slug:
            base_slug = slugify(f"{self.work_session.issue.slug}-break-{self.started_at}")
            self.slug = generate_unique_slug(self, base_slug, max_length=100)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Break during work on {self.work_session.issue.title}"
