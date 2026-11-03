from django.db import models
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.text import slugify

from config.utils import generate_unique_slug


def get_expense_upload_path(instance, filename):
	"""Generate upload path for expense receipts."""
	vehicle_slug = instance.vehicle.slug if instance.vehicle else 'unknown'
	return f'vehicle/{vehicle_slug}/expenses/{filename}'


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


class Workshop(models.Model):
	org = models.ForeignKey('core.Organization', on_delete=models.CASCADE, related_name='workshops')
	name = models.CharField(max_length=120)
	notes = models.TextField(blank=True)
	slug = models.SlugField(unique=True, blank=True)
	incharges = models.ManyToManyField('core.User', related_name='workshops_incharge', blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['name']
		verbose_name = 'Workshop'
		verbose_name_plural = 'Workshops'

	def clean(self):
		super().clean()
		if not self.org_id:
			return

		# M2M values exist only after initial save, so validate when id is available.
		if not self.pk:
			return

		invalid_incharges = self.incharges.exclude(
			organization=self.org,
			user_type__in=['maintainer', 'supervisor'],
		)
		if invalid_incharges.exists():
			raise ValidationError('Workshop incharges must be maintainers or supervisors in the same organization.')

	def save(self, *args, **kwargs):
		self.name = self.name.strip()

		if not self.slug:
			base_slug = slugify(self.name)
			self.slug = generate_unique_slug(self, base_slug)

		super().save(*args, **kwargs)

	def __str__(self):
		return self.name

	def get_absolute_url(self):
		return reverse('fleet_management:central_admin:workshop_detail', kwargs={'slug': self.slug})


class VehicleActivity(models.Model):
	ACTION_CREATED = 'created'
	ACTION_UPDATED = 'updated'
	ACTION_STATUS_CHANGED = 'status_changed'
	ACTION_DELETED = 'deleted'
	ACTION_DETAILS_EDITED = 'details_edited'
	ACTION_EXPENSE_CREATED = 'expense_created'
	ACTION_EXPENSE_UPDATED = 'expense_updated'
	ACTION_EXPENSE_DELETED = 'expense_deleted'

	ACTION_CHOICES = [
		(ACTION_CREATED, 'Created'),
		(ACTION_UPDATED, 'Updated'),
		(ACTION_STATUS_CHANGED, 'Status Changed'),
		(ACTION_DELETED, 'Deleted'),
		(ACTION_DETAILS_EDITED, 'Details Edited'),
		(ACTION_EXPENSE_CREATED, 'Expense Created'),
		(ACTION_EXPENSE_UPDATED, 'Expense Updated'),
		(ACTION_EXPENSE_DELETED, 'Expense Deleted'),
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


class VehicleExpense(models.Model):
	CATEGORY_FUEL = 'fuel'
	CATEGORY_MAINTENANCE = 'maintenance'
	CATEGORY_REPAIRS = 'repairs'
	CATEGORY_TOLLS = 'tolls'
	CATEGORY_PARKING = 'parking'
	CATEGORY_INSURANCE = 'insurance'
	CATEGORY_OTHER = 'other'

	CATEGORY_CHOICES = [
		(CATEGORY_FUEL, 'Fuel'),
		(CATEGORY_MAINTENANCE, 'Maintenance'),
		(CATEGORY_REPAIRS, 'Repairs'),
		(CATEGORY_TOLLS, 'Tolls'),
		(CATEGORY_PARKING, 'Parking'),
		(CATEGORY_INSURANCE, 'Insurance'),
		(CATEGORY_OTHER, 'Other'),
	]

	vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='expenses')
	amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Expense amount in currency")
	expense_date = models.DateField(help_text="Date when expense occurred")
	category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
	description = models.TextField(blank=True, null=True)
	receipt = models.FileField(upload_to=get_expense_upload_path, blank=True, null=True)
	created_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_expenses')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-expense_date', '-created_at']
		verbose_name = 'Vehicle Expense'
		verbose_name_plural = 'Vehicle Expenses'
		indexes = [
			models.Index(fields=['vehicle', '-expense_date']),
			models.Index(fields=['created_by', '-created_at']),
		]

	def __str__(self):
		return f"{self.get_category_display()} - {self.vehicle} - {self.amount}"

