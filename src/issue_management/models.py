from django.db import models
from config.utils import generate_unique_slug
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    voice = models.FileField(upload_to='public/issue_voices/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    org = models.ForeignKey('core.Organization', related_name='issues', on_delete=models.CASCADE)
    space = models.ForeignKey('core.Space', related_name='issues', on_delete=models.CASCADE)
    slug = models.SlugField(unique=True)
     
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = generate_unique_slug(base_slug)
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
            self.slug = generate_unique_slug(base_slug)
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
            base_slug = slugify(f"{self.issue.title}-{self.created_at}")
            self.slug = generate_unique_slug(base_slug)
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"Comment on Issue: {self.issue.title}"
    
