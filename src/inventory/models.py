from django.db import models
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
        
    