from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from config.utils import generate_unique_slug


class Vehicle(models.Model):
	STATUS_ACTIVE = 'active'
	STATUS_IN_MAINTENANCE = 'maintenance'
	STATUS_OUT_OF_SERVICE = 'out_of_service'

	STATUS_CHOICES = [
		(STATUS_ACTIVE, 'Active'),
		(STATUS_IN_MAINTENANCE, 'In Maintenance'),
		(STATUS_OUT_OF_SERVICE, 'Out of Service'),
	]

	TYPE_CAR = 'car'
	TYPE_VAN = 'van'
	TYPE_BUS = 'bus'
	TYPE_TRUCK = 'truck'
	TYPE_MOTORCYCLE = 'motorcycle'
	TYPE_OTHER = 'other'

	VEHICLE_TYPE_CHOICES = [
		(TYPE_CAR, 'Car'),
		(TYPE_VAN, 'Van'),
		(TYPE_BUS, 'Bus'),
		(TYPE_TRUCK, 'Truck'),
		(TYPE_MOTORCYCLE, 'Motorcycle'),
		(TYPE_OTHER, 'Other'),
	]

	org = models.ForeignKey('core.Organization', on_delete=models.CASCADE, related_name='vehicles')
	registration_number = models.CharField(max_length=32, unique=True)
	vehicle_type = models.CharField(max_length=24, choices=VEHICLE_TYPE_CHOICES)
	manufacturer = models.CharField(max_length=80)
	model = models.CharField(max_length=80)
	year = models.PositiveIntegerField(null=True, blank=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
	notes = models.TextField(blank=True)
	slug = models.SlugField(unique=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['registration_number']
		verbose_name = 'Vehicle'
		verbose_name_plural = 'Vehicles'

	def save(self, *args, **kwargs):
		self.registration_number = self.registration_number.strip().upper()
		self.manufacturer = self.manufacturer.strip()
		self.model = self.model.strip()

		if not self.slug:
			base_slug = slugify(self.registration_number)
			self.slug = generate_unique_slug(self, base_slug)

		super().save(*args, **kwargs)

	def __str__(self):
		return f'{self.registration_number} - {self.manufacturer} {self.model}'

	def get_absolute_url(self):
		return reverse('fleet_management:central_admin:vehicle_detail', kwargs={'slug': self.slug})


class VehicleActivity(models.Model):
	ACTION_CREATED = 'created'
	ACTION_UPDATED = 'updated'
	ACTION_STATUS_CHANGED = 'status_changed'
	ACTION_DELETED = 'deleted'
	ACTION_DETAILS_EDITED = 'details_edited'

	ACTION_CHOICES = [
		(ACTION_CREATED, 'Created'),
		(ACTION_UPDATED, 'Updated'),
		(ACTION_STATUS_CHANGED, 'Status Changed'),
		(ACTION_DELETED, 'Deleted'),
		(ACTION_DETAILS_EDITED, 'Details Edited'),
	]

	vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='activities', null=True, blank=True)
	org = models.ForeignKey('core.Organization', on_delete=models.CASCADE, related_name='vehicle_activities')
	action = models.CharField(max_length=20, choices=ACTION_CHOICES)
	user = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True)
	timestamp = models.DateTimeField(auto_now_add=True)
	field_name = models.CharField(max_length=100, blank=True, null=True)
	old_value = models.TextField(blank=True, null=True)
	new_value = models.TextField(blank=True, null=True)
	details = models.TextField(blank=True, null=True)
	vehicle_slug = models.SlugField(blank=True, null=True, help_text="Slug of deleted vehicle for reference")

	class Meta:
		ordering = ['-timestamp']
		verbose_name = 'Vehicle Activity'
		verbose_name_plural = 'Vehicle Activities'
		indexes = [
			models.Index(fields=['org', '-timestamp']),
			models.Index(fields=['vehicle', '-timestamp']),
		]

	def __str__(self):
		return f"{self.get_action_display()} - {self.vehicle or self.vehicle_slug} by {self.user or 'System'}"

