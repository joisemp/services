from django.db import models
from django.utils.text import slugify

from config.utils import generate_unique_slug
from core.models import Organisation

# Create your models here.

class WorkCategory(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    org = models.ForeignKey(Organisation, related_name='work_categories', on_delete=models.CASCADE)
    slug = models.SlugField(unique=True, db_index=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
