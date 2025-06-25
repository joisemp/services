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

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.first_name}-{self.last_name}{self.org}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{str(self.first_name)} {str(self.last_name)}" if self.first_name or self.last_name else str(self.user)
    

class Organisation(models.Model):
    name = models.CharField(max_length=255, unique=True)
    address = models.TextField(blank=True)
    central_admins = models.ManyToManyField('User', related_name='managed_organisations', limit_choices_to={'profile__user_type': 'central_admin'})
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    

@receiver(post_delete, sender=UserProfile)
def delete_user_on_profile_delete(sender, instance, **kwargs):
    try:
        user = instance.user
        user.delete()
        print(f"User {user.email} and associated profile deleted successfully.")
    except Exception as e:
        print(f"Error occurred while deleting user: {str(e)}")

