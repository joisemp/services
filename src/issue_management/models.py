from django.db import models
from django.utils import timezone
from datetime import timedelta
from config.utils import generate_unique_slug, generate_unique_code, compress_image
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
    issue_id = models.CharField(max_length=20, unique=True, help_text="Unique identifier for the issue")
    slug = models.SlugField(unique=True)
     
    def save(self, *args, **kwargs):
        if not self.issue_id:
            # Generate unique issue_id using org prefix and unique code
            org_prefix = self.org.name[:3].upper() if self.org else 'ISS'
            self.issue_id = f"{org_prefix}-{generate_unique_code(Issue, no_of_char=6, unique_field='issue_id')}"
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
            # Generate slug using unique code instead of filename
            self.slug = generate_unique_code(self, no_of_char=12, unique_field='slug')
        
        # Compress and convert image to WebP with unique alphanumeric name if it's a new upload or has been changed
        if self.image and (not self.pk or self._state.adding):
            self.image = compress_image(
                self.image, 
                max_width=1920, 
                max_height=1920, 
                quality=85, 
                format='WEBP',
                upload_path='public/issue_images/'
            )
        
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
            # Generate slug using unique code instead of filename
            self.slug = generate_unique_code(self, no_of_char=12, unique_field='slug')
        
        # Compress and convert image to WebP with unique alphanumeric name if it's a new upload or has been changed
        if self.image and (not self.pk or self._state.adding):
            self.image = compress_image(
                self.image, 
                max_width=1920, 
                max_height=1920, 
                quality=85, 
                format='WEBP',
                upload_path='public/work_task_resolution_images/'
            )
        
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
            # Generate slug using unique code instead of filename
            self.slug = generate_unique_code(self, no_of_char=12, unique_field='slug')
        
        # Compress and convert image to WebP with unique alphanumeric name if it's a new upload or has been changed
        if self.image and (not self.pk or self._state.adding):
            self.image = compress_image(
                self.image, 
                max_width=1920, 
                max_height=1920, 
                quality=85, 
                format='WEBP',
                upload_path='public/issue_resolution_images/'
            )
        
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
            # Generate slug using unique code instead of filename
            self.slug = generate_unique_code(self, no_of_char=12, unique_field='slug')
        
        # Compress and convert image to WebP with unique alphanumeric name if it's a new upload or has been changed
        if self.image and (not self.pk or self._state.adding):
            self.image = compress_image(
                self.image, 
                max_width=1920, 
                max_height=1920, 
                quality=85, 
                format='WEBP',
                upload_path='public/site_visit_images/'
            )
        
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


class IssueReviewComment(models.Model):
    """
    Review comments for issues. These are different from regular comments
    and are specifically for reviewers to provide feedback and review notes.
    """
    issue = models.ForeignKey(Issue, related_name='review_comments', on_delete=models.CASCADE)
    user = models.ForeignKey('core.User', related_name='issue_review_comments', on_delete=models.CASCADE)
    comment = models.TextField(help_text="Review comment or feedback")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(unique=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Issue Review Comment'
        verbose_name_plural = 'Issue Review Comments'
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.issue.title}-review-comment")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"Review Comment by {self.user.get_full_name() or self.user} on Issue: {self.issue.title}"


