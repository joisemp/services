from django.contrib import admin

from fleet_management.models import Vehicle, Workshop


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
	list_display = ['registration_number', 'vehicle_type', 'status', 'org', 'created_at']
	list_filter = ['vehicle_type', 'status', 'org', 'created_at']
	search_fields = ['registration_number', 'manufacturer', 'model']
	readonly_fields = ['slug', 'created_at', 'updated_at']


@admin.register(Workshop)
class WorkshopAdmin(admin.ModelAdmin):
	list_display = ['name', 'org', 'created_at']
	list_filter = ['org', 'created_at']
	search_fields = ['name']
	filter_horizontal = ['incharges']
	readonly_fields = ['slug', 'created_at', 'updated_at']
