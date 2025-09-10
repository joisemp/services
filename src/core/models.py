from django.db import models
from config.utils import generate_unique_slug
from django.utils.text import slugify


class Organization(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    address_line_one = models.CharField(max_length=255, blank=True, null=True)
    address_line_two = models.CharField(max_length=255, blank=True, null=True)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = generate_unique_slug(base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    
class Space(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    org = models.ForeignKey(Organization, related_name='spaces', on_delete=models.CASCADE)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = generate_unique_slug(base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.org.name})"
