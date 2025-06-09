from django.db import models

# Create your models here.

class Issue(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    voice = models.FileField(upload_to='issue_voices/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class IssueImage(models.Model):
    issue = models.ForeignKey(Issue, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='issue_images/')

    def __str__(self):
        return f"Image for {self.issue.title}"
