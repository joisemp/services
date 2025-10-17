from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Issue, IssueImage, IssueComment, WorkTask, WorkTaskResolutionImage, 
    WorkTaskShare, SiteVisit, SiteVisitImage, IssueReviewComment, IssueReviewCommentImage
)


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


class WorkTaskResolutionImageInline(admin.TabularInline):
    model = WorkTaskResolutionImage
    extra = 1
    fields = ['image', 'image_preview', 'uploaded_at']
    readonly_fields = ['image_preview', 'uploaded_at']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="100" style="object-fit: cover;" />', obj.image.url)
        return 'No image'
    image_preview.short_description = 'Preview'


@admin.register(WorkTask)
class WorkTaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'issue', 'assigned_to', 'completed', 'due_date', 'created_at', 'resolution_image_count']
    list_filter = ['completed', 'created_at', 'due_date', 'issue__org']
    search_fields = ['title', 'description', 'issue__title']
    autocomplete_fields = ['issue', 'assigned_to']
    date_hierarchy = 'created_at'
    ordering = ['completed', 'due_date']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'slug')
        }),
        ('Assignment', {
            'fields': ('issue', 'assigned_to', 'due_date')
        }),
        ('Completion Status', {
            'fields': ('completed', 'resolution_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    inlines = [WorkTaskResolutionImageInline]
    
    def resolution_image_count(self, obj):
        return obj.resolution_images.count()
    resolution_image_count.short_description = 'Resolution Images'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('issue', 'assigned_to').prefetch_related('resolution_images')
    
    actions = ['mark_as_completed', 'mark_as_incomplete']
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(completed=True)
        self.message_user(request, f'{updated} tasks marked as completed.')
    mark_as_completed.short_description = 'Mark selected tasks as completed'
    
    def mark_as_incomplete(self, request, queryset):
        updated = queryset.update(completed=False)
        self.message_user(request, f'{updated} tasks marked as incomplete.')
    mark_as_incomplete.short_description = 'Mark selected tasks as incomplete'


@admin.register(WorkTaskResolutionImage)
class WorkTaskResolutionImageAdmin(admin.ModelAdmin):
    list_display = ['work_task_title', 'image_preview', 'uploaded_at', 'work_task_link']
    list_filter = ['uploaded_at', 'work_task__issue__org']
    search_fields = ['work_task__title', 'work_task__issue__title']
    autocomplete_fields = ['work_task']
    date_hierarchy = 'uploaded_at'
    ordering = ['-uploaded_at']
    
    def work_task_title(self, obj):
        return obj.work_task.title
    work_task_title.short_description = 'Work Task'
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="80" height="80" style="object-fit: cover;" />', obj.image.url)
        return 'No image'
    image_preview.short_description = 'Preview'
    
    def work_task_link(self, obj):
        url = reverse('admin:issue_management_worktask_change', args=[obj.work_task.pk])
        return format_html('<a href="{}">View Work Task</a>', url)
    work_task_link.short_description = 'Work Task Link'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('work_task', 'work_task__issue', 'work_task__issue__org')


@admin.register(WorkTaskShare)
class WorkTaskShareAdmin(admin.ModelAdmin):
    list_display = ['work_task', 'recipient_info', 'permission_level', 'is_active', 'is_expired', 'access_count', 'created_at', 'expires_at']
    list_filter = ['is_active', 'permission_level', 'created_at', 'expires_at']
    search_fields = ['work_task__title', 'recipient_email', 'recipient_name', 'share_token']
    autocomplete_fields = ['work_task', 'created_by']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    readonly_fields = ['share_token', 'access_count', 'last_accessed', 'created_at', 'get_share_url']
    
    fieldsets = (
        ('Work Task', {
            'fields': ('work_task', 'created_by')
        }),
        ('Recipient Information', {
            'fields': ('recipient_email', 'recipient_name')
        }),
        ('Access Control', {
            'fields': ('permission_level', 'is_active', 'password_protected', 'access_password', 'allow_download_attachments')
        }),
        ('Time Control', {
            'fields': ('expires_at', 'max_access_count')
        }),
        ('Tracking', {
            'fields': ('share_token', 'access_count', 'last_accessed', 'created_at', 'get_share_url'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def recipient_info(self, obj):
        if obj.recipient_email and obj.recipient_name:
            return f'{obj.recipient_name} ({obj.recipient_email})'
        elif obj.recipient_email:
            return obj.recipient_email
        elif obj.recipient_name:
            return obj.recipient_name
        return 'Anonymous'
    recipient_info.short_description = 'Recipient'
    
    def get_share_url(self, obj):
        if obj.pk:
            return format_html('<a href="{}" target="_blank">{}</a>', obj.get_absolute_url(), obj.get_absolute_url())
        return 'Save to generate URL'
    get_share_url.short_description = 'Share URL'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('work_task', 'work_task__issue', 'created_by')
    
    actions = ['deactivate_shares', 'extend_expiration_7_days', 'extend_expiration_30_days']
    
    def deactivate_shares(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} shares deactivated.')
    deactivate_shares.short_description = 'Deactivate selected shares'
    
    def extend_expiration_7_days(self, request, queryset):
        from datetime import timedelta
        from django.utils import timezone
        for share in queryset:
            share.extend_expiration(days=7)
        self.message_user(request, f'Extended expiration by 7 days for {queryset.count()} shares.')
    extend_expiration_7_days.short_description = 'Extend expiration by 7 days'
    
    def extend_expiration_30_days(self, request, queryset):
        from datetime import timedelta
        from django.utils import timezone
        for share in queryset:
            share.extend_expiration(days=30)
        self.message_user(request, f'Extended expiration by 30 days for {queryset.count()} shares.')
    extend_expiration_30_days.short_description = 'Extend expiration by 30 days'


class SiteVisitImageInline(admin.TabularInline):
    model = SiteVisitImage
    extra = 1
    fields = ['image', 'caption', 'image_preview', 'uploaded_at']
    readonly_fields = ['image_preview', 'uploaded_at']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="100" style="object-fit: cover;" />', obj.image.url)
        return 'No image'
    image_preview.short_description = 'Preview'


@admin.register(SiteVisit)
class SiteVisitAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'issue', 'status', 'created_by', 'assigned_to', 
        'scheduled_date', 'is_overdue', 'image_count'
    ]
    list_filter = ['status', 'scheduled_date', 'created_at', 'issue__org']
    search_fields = ['title', 'description', 'issue__title', 'assigned_to__first_name', 'assigned_to__last_name']
    autocomplete_fields = ['issue', 'created_by', 'assigned_to']
    date_hierarchy = 'scheduled_date'
    ordering = ['-scheduled_date']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'slug')
        }),
        ('Issue & Assignment', {
            'fields': ('issue', 'created_by', 'assigned_to')
        }),
        ('Scheduling', {
            'fields': ('scheduled_date', 'estimated_duration')
        }),
        ('Status Tracking', {
            'fields': ('status', 'started_at', 'completed_at')
        }),
        ('Visit Details', {
            'fields': ('findings', 'actions_taken', 'recommendations'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'started_at', 'completed_at']
    inlines = [SiteVisitImageInline]
    
    def image_count(self, obj):
        return obj.images.count()
    image_count.short_description = 'Images'
    
    def is_overdue(self, obj):
        return obj.is_overdue
    is_overdue.boolean = True
    is_overdue.short_description = 'Overdue'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('issue', 'created_by', 'assigned_to').prefetch_related('images')
    
    actions = ['mark_in_progress', 'mark_completed', 'cancel_visits']
    
    def mark_in_progress(self, request, queryset):
        count = 0
        for visit in queryset:
            if visit.status == 'scheduled':
                visit.mark_in_progress()
                count += 1
        self.message_user(request, f'{count} site visits marked as in progress.')
    mark_in_progress.short_description = 'Mark selected visits as in progress'
    
    def mark_completed(self, request, queryset):
        count = 0
        for visit in queryset:
            if visit.status in ['scheduled', 'in_progress']:
                visit.mark_completed()
                count += 1
        self.message_user(request, f'{count} site visits marked as completed.')
    mark_completed.short_description = 'Mark selected visits as completed'
    
    def cancel_visits(self, request, queryset):
        count = 0
        for visit in queryset:
            if visit.status in ['scheduled', 'in_progress']:
                visit.cancel()
                count += 1
        self.message_user(request, f'{count} site visits cancelled.')
    cancel_visits.short_description = 'Cancel selected visits'


@admin.register(SiteVisitImage)
class SiteVisitImageAdmin(admin.ModelAdmin):
    list_display = ['site_visit_title', 'caption', 'image_preview', 'uploaded_at', 'site_visit_link']
    list_filter = ['uploaded_at', 'site_visit__status']
    search_fields = ['site_visit__title', 'caption']
    autocomplete_fields = ['site_visit']
    date_hierarchy = 'uploaded_at'
    ordering = ['-uploaded_at']
    
    def site_visit_title(self, obj):
        return obj.site_visit.title
    site_visit_title.short_description = 'Site Visit'
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="80" height="80" style="object-fit: cover;" />', obj.image.url)
        return 'No image'
    image_preview.short_description = 'Preview'
    
    def site_visit_link(self, obj):
        url = reverse('admin:issue_management_sitevisit_change', args=[obj.site_visit.pk])
        return format_html('<a href="{}">View Site Visit</a>', url)
    site_visit_link.short_description = 'Site Visit Link'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('site_visit', 'site_visit__issue')


class IssueReviewCommentImageInline(admin.TabularInline):
    model = IssueReviewCommentImage
    extra = 1
    fields = ['image', 'image_preview', 'uploaded_at']
    readonly_fields = ['image_preview', 'uploaded_at']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="100" style="object-fit: cover;" />', obj.image.url)
        return 'No image'
    image_preview.short_description = 'Preview'


@admin.register(IssueReviewComment)
class IssueReviewCommentAdmin(admin.ModelAdmin):
    list_display = ['issue_title', 'user', 'comment_preview', 'created_at', 'image_count', 'issue_link']
    list_filter = ['created_at', 'issue__status', 'issue__org', 'issue__space']
    search_fields = ['comment', 'issue__title', 'user__first_name', 'user__last_name', 'user__email']
    autocomplete_fields = ['issue', 'user']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('issue', 'user', 'comment', 'slug')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [IssueReviewCommentImageInline]
    
    def issue_title(self, obj):
        return obj.issue.title
    issue_title.short_description = 'Issue'
    
    def comment_preview(self, obj):
        return obj.comment[:100] + '...' if len(obj.comment) > 100 else obj.comment
    comment_preview.short_description = 'Comment Preview'
    
    def image_count(self, obj):
        return obj.images.count()
    image_count.short_description = 'Images'
    
    def issue_link(self, obj):
        url = reverse('admin:issue_management_issue_change', args=[obj.issue.pk])
        return format_html('<a href="{}">View Issue</a>', url)
    issue_link.short_description = 'Issue Link'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('issue', 'issue__org', 'issue__space', 'user').prefetch_related('images')


@admin.register(IssueReviewCommentImage)
class IssueReviewCommentImageAdmin(admin.ModelAdmin):
    list_display = ['review_comment_issue', 'image_preview', 'uploaded_at', 'review_comment_link']
    list_filter = ['uploaded_at', 'review_comment__issue__org']
    search_fields = ['review_comment__issue__title', 'review_comment__comment']
    autocomplete_fields = ['review_comment']
    date_hierarchy = 'uploaded_at'
    ordering = ['-uploaded_at']
    
    def review_comment_issue(self, obj):
        return obj.review_comment.issue.title
    review_comment_issue.short_description = 'Issue'
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="80" height="80" style="object-fit: cover;" />', obj.image.url)
        return 'No image'
    image_preview.short_description = 'Preview'
    
    def review_comment_link(self, obj):
        url = reverse('admin:issue_management_issuereviewcomment_change', args=[obj.review_comment.pk])
        return format_html('<a href="{}">View Review Comment</a>', url)
    review_comment_link.short_description = 'Review Comment Link'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('review_comment', 'review_comment__issue', 'review_comment__user')
