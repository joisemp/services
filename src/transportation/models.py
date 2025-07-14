from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from django.core.validators import RegexValidator
from django.urls import reverse
from config.utils import generate_unique_slug
from core.models import Organisation


class VehicleType(models.Model):
    """Model to define different types of vehicles"""
    TYPE_CHOICES = [
        ('car', 'Car'),
        ('truck', 'Truck'),
        ('motorcycle', 'Motorcycle'),
        ('bus', 'Bus'),
        ('van', 'Van'),
        ('suv', 'SUV'),
        ('bicycle', 'Bicycle'),
        ('scooter', 'Scooter'),
        ('trailer', 'Trailer'),
        ('other', 'Other'),
    ]
    
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='vehicle_types')
    name = models.CharField(max_length=50, choices=TYPE_CHOICES)
    description = models.TextField(blank=True, null=True)
    slug = models.SlugField(unique=True, db_index=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.organisation.code}-{self.get_name_display()}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['organisation', 'name']
        unique_together = ['organisation', 'name']
        verbose_name = 'Vehicle Type'
        verbose_name_plural = 'Vehicle Types'
    
    def __str__(self):
        return f"{self.organisation.name} - {self.get_name_display()}"


class VehicleMake(models.Model):
    """Model to store vehicle manufacturers/makes"""
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='vehicle_makes')
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=100, blank=True, null=True)
    founded_year = models.IntegerField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    slug = models.SlugField(unique=True, db_index=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.organisation.code}-{self.name}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['organisation', 'name']
        unique_together = ['organisation', 'name']
        verbose_name = 'Vehicle Make'
        verbose_name_plural = 'Vehicle Makes'
    
    def __str__(self):
        return f"{self.organisation.name} - {self.name}"


class VehicleModel(models.Model):
    """Model to store specific vehicle models"""
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='vehicle_models')
    make = models.ForeignKey(VehicleMake, on_delete=models.CASCADE, related_name='models')
    name = models.CharField(max_length=100)
    vehicle_type = models.ForeignKey(VehicleType, on_delete=models.CASCADE, related_name='models')
    year_introduced = models.IntegerField(blank=True, null=True)
    year_discontinued = models.IntegerField(blank=True, null=True)
    engine_types = models.CharField(max_length=200, blank=True, null=True, help_text="e.g., Gasoline, Diesel, Electric, Hybrid")
    slug = models.SlugField(unique=True, db_index=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.organisation.code}-{self.make.name}-{self.name}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['organisation', 'make__name', 'name']
        unique_together = ['organisation', 'make', 'name']
        verbose_name = 'Vehicle Model'
        verbose_name_plural = 'Vehicle Models'
    
    def __str__(self):
        return f"{self.make.name} {self.name}"


