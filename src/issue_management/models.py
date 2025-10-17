from django.db import models
from django.utils import timezone
from datetime import timedelta
from config.utils import generate_unique_slug, generate_unique_code
from django.utils.text import slugify


class Issue(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('escalated', 'Escalated'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    title = models.CharField(max_length=200)
    description = models.TextField()
    reporter = models.ForeignKey('core.User', related_name='reported_issues', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    voice = models.FileField(upload_to='public/issue_voices/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    resolution_notes = models.TextField(blank=True, null=True, help_text="Notes describing how the issue was resolved")
    
    class Meta:
        ordering = ['-created_at']  # Default ordering, overridden in views with priority
    
    # Issue assignment fields
    assigned_to = models.ForeignKey(
        'core.User', 
        related_name='assigned_issues', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Supervisor assigned to handle this issue"
    )
    assigned_at = models.DateTimeField(null=True, blank=True, help_text="When the issue was assigned")
    assigned_by = models.ForeignKey(
        'core.User', 
        related_name='issues_assigned_by_me', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Who assigned this issue"
    )
    requires_review = models.BooleanField(
        default=False, 
        help_text="Whether this issue requires review before being marked as resolved"
    )
    reviewed_by = models.ForeignKey(
        'core.User', 
        related_name='reviewed_issues', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Who reviewed this issue (if review required)"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, help_text="When the issue was reviewed")
    review_notes = models.TextField(blank=True, null=True, help_text="Notes from the review process")
    reviewers = models.ManyToManyField(
        'core.User',
        related_name='issues_to_review',
        blank=True,
        help_text="Users assigned to review this issue when requires_review is checked"
    )
    
    org = models.ForeignKey('core.Organization', related_name='issues', on_delete=models.CASCADE)
    space = models.ForeignKey('core.Space', related_name='issues', on_delete=models.CASCADE, blank=True, null=True)
    slug = models.SlugField(unique=True)
     
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
        
    def __str__(self):
        return self.title
    

class IssueImage(models.Model):
    issue = models.ForeignKey(Issue, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='public/issue_images/')
    slug = models.SlugField(unique=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.image.name)
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Image for Issue: {self.issue.title}"
    
    
class IssueComment(models.Model):
    issue = models.ForeignKey(Issue, related_name='comments', on_delete=models.CASCADE)
    user = models.ForeignKey('core.User', related_name='issue_comments', on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True)
    
    class Meta:
        ordering = ['created_at']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.issue.title}-comment")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"Comment by {self.user.get_full_name() or self.user} on Issue: {self.issue.title}"
    

class WorkTask(models.Model):
    issue = models.ForeignKey(Issue, related_name='work_tasks', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    resolution_notes = models.TextField(blank=True, null=True)
    assigned_to = models.ForeignKey('core.User', related_name='work_tasks', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_date = models.DateTimeField(blank=True, null=True)
    completed = models.BooleanField(default=False)
    slug = models.SlugField(unique=True)
    
    class Meta:
        ordering = ['completed', 'due_date']  # Incomplete first, then by due date
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
        
    def __str__(self):
        return self.title


class WorkTaskResolutionImage(models.Model):
    """Images attached to work task resolutions"""
    work_task = models.ForeignKey(WorkTask, related_name='resolution_images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='public/work_task_resolution_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True)
    
    class Meta:
        ordering = ['uploaded_at']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.work_task.title}-resolution-image")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Resolution Image for Work Task: {self.work_task.title}"


class IssueResolutionImage(models.Model):
    """Images attached to issue resolutions"""
    issue = models.ForeignKey(Issue, related_name='resolution_images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='public/issue_resolution_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True)
    
    class Meta:
        ordering = ['uploaded_at']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.issue.title}-resolution-image")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Resolution Image for Issue: {self.issue.title}"


class WorkTaskShare(models.Model):
    """
    Model for sharing work tasks with external people via temporary links.
    Allows controlled access to work tasks for people outside the organization.
    """
    PERMISSION_CHOICES = [
        ('view_only', 'View Only'),
        ('comment', 'View and Comment'),
        ('collaborate', 'View, Comment, and Update Status'),
    ]
    
    work_task = models.ForeignKey(WorkTask, related_name='shares', on_delete=models.CASCADE)
    share_token = models.CharField(max_length=32, unique=True, db_index=True)
    created_by = models.ForeignKey('core.User', related_name='created_task_shares', on_delete=models.CASCADE)
    
    # External recipient info (optional - for tracking)
    recipient_email = models.EmailField(blank=True, null=True, help_text="Email of external recipient (optional)")
    recipient_name = models.CharField(max_length=100, blank=True, null=True, help_text="Name of external recipient (optional)")
    
    # Access control
    permission_level = models.CharField(max_length=20, choices=PERMISSION_CHOICES, default='view_only')
    is_active = models.BooleanField(default=True)
    
    # Time-based access control
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="When this share link expires")
    last_accessed = models.DateTimeField(null=True, blank=True)
    access_count = models.PositiveIntegerField(default=0)
    max_access_count = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum number of times this link can be accessed")
    
    # Additional options
    allow_download_attachments = models.BooleanField(default=True)
    password_protected = models.BooleanField(default=False)
    access_password = models.CharField(max_length=50, blank=True, null=True, help_text="Optional password for additional security")
    
    # Tracking
    notes = models.TextField(blank=True, null=True, help_text="Internal notes about this share")
    
    class Meta:
        verbose_name = 'Work Task Share'
        verbose_name_plural = 'Work Task Shares'
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.share_token:
            # Generate a unique 32-character token
            self.share_token = generate_unique_code(self, no_of_char=32, unique_field='share_token')
        
        # Set default expiration if not provided (7 days from creation)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
            
        super().save(*args, **kwargs)
    
    def is_valid(self):
        """Check if the share link is still valid"""
        if not self.is_active:
            return False
        
        if self.expires_at and timezone.now() > self.expires_at:
            return False
            
        if self.max_access_count and self.access_count >= self.max_access_count:
            return False
            
        return True
    
    def record_access(self):
        """Record an access to this shared link"""
        self.last_accessed = timezone.now()
        self.access_count += 1
        self.save(update_fields=['last_accessed', 'access_count'])
    
    def get_absolute_url(self):
        """Get the public URL for this shared work task"""
        from django.urls import reverse
        return reverse('issue_management:shared_work_task', kwargs={'token': self.share_token})
    
    def get_full_url(self, request=None):
        """Get the full URL including domain"""
        if request:
            return request.build_absolute_uri(self.get_absolute_url())
        return self.get_absolute_url()
    
    def extend_expiration(self, days=7):
        """Extend the expiration by specified number of days"""
        if self.expires_at:
            self.expires_at = max(timezone.now(), self.expires_at) + timedelta(days=days)
        else:
            self.expires_at = timezone.now() + timedelta(days=days)
        self.save(update_fields=['expires_at'])
    
    def deactivate(self):
        """Deactivate this share link"""
        self.is_active = False
        self.save(update_fields=['is_active'])
    
    @property
    def is_expired(self):
        """Check if the share has expired"""
        return self.expires_at and timezone.now() > self.expires_at
    
    @property
    def days_until_expiration(self):
        """Get number of days until expiration"""
        if not self.expires_at:
            return None
        delta = self.expires_at - timezone.now()
        return max(0, delta.days)
    
    def __str__(self):
        recipient = self.recipient_email or self.recipient_name or "Anonymous"
        return f"Share of '{self.work_task.title}' with {recipient}"


class SiteVisit(models.Model):
    """
    Model for site visits where supervisors assign maintainers or other supervisors
    to visit a site for an issue. Each issue can have multiple site visits.
    """
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    issue = models.ForeignKey(Issue, related_name='site_visits', on_delete=models.CASCADE)
    title = models.CharField(max_length=200, help_text="Brief description of the site visit purpose")
    description = models.TextField(help_text="Detailed description of what needs to be done during the visit")
    location = models.CharField(max_length=300, default='Location to be specified', help_text="Location/address where the site visit will take place")
    
    # Assignment fields
    created_by = models.ForeignKey(
        'core.User', 
        related_name='created_site_visits', 
        on_delete=models.CASCADE,
        help_text="Supervisor who created this site visit"
    )
    assigned_to = models.ForeignKey(
        'core.User',
        related_name='assigned_site_visits',
        on_delete=models.CASCADE,
        help_text="Maintainer or supervisor assigned to perform the visit"
    )
    
    # Scheduling
    scheduled_date = models.DateTimeField(help_text="When the site visit is scheduled")
    estimated_duration = models.DurationField(
        null=True, 
        blank=True,
        help_text="Estimated duration of the site visit"
    )
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    started_at = models.DateTimeField(null=True, blank=True, help_text="When the visit actually started")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="When the visit was completed")
    
    # Visit details
    findings = models.TextField(
        blank=True, 
        null=True,
        help_text="Findings and observations from the site visit"
    )
    actions_taken = models.TextField(
        blank=True,
        null=True,
        help_text="Actions taken during the site visit"
    )
    recommendations = models.TextField(
        blank=True,
        null=True,
        help_text="Recommendations for follow-up actions"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Slug for URL
    slug = models.SlugField(unique=True)
    
    class Meta:
        ordering = ['-scheduled_date']
        verbose_name = 'Site Visit'
        verbose_name_plural = 'Site Visits'
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.issue.title}-site-visit")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    def mark_in_progress(self):
        """Mark the site visit as in progress"""
        if self.status == 'scheduled':
            self.status = 'in_progress'
            self.started_at = timezone.now()
            self.save(update_fields=['status', 'started_at', 'updated_at'])
    
    def mark_completed(self):
        """Mark the site visit as completed"""
        if self.status in ['scheduled', 'in_progress']:
            self.status = 'completed'
            self.completed_at = timezone.now()
            if not self.started_at:
                self.started_at = self.completed_at
            self.save(update_fields=['status', 'started_at', 'completed_at', 'updated_at'])
    
    def cancel(self):
        """Cancel the site visit"""
        if self.status in ['scheduled', 'in_progress']:
            self.status = 'cancelled'
            self.save(update_fields=['status', 'updated_at'])
    
    @property
    def is_overdue(self):
        """Check if the site visit is overdue"""
        if self.status == 'scheduled' and self.scheduled_date:
            return timezone.now() > self.scheduled_date
        return False
    
    @property
    def duration(self):
        """Calculate actual duration of the visit if completed"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    def __str__(self):
        return f"Site Visit: {self.title} for {self.issue.title}"


class SiteVisitImage(models.Model):
    """Images captured during site visits"""
    site_visit = models.ForeignKey(SiteVisit, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='public/site_visit_images/')
    caption = models.CharField(max_length=200, blank=True, null=True, help_text="Optional caption for the image")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True)
    
    class Meta:
        ordering = ['uploaded_at']
        verbose_name = 'Site Visit Image'
        verbose_name_plural = 'Site Visit Images'
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.site_visit.title}-image")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Image for Site Visit: {self.site_visit.title}"


# Signal to automatically delete image files when WorkTaskResolutionImage is deleted
from django.db.models.signals import pre_delete
from django.dispatch import receiver

@receiver(pre_delete, sender=WorkTaskResolutionImage)
def delete_resolution_image_file(sender, instance, **kwargs):
    """
    Delete the image file from storage when a WorkTaskResolutionImage instance is deleted.
    This ensures orphaned files don't accumulate in storage.
    """
    if instance.image:
        # Delete the file from storage
        instance.image.delete(save=False)


@receiver(pre_delete, sender=IssueImage)
def delete_issue_image_file(sender, instance, **kwargs):
    """
    Delete the image file from storage when an IssueImage instance is deleted.
    This ensures orphaned files don't accumulate in storage.
    """
    if instance.image:
        # Delete the file from storage
        instance.image.delete(save=False)


@receiver(pre_delete, sender=IssueResolutionImage)
def delete_issue_resolution_image_file(sender, instance, **kwargs):
    """
    Delete the image file from storage when an IssueResolutionImage instance is deleted.
    This ensures orphaned files don't accumulate in storage.
    """
    if instance.image:
        # Delete the file from storage
        instance.image.delete(save=False)


@receiver(pre_delete, sender=SiteVisitImage)
def delete_site_visit_image_file(sender, instance, **kwargs):
    """
    Delete the image file from storage when a SiteVisitImage instance is deleted.
    This ensures orphaned files don't accumulate in storage.
    """
    if instance.image:
        # Delete the file from storage
        instance.image.delete(save=False)
