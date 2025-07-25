from django.contrib import admin
from .models import WorkCategory, Spaces, SpaceSettings

# Register your models here.

@admin.register(Spaces)
class SpacesAdmin(admin.ModelAdmin):
    list_display = ['name', 'org', 'is_access_enabled', 'get_admin_count', 'created_at']
    list_filter = ['is_access_enabled', 'require_approval', 'org', 'created_at']
    search_fields = ['name', 'description', 'org__name']
    filter_horizontal = ['space_admins']
    readonly_fields = ['slug', 'created_at', 'updated_at']
    
    def get_admin_count(self, obj):
        return obj.get_admin_count()
    get_admin_count.short_description = 'Admin Count'


@admin.register(SpaceSettings)
class SpaceSettingsAdmin(admin.ModelAdmin):
    list_display = ['space', 'enable_issue_management', 'enable_service_management', 'enable_transportation', 'enable_finance', 'enable_marketplace', 'enable_asset_management']
    list_filter = ['enable_issue_management', 'enable_service_management', 'enable_transportation', 'enable_finance', 'enable_marketplace', 'enable_asset_management']
    search_fields = ['space__name', 'space__org__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Space', {
            'fields': ('space',)
        }),
        ('Module Access', {
            'fields': ('enable_issue_management', 'enable_service_management', 'enable_transportation', 'enable_finance', 'enable_marketplace', 'enable_asset_management')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        })
    )


@admin.register(WorkCategory)
class WorkCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'org', 'slug']
    list_filter = ['org']
    search_fields = ['name', 'description', 'org__name']
    readonly_fields = ['slug']
