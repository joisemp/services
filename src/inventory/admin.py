from django.contrib import admin

from inventory.models import InventorySettings, ProductDeletionRequest


@admin.register(ProductDeletionRequest)
class ProductDeletionRequestAdmin(admin.ModelAdmin):
	list_display = ('product_name', 'product_code', 'status', 'org', 'warehouse', 'requested_by', 'requested_at', 'reviewed_by')
	list_filter = ('status', 'org', 'warehouse', 'requested_at')
	search_fields = ('product_name', 'product_code', 'requested_by__email', 'requested_by__phone_number')
	readonly_fields = ('slug', 'requested_at', 'reviewed_at')


@admin.register(InventorySettings)
class InventorySettingsAdmin(admin.ModelAdmin):
	list_display = ('org', 'created_at', 'updated_at')
	readonly_fields = ('created_at', 'updated_at')