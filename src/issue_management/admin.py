from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Issue, IssueImage, IssueComment


class IssueImageInline(admin.TabularInline):
    model = IssueImage
    extra = 1
    fields = ['image', 'image_preview']
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="100" style="object-fit: cover;" />', obj.image.url)
        return 'No image'
    image_preview.short_description = 'Preview'


class IssueCommentInline(admin.TabularInline):
    model = IssueComment
    extra = 1
    fields = ['comment', 'created_at']
    readonly_fields = ['created_at']


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'status', 'priority', 'org', 'space', 
        'created_at', 'updated_at', 'has_voice', 'comment_count', 'image_count'
    ]
    list_filter = ['status', 'priority', 'org', 'space', 'created_at']
    search_fields = ['title', 'description', 'org__name', 'space__name']
    prepopulated_fields = {'slug': ('title',)}
    autocomplete_fields = ['org', 'space']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'slug')
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority')
        }),
        ('Organization & Space', {
            'fields': ('org', 'space')
        }),
        ('Media', {
            'fields': ('voice', 'voice_player'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'voice_player']
    
    inlines = [IssueImageInline, IssueCommentInline]
    
    def has_voice(self, obj):
        return bool(obj.voice)
    has_voice.boolean = True
    has_voice.short_description = 'Voice Recording'
    
    def comment_count(self, obj):
        return obj.comments.count()
    comment_count.short_description = 'Comments'
    
    def image_count(self, obj):
        return obj.images.count()
    image_count.short_description = 'Images'
    
    def voice_player(self, obj):
        if obj.voice:
            return format_html(
                '<audio controls style="width: 300px;"><source src="{}" type="audio/mpeg">Your browser does not support the audio element.</audio>',
                obj.voice.url
            )
        return 'No voice recording'
    voice_player.short_description = 'Voice Player'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('org', 'space').prefetch_related('comments', 'images')
    
    actions = ['mark_as_resolved', 'mark_as_closed', 'mark_as_in_progress']
    
    def mark_as_resolved(self, request, queryset):
        updated = queryset.update(status='resolved')
        self.message_user(request, f'{updated} issues marked as resolved.')
    mark_as_resolved.short_description = 'Mark selected issues as resolved'
    
    def mark_as_closed(self, request, queryset):
        updated = queryset.update(status='closed')
        self.message_user(request, f'{updated} issues marked as closed.')
    mark_as_closed.short_description = 'Mark selected issues as closed'
    
    def mark_as_in_progress(self, request, queryset):
        updated = queryset.update(status='in_progress')
        self.message_user(request, f'{updated} issues marked as in progress.')
    mark_as_in_progress.short_description = 'Mark selected issues as in progress'


@admin.register(IssueImage)
class IssueImageAdmin(admin.ModelAdmin):
    list_display = ['issue_title', 'image_preview', 'slug', 'issue_link']
    list_filter = ['issue__status', 'issue__org', 'issue__space']
    search_fields = ['issue__title', 'slug']
    autocomplete_fields = ['issue']
    
    def issue_title(self, obj):
        return obj.issue.title
    issue_title.short_description = 'Issue'
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="80" height="80" style="object-fit: cover;" />', obj.image.url)
        return 'No image'
    image_preview.short_description = 'Preview'
    
    def issue_link(self, obj):
        url = reverse('admin:issue_management_issue_change', args=[obj.issue.pk])
        return format_html('<a href="{}">View Issue</a>', url)
    issue_link.short_description = 'Issue Link'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('issue', 'issue__org', 'issue__space')


@admin.register(IssueComment)
class IssueCommentAdmin(admin.ModelAdmin):
    list_display = ['issue_title', 'comment_preview', 'created_at', 'issue_link']
    list_filter = ['created_at', 'issue__status', 'issue__org', 'issue__space']
    search_fields = ['comment', 'issue__title']
    autocomplete_fields = ['issue']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def issue_title(self, obj):
        return obj.issue.title
    issue_title.short_description = 'Issue'
    
    def comment_preview(self, obj):
        return obj.comment[:100] + '...' if len(obj.comment) > 100 else obj.comment
    comment_preview.short_description = 'Comment Preview'
    
    def issue_link(self, obj):
        url = reverse('admin:issue_management_issue_change', args=[obj.issue.pk])
        return format_html('<a href="{}">View Issue</a>', url)
    issue_link.short_description = 'Issue Link'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('issue', 'issue__org', 'issue__space')
