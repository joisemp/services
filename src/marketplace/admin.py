from django.contrib import admin
from .models import ShoppingList, ShoppingListItem, Purchase, PurchaseItem, ShoppingListStatusHistory

# Register your models here.

@admin.register(ShoppingList)
class ShoppingListAdmin(admin.ModelAdmin):
    list_display = ['name', 'org', 'status', 'priority', 'created_by', 'total_cost', 'created_at']
    list_filter = ['status', 'priority', 'org', 'created_at']
    search_fields = ['name', 'description', 'created_by__profile__first_name', 'created_by__profile__last_name']
    readonly_fields = ['slug', 'total_cost', 'created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'org', 'created_by')
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority', 'approved_by')
        }),
        ('Budget', {
            'fields': ('budget_limit', 'total_cost')
        }),
        ('Metadata', {
            'fields': ('slug', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(ShoppingListItem)
class ShoppingListItemAdmin(admin.ModelAdmin):
    list_display = ['item_name', 'shopping_list', 'quantity', 'estimated_cost', 'supplier', 'category', 'is_purchased']
    list_filter = ['is_purchased', 'category', 'shopping_list__org', 'created_at']
    search_fields = ['item_name', 'description', 'supplier', 'shopping_list__name']
    readonly_fields = ['slug', 'created_at']
    
    fieldsets = (
        (None, {
            'fields': ('shopping_list', 'item_name', 'description', 'category')
        }),
        ('Quantity & Cost', {
            'fields': ('quantity', 'estimated_cost', 'actual_cost')
        }),
        ('Purchase Info', {
            'fields': ('supplier', 'is_purchased', 'purchase_date')
        }),
        ('Additional Info', {
            'fields': ('notes', 'slug', 'created_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ['purchase_id', 'shopping_list', 'supplier_name', 'total_amount', 'status', 'ordered_by', 'created_at']
    list_filter = ['status', 'shopping_list__org', 'created_at']
    search_fields = ['purchase_id', 'supplier_name', 'shopping_list__name', 'ordered_by__profile__first_name']
    readonly_fields = ['purchase_id', 'slug', 'created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('purchase_id', 'shopping_list', 'total_amount', 'status')
        }),
        ('Users', {
            'fields': ('ordered_by', 'approved_by')
        }),
        ('Supplier Info', {
            'fields': ('supplier_name', 'supplier_contact')
        }),
        ('Delivery Info', {
            'fields': ('order_date', 'expected_delivery', 'actual_delivery')
        }),
        ('Additional Info', {
            'fields': ('invoice_number', 'notes', 'slug', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(PurchaseItem)
class PurchaseItemAdmin(admin.ModelAdmin):
    list_display = ['purchase', 'shopping_list_item', 'quantity_ordered', 'unit_cost', 'total_cost', 'is_received']
    list_filter = ['is_received', 'purchase__status', 'purchase__shopping_list__org']
    search_fields = ['purchase__purchase_id', 'shopping_list_item__item_name']
    readonly_fields = ['slug', 'total_cost']
    
    fieldsets = (
        (None, {
            'fields': ('purchase', 'shopping_list_item')
        }),
        ('Order Info', {
            'fields': ('quantity_ordered', 'unit_cost', 'total_cost')
        }),
        ('Received Info', {
            'fields': ('quantity_received', 'is_received', 'received_date')
        }),
        ('Additional Info', {
            'fields': ('notes', 'slug'),
            'classes': ('collapse',)
        })
    )


@admin.register(ShoppingListStatusHistory)
class ShoppingListStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['shopping_list', 'old_status', 'new_status', 'changed_by', 'created_at']
    list_filter = ['old_status', 'new_status', 'shopping_list__org', 'created_at']
    search_fields = ['shopping_list__name', 'comment', 'changed_by__profile__first_name']
    readonly_fields = ['slug', 'created_at']
    
    fieldsets = (
        (None, {
            'fields': ('shopping_list', 'changed_by')
        }),
        ('Status Change', {
            'fields': ('old_status', 'new_status', 'comment')
        }),
        ('Metadata', {
            'fields': ('slug', 'created_at'),
            'classes': ('collapse',)
        })
    )
