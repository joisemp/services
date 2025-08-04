from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from . user_manager import UserManager
from django.utils.text import slugify
from config.utils import generate_unique_slug
from django.db.models.signals import post_delete
from django.dispatch import receiver
from service_management.models import WorkCategory
    
    
class User(AbstractUser):
    username = None
    email = models.EmailField(_('email address'), unique=True, null=True, blank=True)
    phone = models.CharField(_('phone number'), max_length=20, unique=True, null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='core_user_set',
        blank=True,
        help_text=_('The groups this user belongs to.'),
        verbose_name=_('groups'),
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='core_user_permissions_set',
        blank=True,
        help_text=_('Specific permissions for this user.'),
        verbose_name=_('user permissions'),
    )

    def has_usable_password(self):
        # General users have no password set
        if hasattr(self, 'profile') and self.profile.user_type == 'general_user':
            return False
        return super().has_usable_password()

    def __str__(self):
        return self.email if self.email else self.phone

    
class UserProfile(models.Model):
    USER_TYPE_CHOICES = [
        ('central_admin', 'Central Admin'),
        ('institution_admin', 'Insitution Admin'),
        ('departement_incharge', 'Departement Incharge'),
        ('room_incharge', 'Room Incharge'),
        ('space_admin', 'Space Admin'),
        ('maintainer', 'Maintainer'),
        ('general_user', 'General User'),
    ]

    user = models.OneToOneField(User, primary_key=True, on_delete=models.CASCADE, related_name='profile')
    org = models.ForeignKey('Organisation', null=True, on_delete=models.SET_NULL, related_name='org')
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    slug = models.SlugField(unique=True, db_index=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='general_user')
    skills = models.ManyToManyField('service_management.WorkCategory', related_name='skilled_users', blank=True)
    current_active_space = models.ForeignKey('service_management.Spaces', null=True, blank=True, on_delete=models.SET_NULL, related_name='current_active_users')
    
    # Maintainer space assignments - for space-specific or organization-wide availability
    assigned_spaces = models.ManyToManyField(
        'service_management.Spaces', 
        related_name='assigned_maintainers', 
        blank=True,
        help_text="Spaces this maintainer is assigned to. Leave empty for organization-wide availability."
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.first_name}-{self.last_name}{self.org}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{str(self.first_name)} {str(self.last_name)}" if self.first_name or self.last_name else str(self.user)
    
    def get_administered_spaces(self):
        """Get all spaces that this user administers"""
        from service_management.models import Spaces
        if self.user_type == 'space_admin':
            return self.user.administered_spaces.all()
        elif self.user_type == 'central_admin' and self.org:
            # Central admins can access all spaces in their organisation
            return self.org.spaces.all()
        return Spaces.objects.none()
    
    def can_administer_space(self, space):
        """Check if this user can administer the given space"""
        # Space admins can only administer their assigned spaces
        if self.user_type == 'space_admin':
            return space.is_user_admin(self.user)
        
        # Central admins can administer all spaces in their organisation
        if self.user_type == 'central_admin' and self.org:
            return space.org == self.org
            
        return False
    
    def switch_active_space(self, space):
        """Switch the user's current active space"""
        if self.can_administer_space(space):
            self.current_active_space = space
            self.save(update_fields=['current_active_space'])
            return True
        return False
    
    def get_available_spaces_for_switching(self):
        """Get all spaces this user can switch to"""
        return self.get_administered_spaces()
    
    def can_access_module_in_current_space(self, module_name):
        """Check if user can access a module in their current active space"""
        if not self.current_active_space:
            return False
        return self.current_active_space.can_user_access_module(self.user, module_name)
    
    def get_accessible_modules_in_current_space(self):
        """Get list of modules user can access in their current active space"""
        if not self.current_active_space:
            return []
        
        all_modules = ['dashboard', 'issue_management', 'service_management', 'transportation']
        accessible_modules = []
        
        for module in all_modules:
            if self.current_active_space.can_user_access_module(self.user, module):
                accessible_modules.append(module)
                
        return accessible_modules
    
    def is_organization_wide_maintainer(self):
        """Check if this maintainer is available organization-wide (no specific space assignments)"""
        return self.user_type == 'maintainer' and not self.assigned_spaces.exists()
    
    def get_maintainer_available_spaces(self):
        """Get spaces where this maintainer can work on issues"""
        if self.user_type != 'maintainer':
            return []
        
        if self.is_organization_wide_maintainer():
            # Organization-wide maintainer can work in all spaces in their org
            if self.org:
                return self.org.spaces.all()
            return []
        else:
            # Space-specific maintainer can only work in assigned spaces
            return self.assigned_spaces.all()
    
    def can_maintain_in_space(self, space):
        """Check if this maintainer can work on issues in the given space"""
        if self.user_type != 'maintainer':
            return False
        
        if not space or space.org != self.org:
            return False
        
        if self.is_organization_wide_maintainer():
            return True  # Can work anywhere in the organization
        else:
            return self.assigned_spaces.filter(id=space.id).exists()
    
    def can_be_assigned_to_issue(self, issue):
        """Check if this maintainer can be assigned to a specific issue"""
        if self.user_type != 'maintainer':
            return False
        
        # Check organization match
        if issue.org != self.org:
            return False
        
        # If issue has no space, only organization-wide maintainers can handle it
        if not issue.space:
            return self.is_organization_wide_maintainer()
        
        # Check space assignment
        return self.can_maintain_in_space(issue.space)
    

class Organisation(models.Model):
    CURRENCY_CHOICES = [
        ('INR', 'Indian Rupee (₹)'),
        ('USD', 'US Dollar ($)'),
        ('EUR', 'Euro (€)'),
        ('GBP', 'British Pound (£)'),
        ('JPY', 'Japanese Yen (¥)'),
    ]
    
    name = models.CharField(max_length=255, unique=True)
    address = models.TextField(blank=True)
    currency_code = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='INR')
    central_admins = models.ManyToManyField('User', related_name='managed_organisations', limit_choices_to={'profile__user_type': 'central_admin'})
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
    def get_space_count(self):
        """Get the number of spaces in this organisation"""
        return self.spaces.count()
    
    def get_space_admins(self):
        """Get all space admins across all spaces in this organisation"""
        from django.db.models import Q
        space_admin_ids = []
        for space in self.spaces.all():
            space_admin_ids.extend(space.space_admins.values_list('id', flat=True))
        
        return User.objects.filter(id__in=space_admin_ids).distinct()
    
    def is_user_central_admin(self, user):
        """Check if a user is a central admin of this organisation"""
        return self.central_admins.filter(id=user.id).exists()
    
    def get_currency_symbol(self):
        """Get currency symbol for this organisation"""
        from finance.currency import get_currency_symbol
        return get_currency_symbol(self.currency_code)


@receiver(post_delete, sender=UserProfile)
def delete_user_on_profile_delete(sender, instance, **kwargs):
    try:
        user = instance.user
        user.delete()
        print(f"User {user.email} and associated profile deleted successfully.")
    except Exception as e:
        print(f"Error occurred while deleting user: {str(e)}")

