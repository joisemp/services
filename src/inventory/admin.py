from django.contrib import admin

from inventory.models import ProductDeletionRequest


@admin.register(ProductDeletionRequest)
class ProductDeletionRequestAdmin(admin.ModelAdmin):
	list_display = ('product_name', 'product_code', 'status', 'org', 'warehouse', 'requested_by', 'requested_at', 'reviewed_by')
	list_filter = ('status', 'org', 'warehouse', 'requested_at')
	search_fields = ('product_name', 'product_code', 'requested_by__email', 'requested_by__phone_number')
	readonly_fields = ('slug', 'requested_at', 'reviewed_at')