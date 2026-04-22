from django.db import models
from django.core.exceptions import ValidationError
from datetime import timedelta
from django.utils import timezone
from config.utils import generate_unique_slug, generate_unique_code, compress_image
from django.utils.text import slugify


UNIT_CHOICES = [
    ('CARTONS', 'CARTONS ( Ctn )'),
    ('KILOGRAMS', 'KILOGRAMS ( Kg )'),
    ('QUINTAL', 'QUINTAL ( Qtl )'),
    ('BOTTLES', 'BOTTLES ( Btl )'),
    ('PIECES', 'PIECES ( Pcs )'),
    ('ROLLS', 'ROLLS ( Rol )'),
    ('NUMBERS', 'NUMBERS ( Nos )'),
    ('PAIRS', 'PAIRS ( Prs )'),
    ('TABLETS', 'TABLETS ( Tbs )'),
    ('MILILITRE', 'MILILITRE ( Ml )'),
    ('BUNDLES', 'BUNDLES ( Bdl )'),
    ('BOX', 'BOX ( Box )'),
    ('SQUARE_METERS', 'SQUARE METERS ( Sqm )'),
    ('BAGS', 'BAGS ( Bag )'),
    ('CANS', 'CANS ( Can )'),
    ('SQUARE_FEET', 'SQUARE FEET ( Sqf )'),
    ('LITRE', 'LITRE ( Ltr )'),
    ('DOZENS', 'DOZENS ( Dzn )'),
    ('PACKS', 'PACKS ( Pac )'),
    ('GRAMMES', 'GRAMMES ( Gm )'),
    ('METERS', 'METERS ( Mtr )'),
]


class ActiveProductManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class Category(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    org = models.ForeignKey('core.Organization', on_delete=models.CASCADE, related_name='categories')
    slug = models.SlugField(unique=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
        

class Brand(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    org = models.ForeignKey('core.Organization', on_delete=models.CASCADE, related_name='brands')
    slug = models.SlugField(unique=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Warehouse(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    org = models.ForeignKey('core.Organization', on_delete=models.CASCADE, related_name='warehouses')
    slug = models.SlugField(unique=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class InventorySettings(models.Model):
    org = models.OneToOneField('core.Organization', on_delete=models.CASCADE, related_name='inventory_settings')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Inventory Settings'
        verbose_name_plural = 'Inventory Settings'

    def __str__(self):
        return f'Inventory Settings - {self.org}'
        

class Room(models.Model):
    name = models.CharField(max_length=255)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='rooms')
    slug = models.SlugField(unique=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.warehouse.name} - {self.name}"


class Bucket(models.Model):
    name = models.CharField(max_length=255)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='buckets')
    slug = models.SlugField(unique=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.room.name} - {self.name}"


class Product(models.Model):
    TYPE_CHOICES = [
        ('SINGLE_VARIANT', 'SINGLE VARIANT'),
        ('MULTI_VARIANT', 'MULTI VARIANT'),
    ]
    name = models.CharField(max_length=255)
    description = models.TextField()
    total_incoming_quantity = models.IntegerField(default=0)
    total_used_quantity = models.IntegerField(default=0)
    universal_available_quantity = models.IntegerField(default=0)
    unit = models.CharField(max_length=50, choices=UNIT_CHOICES)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    slug = models.SlugField(unique=True)
    product_code = models.CharField(max_length=20, unique=True, blank=True)
    org = models.ForeignKey('core.Organization', on_delete=models.CASCADE, related_name='products')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='products')
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, related_name='products', null=True, blank=True)
    bucket = models.ForeignKey(Bucket, on_delete=models.SET_NULL, related_name='products', null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, related_name='products', null=True, blank=True)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, related_name='products', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = ActiveProductManager()
    all_objects = models.Manager()
    
    def save(self, *args, **kwargs):
        if not self.product_code:
            # Generate unique product_code using org prefix and unique code
            org_prefix = self.org.name[:3].upper() if self.org else 'INV'
            self.product_code = f"PRD-{org_prefix}-{generate_unique_code(Product, no_of_char=6, unique_field='product_code')}"
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def soft_delete(self):
        if self.is_deleted:
            return

        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])


class ProductDeletionRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        related_name='deletion_requests',
        null=True,
        blank=True,
    )
    product_name = models.CharField(max_length=255)
    product_code = models.CharField(max_length=20, blank=True)
    org = models.ForeignKey('core.Organization', on_delete=models.CASCADE, related_name='product_deletion_requests')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='product_deletion_requests')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='pending')

    requested_by = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='product_deletion_requests_made',
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    request_reason = models.TextField()

    reviewed_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        related_name='product_deletion_requests_reviewed',
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_reason = models.TextField(blank=True)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['org', '-requested_at']),
            models.Index(fields=['status', '-requested_at']),
            models.Index(fields=['warehouse', '-requested_at']),
        ]

    def save(self, *args, **kwargs):
        if self.product:
            self.product_name = self.product.name
            self.product_code = self.product.product_code

        if not self.slug:
            base_slug = slugify(f"{self.product_name}-deletion-request")
            self.slug = generate_unique_slug(self, base_slug)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Deletion Request - {self.product_name} ({self.get_status_display()})"
    
class Variant(models.Model):
    name = models.CharField(max_length=255)
    unit = models.CharField(max_length=50, choices=UNIT_CHOICES)
    total_incoming_quantity = models.IntegerField(default=0)
    total_used_quantity = models.IntegerField(default=0)
    universal_available_quantity = models.IntegerField(default=0)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, related_name='variants', null=True, blank=True)
    size = models.ForeignKey('Size', on_delete=models.SET_NULL, related_name='variants', null=True, blank=True)
    slug = models.SlugField(unique=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} - {self.name}"    


class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='public/product_images/')
    display_order = models.IntegerField(default=0)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'created_at', 'id']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_code(ProductImage, no_of_char=12, unique_field='slug')

        if self.image and (not self.pk or self._state.adding):
            self.image = compress_image(
                self.image,
                max_width=1920,
                max_height=1920,
                quality=85,
                format='WEBP',
                upload_path='public/product_images/',
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Image for Product: {self.product.name}"


class VariantImage(models.Model):
    variant = models.ForeignKey(Variant, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='public/variant_images/')
    display_order = models.IntegerField(default=0)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'created_at', 'id']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_code(VariantImage, no_of_char=12, unique_field='slug')

        if self.image and (not self.pk or self._state.adding):
            self.image = compress_image(
                self.image,
                max_width=1920,
                max_height=1920,
                quality=85,
                format='WEBP',
                upload_path='public/variant_images/',
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Image for Variant: {self.variant.name}"
    

class Size(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    org = models.ForeignKey('core.Organization', on_delete=models.CASCADE, related_name='sizes')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sizes')
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE, related_name='sizes', null=True, blank=True)
    slug = models.SlugField(unique=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)    

    def __str__(self):
        return f"{self.product.name} - {self.name}"


class StockMovementBatch(models.Model):
    reference_code = models.CharField(max_length=32, unique=True, blank=True)
    slug = models.SlugField(unique=True)
    org = models.ForeignKey('core.Organization', on_delete=models.CASCADE, related_name='stock_movement_batches')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stock_movement_batches')
    recorded_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        related_name='stock_movement_batches',
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['org', '-created_at']),
            models.Index(fields=['warehouse', '-created_at']),
        ]

    def save(self, *args, **kwargs):
        if not self.reference_code:
            org_prefix = self.org.name[:3].upper() if self.org else 'INV'
            unique_code = generate_unique_code(
                StockMovementBatch,
                no_of_char=8,
                unique_field='reference_code',
            )
            self.reference_code = f"SMB-{org_prefix}-{unique_code}"
        if not self.slug:
            base_slug = slugify(self.reference_code)
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.reference_code