class Vehicle(models.Model):
    """Main model for individual vehicles"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('maintenance', 'Under Maintenance'),
        ('retired', 'Retired'),
        ('sold', 'Sold'),
        ('damaged', 'Damaged'),
        ('stolen', 'Stolen'),
    ]
    
    FUEL_CHOICES = [
        ('gasoline', 'Gasoline'),
        ('diesel', 'Diesel'),
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid'),
        ('cng', 'Compressed Natural Gas'),
        ('lpg', 'Liquefied Petroleum Gas'),
        ('hydrogen', 'Hydrogen'),
        ('other', 'Other'),
    ]
    
    TRANSMISSION_CHOICES = [
        ('manual', 'Manual'),
        ('automatic', 'Automatic'),
        ('cvt', 'CVT'),
        ('semi_automatic', 'Semi-Automatic'),
    ]
    
    # Basic Information
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='vehicles')
    vehicle_model = models.ForeignKey(VehicleModel, on_delete=models.CASCADE, related_name='vehicles')
    license_plate = models.CharField(
        max_length=20,
        validators=[RegexValidator(
            regex=r'^[A-Z0-9\-\s]+$',
            message='License plate can only contain letters, numbers, hyphens, and spaces'
        )]
    )
    vin = models.CharField(
        max_length=17, 
        unique=True, 
        verbose_name='VIN (Vehicle Identification Number)',
        validators=[RegexValidator(
            regex=r'^[A-HJ-NPR-Z0-9]{17}$',
            message='VIN must be exactly 17 characters and cannot contain I, O, or Q'
        )]
    )
    year = models.IntegerField()
    color = models.CharField(max_length=50)
    
    # Technical Specifications
    engine_capacity = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True, help_text="Engine capacity in liters")
    fuel_type = models.CharField(max_length=20, choices=FUEL_CHOICES)
    transmission = models.CharField(max_length=20, choices=TRANSMISSION_CHOICES)
    mileage = models.IntegerField(default=0, help_text="Current mileage/odometer reading")
    
    # Ownership and Management
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vehicles', blank=True, null=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='assigned_vehicles', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Purchase Information
    purchase_date = models.DateField(blank=True, null=True)
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    current_value = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    
    # Insurance and Registration
    insurance_company = models.CharField(max_length=100, blank=True, null=True)
    insurance_policy_number = models.CharField(max_length=50, blank=True, null=True)
    insurance_expiry = models.DateField(blank=True, null=True)
    registration_expiry = models.DateField(blank=True, null=True)
    
    # Maintenance
    last_service_date = models.DateField(blank=True, null=True)
    next_service_due = models.DateField(blank=True, null=True)
    service_interval_km = models.IntegerField(blank=True, null=True, help_text="Service interval in kilometers")
    
    # Additional Information
    notes = models.TextField(blank=True, null=True)
    is_company_vehicle = models.BooleanField(default=True)
    slug = models.SlugField(unique=True, db_index=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.organisation.code}-{self.vehicle_model.make.name}-{self.vehicle_model.name}-{self.license_plate}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['organisation', '-created_at']
        unique_together = ['organisation', 'license_plate']
        verbose_name = 'Vehicle'
        verbose_name_plural = 'Vehicles'
    
    def __str__(self):
        return f"{self.vehicle_model} - {self.license_plate}"
    
    def get_absolute_url(self):
        return reverse('transportation:vehicle_detail', kwargs={'slug': self.slug})
    
    @property
    def full_name(self):
        return f"{self.year} {self.vehicle_model} ({self.license_plate})"
    
    @property
    def is_insurance_expired(self):
        if self.insurance_expiry:
            return self.insurance_expiry < timezone.now().date()
        return None
    
    @property
    def is_registration_expired(self):
        if self.registration_expiry:
            return self.registration_expiry < timezone.now().date()
        return None
    
    @property
    def is_service_due(self):
        if self.next_service_due:
            return self.next_service_due <= timezone.now().date()
        return None


class VehicleDocument(models.Model):
    """Model to store vehicle-related documents"""
    
    DOCUMENT_TYPES = [
        ('registration', 'Registration Certificate'),
        ('insurance', 'Insurance Policy'),
        ('permit', 'Permit'),
        ('license', 'Driver License'),
        ('inspection', 'Inspection Certificate'),
        ('warranty', 'Warranty Document'),
        ('manual', 'User Manual'),
        ('receipt', 'Purchase Receipt'),
        ('other', 'Other'),
    ]
    
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='vehicle_documents')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=200)
    document_file = models.FileField(upload_to='vehicle_documents/%Y/%m/')
    expiry_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    slug = models.SlugField(unique=True, db_index=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.organisation.code}-{self.vehicle.license_plate}-{self.title}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['organisation', '-created_at']
        verbose_name = 'Vehicle Document'
        verbose_name_plural = 'Vehicle Documents'
    
    def __str__(self):
        return f"{self.vehicle.license_plate} - {self.title}"
    
    @property
    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return None


class MaintenanceRecord(models.Model):
    """Model to track vehicle maintenance history"""
    
    MAINTENANCE_TYPES = [
        ('routine', 'Routine Service'),
        ('repair', 'Repair'),
        ('inspection', 'Inspection'),
        ('oil_change', 'Oil Change'),
        ('tire_change', 'Tire Change/Rotation'),
        ('brake_service', 'Brake Service'),
        ('battery', 'Battery Service'),
        ('transmission', 'Transmission Service'),
        ('other', 'Other'),
    ]
    
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='maintenance_records')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='maintenance_records')
    maintenance_type = models.CharField(max_length=20, choices=MAINTENANCE_TYPES)
    date = models.DateField()
    mileage_at_service = models.IntegerField()
    description = models.TextField()
    cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    service_provider = models.CharField(max_length=200, blank=True, null=True)
    next_service_due_date = models.DateField(blank=True, null=True)
    next_service_due_mileage = models.IntegerField(blank=True, null=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    slug = models.SlugField(unique=True, db_index=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.organisation.code}-{self.vehicle.license_plate}-{self.get_maintenance_type_display()}-{self.date}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['organisation', '-date']
        verbose_name = 'Maintenance Record'
        verbose_name_plural = 'Maintenance Records'
    
    def __str__(self):
        return f"{self.vehicle.license_plate} - {self.get_maintenance_type_display()} ({self.date})"
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('transportation:maintenance_detail', kwargs={'pk': self.pk})


class VehicleComponent(models.Model):
    """Model to define different vehicle components that can be tracked"""
    COMPONENT_CATEGORIES = [
        ('engine', 'Engine'),
        ('transmission', 'Transmission'),
        ('brakes', 'Brakes'),
        ('suspension', 'Suspension'),
        ('electrical', 'Electrical'),
        ('body', 'Body'),
        ('interior', 'Interior'),
        ('tires', 'Tires'),
        ('exhaust', 'Exhaust'),
        ('fuel_system', 'Fuel System'),
        ('cooling', 'Cooling System'),
        ('steering', 'Steering'),
        ('lighting', 'Lighting'),
        ('safety', 'Safety Equipment'),
        ('other', 'Other'),
    ]
    
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='vehicle_components')
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=COMPONENT_CATEGORIES)
    description = models.TextField(blank=True, null=True)
    is_critical = models.BooleanField(default=False, help_text="Critical components require immediate attention when issues arise")
    slug = models.SlugField(unique=True, db_index=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.organisation.code}-{self.name}-{self.get_category_display()}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['organisation', 'category', 'name']
        unique_together = ['organisation', 'name', 'category']
        verbose_name = 'Vehicle Component'
        verbose_name_plural = 'Vehicle Components'
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class VehicleComponentInstance(models.Model):
    """Model to track specific component instances in vehicles"""
    STATUS_CHOICES = [
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('critical', 'Critical'),
        ('replaced', 'Replaced'),
        ('removed', 'Removed'),
    ]
    
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='vehicle_component_instances')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='component_instances')
    component = models.ForeignKey(VehicleComponent, on_delete=models.CASCADE, related_name='instances')
    serial_number = models.CharField(max_length=100, blank=True, null=True)
    part_number = models.CharField(max_length=100, blank=True, null=True)
    manufacturer = models.CharField(max_length=100, blank=True, null=True)
    model_number = models.CharField(max_length=100, blank=True, null=True)
    installation_date = models.DateField(blank=True, null=True)
    installation_mileage = models.IntegerField(blank=True, null=True)
    warranty_expiry = models.DateField(blank=True, null=True)
    expected_lifespan_km = models.IntegerField(blank=True, null=True, help_text="Expected lifespan in kilometers")
    expected_lifespan_months = models.IntegerField(blank=True, null=True, help_text="Expected lifespan in months")
    current_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='good')
    last_inspection_date = models.DateField(blank=True, null=True)
    next_inspection_due = models.DateField(blank=True, null=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    slug = models.SlugField(unique=True, db_index=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.organisation.code}-{self.vehicle.license_plate}-{self.component.name}-{self.pk or 'new'}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    @property
    def is_warranty_expired(self):
        if self.warranty_expiry:
            return self.warranty_expiry < timezone.now().date()
        return None
    
    @property
    def is_inspection_due(self):
        if self.next_inspection_due:
            return self.next_inspection_due <= timezone.now().date()
        return None
    
    @property
    def estimated_replacement_date(self):
        if self.installation_date and self.expected_lifespan_months:
            from datetime import timedelta
            return self.installation_date + timedelta(days=self.expected_lifespan_months * 30)
        return None
    
    class Meta:
        ordering = ['organisation', '-created_at']
        verbose_name = 'Vehicle Component Instance'
        verbose_name_plural = 'Vehicle Component Instances'
    
    def __str__(self):
        return f"{self.vehicle.license_plate} - {self.component.name}"


class VehicleChangeLog(models.Model):
    """Model to track all changes made to vehicles and their components"""
    CHANGE_TYPES = [
        ('vehicle_update', 'Vehicle Information Updated'),
        ('component_added', 'Component Added'),
        ('component_updated', 'Component Updated'),
        ('component_replaced', 'Component Replaced'),
        ('component_removed', 'Component Removed'),
        ('maintenance_performed', 'Maintenance Performed'),
        ('inspection_completed', 'Inspection Completed'),
        ('status_changed', 'Status Changed'),
        ('ownership_transferred', 'Ownership Transferred'),
        ('other', 'Other'),
    ]
    
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='vehicle_change_logs')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='change_logs')
    component_instance = models.ForeignKey(VehicleComponentInstance, on_delete=models.CASCADE, related_name='change_logs', blank=True, null=True)
    change_type = models.CharField(max_length=30, choices=CHANGE_TYPES)
    field_changed = models.CharField(max_length=100, blank=True, null=True, help_text="Name of the field that was changed")
    old_value = models.TextField(blank=True, null=True, help_text="Previous value before change")
    new_value = models.TextField(blank=True, null=True, help_text="New value after change")
    description = models.TextField(help_text="Description of what was changed")
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    change_reason = models.TextField(blank=True, null=True, help_text="Reason for the change")
    mileage_at_change = models.IntegerField(blank=True, null=True)
    cost_impact = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Cost associated with this change")
    reference_document = models.ForeignKey(VehicleDocument, on_delete=models.SET_NULL, blank=True, null=True, help_text="Related document for this change")
    maintenance_record = models.ForeignKey(MaintenanceRecord, on_delete=models.SET_NULL, blank=True, null=True, help_text="Related maintenance record")
    slug = models.SlugField(unique=True, db_index=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.organisation.code}-{self.vehicle.license_plate}-{self.get_change_type_display()}-{self.created_at or timezone.now()}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['organisation', '-created_at']
        verbose_name = 'Vehicle Change Log'
        verbose_name_plural = 'Vehicle Change Logs'
    
    def __str__(self):
        return f"{self.vehicle.license_plate} - {self.get_change_type_display()} ({self.created_at.strftime('%Y-%m-%d')})"


class ComponentInspection(models.Model):
    """Model to track detailed inspections of vehicle components"""
    INSPECTION_RESULTS = [
        ('passed', 'Passed'),
        ('warning', 'Warning - Monitor Closely'),
        ('failed', 'Failed - Requires Action'),
        ('critical', 'Critical - Immediate Action Required'),
    ]
    
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='component_inspections')
    component_instance = models.ForeignKey(VehicleComponentInstance, on_delete=models.CASCADE, related_name='inspections')
    inspection_date = models.DateField()
    inspector = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    inspection_type = models.CharField(max_length=100, help_text="Type of inspection (routine, pre-trip, annual, etc.)")
    result = models.CharField(max_length=20, choices=INSPECTION_RESULTS)
    condition_rating = models.IntegerField(choices=[(i, i) for i in range(1, 11)], help_text="Condition rating from 1 (poor) to 10 (excellent)")
    findings = models.TextField(help_text="Detailed findings from the inspection")
    recommendations = models.TextField(blank=True, null=True, help_text="Recommended actions")
    next_inspection_due = models.DateField(blank=True, null=True)
    photos = models.FileField(upload_to='component_inspections/%Y/%m/', blank=True, null=True, help_text="Photos from inspection")
    mileage_at_inspection = models.IntegerField(blank=True, null=True)
    estimated_remaining_life = models.IntegerField(blank=True, null=True, help_text="Estimated remaining life in kilometers")
    replacement_urgency = models.CharField(
        max_length=20, 
        choices=[
            ('immediate', 'Immediate'),
            ('within_week', 'Within 1 Week'),
            ('within_month', 'Within 1 Month'),
            ('within_quarter', 'Within 3 Months'),
            ('within_year', 'Within 1 Year'),
            ('routine', 'At Next Routine Maintenance'),
        ],
        blank=True, null=True
    )
    slug = models.SlugField(unique=True, db_index=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.organisation.code}-{self.component_instance.vehicle.license_plate}-{self.component_instance.component.name}-inspection-{self.inspection_date}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['organisation', '-inspection_date']
        verbose_name = 'Component Inspection'
        verbose_name_plural = 'Component Inspections'
    
    def __str__(self):
        return f"{self.component_instance} - {self.get_result_display()} ({self.inspection_date})"
