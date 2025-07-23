from django.contrib import admin
from .models import Issue, IssueCategory, IssueComment, IssueStatusHistory

@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'priority', 'category', 'org', 'created_by', 'maintainer', 'escalated_by', 'created_at')
    list_filter = ('status', 'priority', 'category', 'org', 'maintainer', 'escalated_by', 'created_at')
    search_fields = ('title', 'description', 'escalation_reason')
    autocomplete_fields = ['org', 'created_by', 'maintainer', 'escalated_by', 'category', 'space']
    readonly_fields = ('slug', 'created_at', 'updated_at', 'resolved_at', 'escalated_at')
    
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'voice')
        }),
        ('Classification', {
            'fields': ('status', 'priority', 'category', 'due_date')
        }),
        ('Assignment', {
            'fields': ('org', 'space', 'created_by', 'maintainer')
        }),
        ('Escalation', {
            'fields': ('escalated_by', 'escalated_at', 'escalation_reason', 'escalation_count'),
            'classes': ('collapse',)
        }),
        ('Resolution', {
            'fields': ('resolution_notes', 'resolved_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('slug', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(IssueCategory)
class IssueCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'org', 'color', 'is_active', 'issues_count', 'created_at')
    list_filter = ('org', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('slug', 'created_at')
    
    def issues_count(self, obj):
        return obj.issues.count()
    issues_count.short_description = 'Issues'

@admin.register(IssueComment)
class IssueCommentAdmin(admin.ModelAdmin):
    list_display = ('issue', 'author', 'is_internal', 'created_at')
    list_filter = ('is_internal', 'created_at', 'issue__org')
    search_fields = ('content', 'issue__title')
    readonly_fields = ('slug', 'created_at', 'updated_at')

@admin.register(IssueStatusHistory)
class IssueStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('issue', 'old_status', 'new_status', 'changed_by', 'created_at')
    list_filter = ('old_status', 'new_status', 'created_at', 'issue__org')
    search_fields = ('issue__title', 'comment')
    readonly_fields = ('slug', 'created_at')
