from django.db import models

# Create your models here.

class Issue(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to='issue_images/', blank=True, null=True)
    voice = models.FileField(upload_to='issue_voices/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