class StockMovementLine(models.Model):
    TARGET_TYPE_CHOICES = [
        ('PRODUCT', 'Product'),
        ('VARIANT', 'Variant'),
    ]
    MOVEMENT_TYPE_CHOICES = [
        ('INCOMING', 'Incoming'),
        ('OUTGOING', 'Outgoing'),
    ]
    CORRECTION_TYPE_CHOICES = [
        ('ORIGINAL', 'Original'),
        ('CORRECTION', 'Correction'),
    ]

    batch = models.ForeignKey(StockMovementBatch, on_delete=models.CASCADE, related_name='lines')
    org = models.ForeignKey('core.Organization', on_delete=models.CASCADE, related_name='stock_movement_lines')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stock_movement_lines')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_movement_lines')
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE, related_name='stock_movement_lines', null=True, blank=True)
    target_type = models.CharField(max_length=16, choices=TARGET_TYPE_CHOICES)
    movement_type = models.CharField(max_length=16, choices=MOVEMENT_TYPE_CHOICES)
    quantity = models.PositiveIntegerField()
    notes = models.TextField(blank=True)
    correction_type = models.CharField(max_length=16, choices=CORRECTION_TYPE_CHOICES, default='ORIGINAL')
    corrects_movement = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        related_name='corrections',
        null=True,
        blank=True,
    )
    corrected_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        related_name='inventory_corrections_made',
        null=True,
        blank=True,
    )
    correction_reason = models.TextField(blank=True)
    corrected_at = models.DateTimeField(null=True, blank=True)

    old_total_incoming_quantity = models.IntegerField(default=0)
    old_total_used_quantity = models.IntegerField(default=0)
    old_available_quantity = models.IntegerField(default=0)
    new_total_incoming_quantity = models.IntegerField(default=0)
    new_total_used_quantity = models.IntegerField(default=0)
    new_available_quantity = models.IntegerField(default=0)

    recorded_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        related_name='stock_movement_lines',
        null=True,
        blank=True,
    )
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['org', '-created_at']),
            models.Index(fields=['warehouse', '-created_at']),
            models.Index(fields=['product', '-created_at']),
            models.Index(fields=['correction_type', '-created_at']),
            models.Index(fields=['corrects_movement']),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(quantity__gt=0), name='stock_movement_quantity_gt_0'),
            models.CheckConstraint(
                check=(
                    (models.Q(target_type='PRODUCT') & models.Q(variant__isnull=True))
                    | (models.Q(target_type='VARIANT') & models.Q(variant__isnull=False))
                ),
                name='stock_movement_variant_matches_target',
            ),
        ]

    def clean(self):
        if self.product and self.org_id and self.product.org_id != self.org_id:
            raise ValidationError('Product must belong to the same organization as the movement.')

        if self.warehouse and self.product and self.product.warehouse_id != self.warehouse_id:
            raise ValidationError('Product must belong to the selected warehouse.')

        if self.variant:
            if self.variant.product_id != self.product_id:
                raise ValidationError('Variant must belong to the selected product.')
            if self.variant.product.org_id != self.org_id:
                raise ValidationError('Variant must belong to the same organization as the movement.')

        if self.correction_type == 'ORIGINAL' and self.corrects_movement_id:
            raise ValidationError('Original movement cannot reference corrected movement.')

        if self.correction_type == 'CORRECTION' and not self.corrects_movement_id:
            raise ValidationError('Correction movement must reference an original movement.')

        if self.corrects_movement_id and self.corrects_movement_id == self.id:
            raise ValidationError('A movement cannot correct itself.')

        if self.corrects_movement and self.corrects_movement.correction_type != 'ORIGINAL':
            raise ValidationError('Only original movements can be corrected.')

    def has_correction(self):
        return self.corrections.exists()

    def can_supervisor_correct(self, at_time=None):
        if self.correction_type != 'ORIGINAL':
            return False
        if self.has_correction():
            return False

        now = at_time or timezone.now()
        return now <= self.created_at + timedelta(hours=48)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.batch.reference_code}-{self.product.name}-{self.movement_type}")
            self.slug = generate_unique_slug(self, base_slug)
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        target_name = self.variant.name if self.variant else self.product.name
        return f"{self.get_movement_type_display()} {self.quantity} - {target_name}"
        
    