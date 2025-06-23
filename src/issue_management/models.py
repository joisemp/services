from django.db import models
from core.models import Organisation
from django.utils.text import slugify
from config.utils import generate_unique_slug

# Create your models here.

class Issue(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    voice = models.FileField(upload_to='issue_voices/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    org = models.ForeignKey(Organisation, related_name='issues', on_delete=models.CASCADE, null=True, blank=True)
    slug = models.SlugField(unique=True, db_index=True, blank=True)
    created_by = models.ForeignKey('core.User', related_name='created_issues', on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

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