class IssueReviewCommentImage(models.Model):
    """Images attached to review comments"""
    review_comment = models.ForeignKey(IssueReviewComment, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='public/review_comment_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True)
    
    class Meta:
        ordering = ['uploaded_at']
        verbose_name = 'Review Comment Image'
        verbose_name_plural = 'Review Comment Images'
    
    def save(self, *args, **kwargs):
        if not self.slug:
            # Generate slug using unique code instead of filename
            self.slug = generate_unique_code(self, no_of_char=12, unique_field='slug')
        
        # Compress and convert image to WebP with unique alphanumeric name if it's a new upload or has been changed
        if self.image and (not self.pk or self._state.adding):
            self.image = compress_image(
                self.image, 
                max_width=1920, 
                max_height=1920, 
                quality=85, 
                format='WEBP',
                upload_path='public/review_comment_images/'
            )
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Image for Review Comment on Issue: {self.review_comment.issue.title}"


@receiver(pre_delete, sender=IssueReviewCommentImage)
def delete_review_comment_image_file(sender, instance, **kwargs):
    """
    Delete the image file from storage when an IssueReviewCommentImage instance is deleted.
    This ensures orphaned files don't accumulate in storage.
    """
    if instance.image:
        # Delete the file from storage
        instance.image.delete(save=False)


class IssueActivity(models.Model):
    """
    Tracks all activities/changes made to an issue for audit and history purposes.
    Excludes comments as they have their own display section.
    """
    ACTIVITY_TYPES = [
        ('created', 'Issue Created'),
        ('status_changed', 'Status Changed'),
        ('priority_changed', 'Priority Changed'),
        ('assigned', 'Issue Assigned'),
        ('reassigned', 'Issue Reassigned'),
        ('unassigned', 'Issue Unassigned'),
        ('updated', 'Issue Updated'),
        ('resolved', 'Issue Resolved'),
        ('reopened', 'Issue Reopened'),
        ('closed', 'Issue Closed'),
        ('cancelled', 'Issue Cancelled'),
        ('escalated', 'Issue Escalated'),
        ('review_requested', 'Review Requested'),
        ('reviewed', 'Issue Reviewed'),
        ('work_task_created', 'Work Task Created'),
        ('work_task_updated', 'Work Task Updated'),
        ('work_task_completed', 'Work Task Completed'),
        ('work_task_reopened', 'Work Task Reopened'),
        ('work_task_deleted', 'Work Task Deleted'),
        ('site_visit_created', 'Site Visit Created'),
        ('site_visit_updated', 'Site Visit Updated'),
        ('site_visit_completed', 'Site Visit Completed'),
        ('site_visit_cancelled', 'Site Visit Cancelled'),
        ('purchase_request_created', 'Purchase Request Created'),
        ('purchase_request_approved', 'Purchase Request Approved'),
        ('purchase_request_rejected', 'Purchase Request Rejected'),
        ('purchase_request_deleted', 'Purchase Request Deleted'),
        ('image_added', 'Image Added'),
        ('image_deleted', 'Image Deleted'),
        ('voice_added', 'Voice Recording Added'),
        ('voice_deleted', 'Voice Recording Deleted'),
    ]
    
    issue = models.ForeignKey(Issue, related_name='activities', on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPES)
    user = models.ForeignKey('core.User', related_name='issue_activities', on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(help_text="Detailed description of what changed")
    old_value = models.TextField(blank=True, null=True, help_text="Previous value (if applicable)")
    new_value = models.TextField(blank=True, null=True, help_text="New value (if applicable)")
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Issue Activity'
        verbose_name_plural = 'Issue Activities'
        indexes = [
            models.Index(fields=['issue', '-created_at']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.issue.slug}-activity")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.issue.title}"


class PurchaseRequest(models.Model):
    """
    Purchase requests created by space admins for issue-related expenses.
    Central admins can approve/reject these requests.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    issue = models.ForeignKey(Issue, related_name='purchase_requests', on_delete=models.CASCADE)
    org = models.ForeignKey('core.Organization', related_name='purchase_requests', on_delete=models.CASCADE)
    space = models.ForeignKey('core.Space', related_name='purchase_requests', on_delete=models.CASCADE, null=True, blank=True)
    
    item = models.CharField(max_length=300, help_text="Name/description of the item to purchase")
    quantity = models.PositiveIntegerField(help_text="Number of units needed")
    description = models.TextField(blank=True, null=True, help_text="Additional notes or details about the purchase request")
    estimated_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Estimated cost in currency (optional)")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Request tracking
    requested_by = models.ForeignKey('core.User', related_name='purchase_requests_created', on_delete=models.CASCADE)
    requested_at = models.DateTimeField(auto_now_add=True)
    
    # Approval tracking
    reviewed_by = models.ForeignKey('core.User', related_name='purchase_requests_reviewed', on_delete=models.SET_NULL, null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, null=True, help_text="Notes from central admin when approving/rejecting")
    
    slug = models.SlugField(unique=True)
    
    class Meta:
        ordering = ['-requested_at']
        verbose_name = 'Purchase Request'
        verbose_name_plural = 'Purchase Requests'
        indexes = [
            models.Index(fields=['issue', '-requested_at']),
            models.Index(fields=['status', '-requested_at']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.item}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.item} (x{self.quantity}) - {self.get_status_display()}"


class ShoppingList(models.Model):
    """
    Shopping lists generated from approved purchase requests.
    Allows central admins to save and reference shopping lists.
    """
    title = models.CharField(max_length=200, help_text="Title/name for this shopping list")
    org = models.ForeignKey('core.Organization', related_name='shopping_lists', on_delete=models.CASCADE)
    
    # Generation tracking
    generated_by = models.ForeignKey('core.User', related_name='shopping_lists_created', on_delete=models.CASCADE)
    generated_at = models.DateTimeField(auto_now_add=True)
    
    # Summary fields
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Total estimated amount for all items")
    item_count = models.PositiveIntegerField(default=0, help_text="Total number of purchase requests in this list")
    
    slug = models.SlugField(unique=True)
    
    class Meta:
        ordering = ['-generated_at']
        verbose_name = 'Shopping List'
        verbose_name_plural = 'Shopping Lists'
        indexes = [
            models.Index(fields=['org', '-generated_at']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.title}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.title} - {self.generated_at.strftime('%Y-%m-%d')}"


class ShoppingListItem(models.Model):
    """
    Individual purchase requests included in a shopping list.
    Links shopping lists to their constituent purchase requests.
    """
    shopping_list = models.ForeignKey(ShoppingList, related_name='items', on_delete=models.CASCADE)
    purchase_request = models.ForeignKey(PurchaseRequest, related_name='shopping_list_items', on_delete=models.CASCADE)
    
    # Store snapshot of values at time of list generation
    item_snapshot = models.CharField(max_length=300, help_text="Item name at time of list generation")
    quantity_snapshot = models.PositiveIntegerField(help_text="Quantity at time of list generation")
    amount_snapshot = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Amount at time of list generation")
    space_name = models.CharField(max_length=200, help_text="Space name at time of list generation")
    issue_title = models.CharField(max_length=200, help_text="Issue title at time of list generation")
    
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['space_name', 'item_snapshot']
        verbose_name = 'Shopping List Item'
        verbose_name_plural = 'Shopping List Items'
        indexes = [
            models.Index(fields=['shopping_list', 'space_name']),
        ]
    
    def __str__(self):
        return f"{self.item_snapshot} in {self.shopping_list.title}"
