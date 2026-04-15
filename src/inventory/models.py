from django.db import models
from django.core.exceptions import ValidationError
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

    batch = models.ForeignKey(StockMovementBatch, on_delete=models.CASCADE, related_name='lines')
    org = models.ForeignKey('core.Organization', on_delete=models.CASCADE, related_name='stock_movement_lines')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stock_movement_lines')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_movement_lines')
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE, related_name='stock_movement_lines', null=True, blank=True)
    target_type = models.CharField(max_length=16, choices=TARGET_TYPE_CHOICES)
    movement_type = models.CharField(max_length=16, choices=MOVEMENT_TYPE_CHOICES)
    quantity = models.PositiveIntegerField()
    notes = models.TextField(blank=True)

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

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.batch.reference_code}-{self.product.name}-{self.movement_type}")
            self.slug = generate_unique_slug(self, base_slug)
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        target_name = self.variant.name if self.variant else self.product.name
        return f"{self.get_movement_type_display()} {self.quantity} - {target_name}"
        
    