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
    
    def get_available_maintainers(self):
        """Get all maintainers who can work on issues in this space"""
        from core.models import User
        from django.db.models import Q
        
        # Get maintainers who can work in this space:
        # 1. Organization-wide maintainers (no space assignments)
        # 2. Space-specific maintainers assigned to this space
        return User.objects.filter(
            Q(profile__user_type='maintainer') &
            Q(profile__org=self.org) &
            (Q(profile__assigned_spaces__isnull=True) | Q(profile__assigned_spaces=self))
        ).distinct()
    
    def get_assigned_maintainers_count(self):
        """Get count of maintainers specifically assigned to this space"""
        return self.assigned_maintainers.count()
    
    def get_organization_wide_maintainers_count(self):
        """Get count of organization-wide maintainers available to this space"""
        from core.models import User
        return User.objects.filter(
            profile__user_type='maintainer',
            profile__org=self.org,
            profile__assigned_spaces__isnull=True
        ).count()
    
    def get_maintainer_breakdown(self):
        """Get a breakdown of maintainer availability for this space"""
        total_available = self.get_available_maintainers().count()
        space_specific = self.get_assigned_maintainers_count()
        organization_wide = self.get_organization_wide_maintainers_count()
        
        return {
            'total_available': total_available,
            'space_specific': space_specific,
            'organization_wide': organization_wide
        }


class SpaceSettings(models.Model):
    """Settings model to control module access for each space"""
    space = models.OneToOneField('Spaces', on_delete=models.CASCADE, related_name='settings')
    
    # Module Access Settings
    enable_issue_management = models.BooleanField(default=True, help_text="Enable/disable issue management")
    enable_service_management = models.BooleanField(default=True, help_text="Enable/disable service management")
    enable_transportation = models.BooleanField(default=False, help_text="Enable/disable transportation")
    enable_finance = models.BooleanField(default=True, help_text="Enable/disable finance management")
    enable_marketplace = models.BooleanField(default=True, help_text="Enable/disable marketplace")
    enable_asset_management = models.BooleanField(default=False, help_text="Enable/disable asset management")
    
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
        if self.enable_issue_management:
            enabled_modules.append('issue_management')
        if self.enable_service_management:
            enabled_modules.append('service_management')
        if self.enable_transportation:
            enabled_modules.append('transportation')
        if self.enable_finance:
            enabled_modules.append('finance')
        if self.enable_marketplace:
            enabled_modules.append('marketplace')
        if self.enable_asset_management:
            enabled_modules.append('asset_management')
        return enabled_modules
    
    def is_module_enabled(self, module_name):
        """Check if a specific module is enabled"""
        module_mapping = {
            'issue_management': self.enable_issue_management,
            'service_management': self.enable_service_management,
            'transportation': self.enable_transportation,
            'finance': self.enable_finance,
            'marketplace': self.enable_marketplace,
            'asset_management': self.enable_asset_management,
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
