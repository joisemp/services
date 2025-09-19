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
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.issue.title}-comment")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"Comment on Issue: {self.issue.title}"
    

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
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
        
    def __str__(self):
        return self.title


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


