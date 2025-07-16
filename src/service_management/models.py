from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

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


class Spaces(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    org = models.ForeignKey('core.Organisation', on_delete=models.CASCADE, related_name='spaces')
    slug = models.SlugField(unique=True, db_index=True)
    
    # Access control settings
    is_access_enabled = models.BooleanField(default=True, help_text="Enable/disable access to this space")
    require_approval = models.BooleanField(default=False, help_text="Require admin approval for new space admins")
    
    # Admin relationships
    space_admins = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name='administered_spaces', 
        limit_choices_to={'profile__user_type': 'space_admin'},
        blank=True,
        help_text="Users who can administer this space"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_spaces')
    
    class Meta:
        verbose_name = "Space"
        verbose_name_plural = "Spaces"
        unique_together = ['name', 'org']
        
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.name}-{self.org.name}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} ({self.org.name})"
    
    def get_admin_count(self):
        """Return the number of space admins for this space"""
        return self.space_admins.count()
    
    def is_user_admin(self, user):
        """Check if a user is an admin of this space"""
        return self.space_admins.filter(id=user.id).exists()
    
    def is_user_central_admin(self, user):
        """Check if a user is a central admin of this space's organisation"""
        if not user.is_authenticated or not hasattr(user, 'profile'):
            return False
        return (user.profile.user_type == 'central_admin' and 
                user.profile.org == self.org)
    
    def can_user_manage_space(self, user):
        """Check if a user can manage this space (space admin or central admin)"""
        return self.is_user_admin(user) or self.is_user_central_admin(user)
    
    def can_user_access(self, user):
        """Check if a user can access this space"""
        if not self.is_access_enabled:
            return False
            
        if user.is_authenticated and hasattr(user, 'profile'):
            # Check if user is a space admin for this space
            if self.is_user_admin(user):
                return True
            
            # Check if user is a central admin of the organisation
            if (user.profile.user_type == 'central_admin' and 
                user.profile.org == self.org):
                return True
                
        return False
    
    def get_enabled_modules(self):
        """Get list of enabled modules for this space"""
        if hasattr(self, 'settings'):
            return self.settings.get_enabled_modules()
        return []
    
    def is_module_enabled(self, module_name):
        """Check if a specific module is enabled for this space"""
        if hasattr(self, 'settings'):
            return self.settings.is_module_enabled(module_name)
        return False
    
    def can_user_access_module(self, user, module_name):
        """Check if a user can access a specific module in this space"""
        if hasattr(self, 'settings'):
            return self.settings.can_user_access_module(user, module_name)
        return False


class SpaceSettings(models.Model):
    """Settings model to control module access for each space"""
    space = models.OneToOneField('Spaces', on_delete=models.CASCADE, related_name='settings')
    
    # Module Access Settings
    enable_issue_management = models.BooleanField(default=True, help_text="Enable/disable issue management")
    enable_service_management = models.BooleanField(default=True, help_text="Enable/disable service management")
    enable_transportation = models.BooleanField(default=False, help_text="Enable/disable transportation")
    enable_dashboard = models.BooleanField(default=True, help_text="Enable/disable dashboard")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='updated_space_settings')
    
    class Meta:
        verbose_name = "Space Settings"
        verbose_name_plural = "Space Settings"
    
    def __str__(self):
        return f"Settings for {self.space.name}"
    
    def get_enabled_modules(self):
        """Return a list of enabled modules for this space"""
        enabled_modules = []
        if self.enable_dashboard:
            enabled_modules.append('dashboard')
        if self.enable_issue_management:
            enabled_modules.append('issue_management')
        if self.enable_service_management:
            enabled_modules.append('service_management')
        if self.enable_transportation:
            enabled_modules.append('transportation')
        return enabled_modules
    
    def is_module_enabled(self, module_name):
        """Check if a specific module is enabled"""
        module_mapping = {
            'dashboard': self.enable_dashboard,
            'issue_management': self.enable_issue_management,
            'service_management': self.enable_service_management,
            'transportation': self.enable_transportation,
        }
        return module_mapping.get(module_name, False)
    
    def can_user_access_module(self, user, module_name):
        """Check if a user can access a specific module in this space"""
        # First check if the module is enabled for this space
        if not self.is_module_enabled(module_name):
            return False
        
        # Check if user can access the space
        if not self.space.can_user_access(user):
            return False
            
        return True


@receiver(post_save, sender=Spaces)
def create_space_settings(sender, instance, created, **kwargs):
    """Automatically create SpaceSettings when a new Space is created"""
    if created:
        SpaceSettings.objects.create(space=instance)
