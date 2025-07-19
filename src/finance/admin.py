from django.contrib import admin
from django.utils.html import format_html
from .models import (
    TransactionCategory,
    FinancialTransaction,
    RecurringTransaction,
    Budget,
    TransactionAttachment,
    FinancialReport
)

# Register your models here.

@admin.register(TransactionCategory)
class TransactionCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'org', 'is_active', 'created_at']
    list_filter = ['is_active', 'org', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['slug', 'created_at', 'updated_at']
    prepopulated_fields = {'slug': ('name',)}

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(org=request.user.profile.org)


class TransactionAttachmentInline(admin.TabularInline):
    model = TransactionAttachment
    extra = 0
    readonly_fields = ['uploaded_at', 'uploaded_by']

    def save_model(self, request, obj, form, change):
        if not change:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(FinancialTransaction)
class FinancialTransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'title', 'amount', 'transaction_type', 'status', 'transaction_date', 'org']
    list_filter = ['transaction_type', 'status', 'payment_method', 'category', 'org', 'transaction_date', 'is_recurring']
    search_fields = ['title', 'description', 'transaction_id', 'reference_number']
    readonly_fields = ['transaction_id', 'slug', 'created_at', 'updated_at']
    date_hierarchy = 'transaction_date'
    inlines = [TransactionAttachmentInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'amount', 'transaction_type', 'payment_method', 'status')
        }),
        ('Categorization', {
            'fields': ('category', 'org')
        }),
        ('Users', {
            'fields': ('created_by', 'approved_by')
        }),
        ('Related Object', {
            'fields': ('content_type', 'object_id'),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('transaction_date',)
        }),
        ('Additional Info', {
            'fields': ('reference_number', 'receipt_image', 'notes', 'is_recurring'),
            'classes': ('collapse',)
        }),
        ('System Fields', {
            'fields': ('transaction_id', 'slug', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(org=request.user.profile.org)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
            if not obj.org:
                obj.org = request.user.profile.org
        super().save_model(request, obj, form, change)


@admin.register(RecurringTransaction)
class RecurringTransactionAdmin(admin.ModelAdmin):
    list_display = ['title', 'amount', 'frequency', 'next_due_date', 'is_active', 'auto_create', 'org']
    list_filter = ['frequency', 'transaction_type', 'is_active', 'auto_create', 'org']
    search_fields = ['title', 'description']
    readonly_fields = ['slug', 'created_at', 'updated_at']
    date_hierarchy = 'next_due_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'amount')
        }),
        ('Recurrence Settings', {
            'fields': ('frequency', 'start_date', 'end_date', 'next_due_date')
        }),
        ('Transaction Template', {
            'fields': ('transaction_type', 'payment_method', 'category')
        }),
        ('Organization & User', {
            'fields': ('org', 'created_by')
        }),
        ('Status', {
            'fields': ('is_active', 'auto_create')
        }),
        ('System Fields', {
            'fields': ('slug', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(org=request.user.profile.org)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
            if not obj.org:
                obj.org = request.user.profile.org
        super().save_model(request, obj, form, change)


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['name', 'budgeted_amount', 'period', 'get_spent_display', 'get_remaining_display', 'is_active', 'org']
    list_filter = ['period', 'is_active', 'org', 'category']
    search_fields = ['name', 'description']
    readonly_fields = ['slug', 'created_at', 'updated_at', 'get_spent_display', 'get_remaining_display', 'get_percentage_used_display']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description')
        }),
        ('Budget Settings', {
            'fields': ('category', 'budgeted_amount', 'period')
        }),
        ('Time Period', {
            'fields': ('start_date', 'end_date')
        }),
        ('Organization', {
            'fields': ('org', 'created_by')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Budget Analysis', {
            'fields': ('get_spent_display', 'get_remaining_display', 'get_percentage_used_display'),
            'classes': ('collapse',)
        }),
        ('System Fields', {
            'fields': ('slug', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_spent_display(self, obj):
        spent = obj.get_spent_amount()
        color = 'red' if obj.is_over_budget() else 'green'
        return format_html('<span style="color: {};">${}</span>', color, spent)
    get_spent_display.short_description = 'Spent Amount'

    def get_remaining_display(self, obj):
        remaining = obj.get_remaining_amount()
        color = 'red' if remaining < 0 else 'green'
        return format_html('<span style="color: {};">${}</span>', color, remaining)
    get_remaining_display.short_description = 'Remaining Amount'

    def get_percentage_used_display(self, obj):
        percentage = obj.get_percentage_used()
        color = 'red' if percentage > 100 else 'orange' if percentage > 80 else 'green'
        return format_html('<span style="color: {};">{:.1f}%</span>', color, percentage)
    get_percentage_used_display.short_description = 'Percentage Used'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(org=request.user.profile.org)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
            if not obj.org:
                obj.org = request.user.profile.org
        super().save_model(request, obj, form, change)


@admin.register(TransactionAttachment)
class TransactionAttachmentAdmin(admin.ModelAdmin):
    list_display = ['filename', 'transaction', 'uploaded_at', 'uploaded_by']
    list_filter = ['uploaded_at', 'uploaded_by']
    search_fields = ['filename', 'description', 'transaction__title']
    readonly_fields = ['uploaded_at', 'uploaded_by']

    def save_model(self, request, obj, form, change):
        if not change:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(FinancialReport)
class FinancialReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'report_type', 'start_date', 'end_date', 'org', 'generated_at']
    list_filter = ['report_type', 'org', 'generated_at']
    search_fields = ['name']
    readonly_fields = ['slug', 'generated_at', 'generated_by']
    date_hierarchy = 'generated_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'report_type')
        }),
        ('Report Parameters', {
            'fields': ('start_date', 'end_date', 'category')
        }),
        ('Organization', {
            'fields': ('org', 'generated_by')
        }),
        ('Report Data', {
            'fields': ('report_data',),
            'classes': ('collapse',)
        }),
        ('Export', {
            'fields': ('pdf_file',),
            'classes': ('collapse',)
        }),
        ('System Fields', {
            'fields': ('slug', 'generated_at'),
            'classes': ('collapse',)
        })
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(org=request.user.profile.org)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.generated_by = request.user
            if not obj.org:
                obj.org = request.user.profile.org
        super().save_model(request, obj, form, change)
