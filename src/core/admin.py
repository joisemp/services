from django.contrib import admin
from .models import Organization, Space


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'address_line_one', 'address_line_two']
    list_filter = ['name']
    search_fields = ['name', 'description', 'address_line_one', 'address_line_two']
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'slug')
        }),
        ('Address Information', {
            'fields': ('address_line_one', 'address_line_two'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('spaces')


@admin.register(Space)
class SpaceAdmin(admin.ModelAdmin):
    list_display = ['name', 'org', 'slug', 'description_preview']
    list_filter = ['org', 'name']
    search_fields = ['name', 'description', 'org__name']
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ['org']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'slug')
        }),
        ('Organization', {
            'fields': ('org',)
        }),
    )
    
    def description_preview(self, obj):
        if obj.description:
            return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
        return 'No description'
    description_preview.short_description = 'Description Preview'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('org').prefetch_related('issues')
