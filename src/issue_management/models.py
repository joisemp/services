from django.db import models
from django.conf import settings
from core.models import Organisation
from django.utils.text import slugify
from config.utils import generate_unique_slug

# Create your models here.

class IssueCategory(models.Model):
    """Categories for organizing issues"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#007bff', help_text="Hex color code for category")
    org = models.ForeignKey(Organisation, related_name='issue_categories', on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True, db_index=True, blank=True)
    
    class Meta:
        verbose_name_plural = "Issue Categories"
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.org}-{self.name}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} ({self.org.name})"

class Issue(models.Model):
    # Status choices
    STATUS_CHOICES = [
        ('open', 'Open'),
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
    voice = models.FileField(upload_to='issue_voices/', blank=True, null=True)
    
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
    slug = models.SlugField(unique=True, db_index=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        
    @property
    def is_overdue(self):
        """Check if issue is overdue"""
        from django.utils import timezone
        return self.due_date and self.due_date < timezone.now() and self.status in ['open', 'in_progress']
    
    @property
    def can_be_escalated(self):
        """Check if issue can be escalated by maintainer"""
        return self.status == 'in_progress' and self.maintainer is not None
    
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

    def save(self, *args, **kwargs):
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
            
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

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
    slug = models.SlugField(unique=True, db_index=True, blank=True)
    
    class Meta:
        ordering = ['created_at']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.issue.slug}-comment-{self.created_at}")
            self.slug = generate_unique_slug(self, base_slug)
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
    slug = models.SlugField(unique=True, db_index=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Issue Status Histories"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.issue.slug}-{self.old_status}-{self.new_status}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.issue.title} - {self.old_status} to {self.new_status}"

class IssueImage(models.Model):
    issue = models.ForeignKey(Issue, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='issue_images/')
    slug = models.SlugField(unique=True, db_index=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.issue.title}-image")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Image for {self.issue.title}"
