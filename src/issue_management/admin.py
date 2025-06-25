from django.contrib import admin
from .models import Issue

@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ('title', 'org', 'created_by', 'maintainer', 'created_at')
    list_filter = ('org', 'maintainer')
    search_fields = ('title', 'description')
    autocomplete_fields = ['org', 'created_by', 'maintainer']
