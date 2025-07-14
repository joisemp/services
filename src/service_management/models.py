from django.db import models
from django.utils.text import slugify
from django.conf import settings

from config.utils import generate_unique_slug

# Create your models here.

class WorkCategory(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    org = models.ForeignKey('core.Organisation', related_name='work_categories', on_delete=models.CASCADE)
    slug = models.SlugField(unique=True, db_index=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ShoppingList(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('purchase_created', 'Purchase Order Created'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_shopping_lists')
    org = models.ForeignKey('core.Organisation', on_delete=models.CASCADE, related_name='shopping_lists')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    budget_limit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_shopping_lists')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(unique=True, db_index=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.name}-{self.created_by.id}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    def calculate_total_cost(self):
        """Calculate total cost from all items"""
        total = self.items.aggregate(
            total=models.Sum('estimated_cost')
        )['total'] or 0
        self.total_cost = total
        self.save(update_fields=['total_cost'])
        return total
    
    def __str__(self):
        return f"{self.name} - {self.org.name}"
    
    class Meta:
        ordering = ['-created_at']


class ShoppingListItem(models.Model):
    shopping_list = models.ForeignKey(ShoppingList, on_delete=models.CASCADE, related_name='items')
    item_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    quantity = models.PositiveIntegerField(default=1)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    supplier = models.CharField(max_length=255, blank=True)
    category = models.ForeignKey(WorkCategory, on_delete=models.SET_NULL, null=True, blank=True)
    is_purchased = models.BooleanField(default=False)
    purchase_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True, db_index=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.item_name}-{self.shopping_list.slug}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
        # Recalculate shopping list total cost
        self.shopping_list.calculate_total_cost()
    
    def delete(self, *args, **kwargs):
        shopping_list = self.shopping_list
        super().delete(*args, **kwargs)
        # Recalculate shopping list total cost after deletion
        shopping_list.calculate_total_cost()
    
    def __str__(self):
        return f"{self.item_name} - {self.shopping_list.name}"
    
    class Meta:
        ordering = ['created_at']


class Purchase(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('ordered', 'Ordered'),
        ('received', 'Received'),
        ('completed', 'Completed'),
    ]
    
    purchase_id = models.CharField(max_length=50, unique=True, blank=True)
    shopping_list = models.ForeignKey(ShoppingList, on_delete=models.CASCADE, related_name='purchases')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    ordered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ordered_purchases')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_purchases')
    supplier_name = models.CharField(max_length=255, blank=True)
    supplier_contact = models.CharField(max_length=255, blank=True)
    order_date = models.DateTimeField(null=True, blank=True)
    expected_delivery = models.DateTimeField(null=True, blank=True)
    actual_delivery = models.DateTimeField(null=True, blank=True)
    invoice_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(unique=True, db_index=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.purchase_id:
            import uuid
            self.purchase_id = f"PUR-{uuid.uuid4().hex[:8].upper()}"
        if not self.slug:
            base_slug = slugify(f"{self.purchase_id}-{self.shopping_list.name}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Purchase {self.purchase_id} - {self.shopping_list.name}"
    
    class Meta:
        ordering = ['-created_at']


class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='items')
    shopping_list_item = models.ForeignKey(ShoppingListItem, on_delete=models.CASCADE)
    quantity_ordered = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_received = models.PositiveIntegerField(default=0)
    is_received = models.BooleanField(default=False)
    received_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    slug = models.SlugField(unique=True, db_index=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.shopping_list_item.item_name}-{self.purchase.purchase_id}")
            self.slug = generate_unique_slug(self, base_slug)
        
        # Always recalculate the total cost when saving
        from decimal import Decimal
        self.total_cost = Decimal(self.quantity_ordered) * Decimal(self.unit_cost)
        
        # Update the purchase total when this item changes
        super().save(*args, **kwargs)
        
        # Recalculate purchase total
        if self.purchase:
            total = self.purchase.items.aggregate(
                total=models.Sum('total_cost')
            )['total'] or Decimal('0.00')
            
            if self.purchase.total_amount != total:
                self.purchase.total_amount = total
                self.purchase.save(update_fields=['total_amount'])
    
    def __str__(self):
        return f"{self.shopping_list_item.item_name} - {self.purchase.purchase_id}"


class ShoppingListStatusHistory(models.Model):
    """Track status changes and comments for shopping lists"""
    shopping_list = models.ForeignKey(ShoppingList, on_delete=models.CASCADE, related_name='status_history')
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    old_status = models.CharField(max_length=20, choices=ShoppingList.STATUS_CHOICES)
    new_status = models.CharField(max_length=20, choices=ShoppingList.STATUS_CHOICES)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True, db_index=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.shopping_list.slug}-{self.old_status}-{self.new_status}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.shopping_list.name} - {self.old_status} to {self.new_status}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Shopping List Status History'
        verbose_name_plural = 'Shopping List Status Histories'
