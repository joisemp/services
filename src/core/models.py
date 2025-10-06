from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.auth.hashers import make_password
from django.core.validators import RegexValidator
from config.utils import generate_unique_slug
from django.utils.text import slugify


class UserManager(BaseUserManager):
    """
    Custom user manager to handle role-based user creation
    - General users with phone: passwordless authentication
    - All other users: email + password authentication
    """
    
    def create_user(self, phone_number=None, email=None, password=None, user_type='general_user', organization=None, **extra_fields):
        """
        Create and return a regular user with proper role-based authentication
        Phone number is now REQUIRED for all user types
        """
        # Only require organization for non-superusers
        if not organization and not extra_fields.get('is_superuser', False):
            raise ValueError('All users (except superusers) must be associated with an organization')
        
        # Phone number is MANDATORY for all users
        if not phone_number:
            raise ValueError('Phone number is required for all users')
        
        # Determine authentication method based on user type
        if user_type == 'general_user':
            # General users can use either phone or email authentication
            if phone_number and not email:
                # Phone authentication - no password required
                auth_method = 'phone'
                user = self.model(
                    phone_number=phone_number, 
                    user_type=user_type, 
                    auth_method=auth_method,
                    organization=organization, 
                    **extra_fields
                )
                # Set unusable password for phone users
                user.set_unusable_password()
            else:
                # Email authentication - password required
                auth_method = 'email'
                if not email:
                    raise ValueError('Email authentication requires an email address')
                if not password:
                    raise ValueError('Email authentication requires a password')
                email = self.normalize_email(email)
                user = self.model(
                    phone_number=phone_number,
                    email=email, 
                    user_type=user_type, 
                    auth_method=auth_method,
                    organization=organization, 
                    **extra_fields
                )
                user.set_password(password)
        else:
            # All other user types must use email authentication with password
            auth_method = 'email'
            if not email:
                raise ValueError(f'{user_type} users must have an email address')
            if not password:
                raise ValueError(f'{user_type} users must have a password')
            email = self.normalize_email(email)
            user = self.model(
                phone_number=phone_number,
                email=email, 
                user_type=user_type, 
                auth_method=auth_method,
                organization=organization, 
                **extra_fields
            )
            user.set_password(password)
        
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, organization=None, **extra_fields):
        """
        Create and return a superuser with email and password
        Superusers must use email authentication and don't require an organization
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'central_admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        if not email:
            raise ValueError('Superuser must have an email address.')
        if not password:
            raise ValueError('Superuser must have a password.')
        
        # Superusers don't need an organization - pass None or provided organization
        return self.create_user(
            email=email, 
            password=password, 
            organization=organization,  # Can be None for superusers
            **extra_fields
        )


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model supporting both phone and email authentication
    - General users with phone authentication: passwordless login (just phone number)
    - All other users: email + password authentication required
    """
    USER_TYPE_CHOICES = [
        ('central_admin', 'Central Admin'),
        ('space_admin', 'Space Admin'),
        ('maintainer', 'Maintainer'),
        ('supervisor', 'Supervisor'),
        ('reviewer', 'Reviewer'),
        ('general_user', 'General User'),
    ]
    
    # Authentication method choices
    AUTH_METHOD_CHOICES = [
        ('phone', 'Phone Authentication'),
        ('email', 'Email Authentication'),
    ]
    
    # Phone number field with validation
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(
        validators=[phone_regex], 
        max_length=17, 
        unique=True,
        help_text="Phone number is required for all users"
    )
    
    # Email field
    email = models.EmailField(
        unique=True, 
        null=True, 
        blank=True,
        help_text="Email address for password-based authentication"
    )
    
    # User type/role to distinguish user roles
    user_type = models.CharField(
        max_length=20, 
        choices=USER_TYPE_CHOICES, 
        default='general_user',
        help_text="Role of the user in the system"
    )
    
    # Authentication method (derived from user type)
    auth_method = models.CharField(
        max_length=10, 
        choices=AUTH_METHOD_CHOICES, 
        default='email',
        help_text="Authentication method for this user"
    )
    
    # Basic user information
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    
    # Organization and space relationships
    organization = models.ForeignKey(
        'Organization', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='users',
        help_text="Organization association (optional for superusers, required for all other users)"
    )
    spaces = models.ManyToManyField(
        'Space', 
        blank=True,
        related_name='users',
        help_text="Spaces are optional for users"
    )
    active_space = models.ForeignKey(
        'Space',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='active_users',
        help_text="Currently active space for space admins (used for context switching)"
    )
    
    objects = UserManager()
    
    # Set the field used for authentication - email for superusers and non-general users
    USERNAME_FIELD = 'email'  # Default to email for authentication
    REQUIRED_FIELDS = ['first_name', 'last_name']  # Fields required when creating superuser
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def has_usable_password(self):
        """
        Return False for phone authentication users (passwordless)
        Return True for email authentication users
        """
        if self.auth_method == 'phone':
            return False
        return super().has_usable_password()
    
    def check_password(self, raw_password):
        """
        Override to handle passwordless phone authentication
        Phone users don't need passwords, just return True if phone exists
        """
        if self.auth_method == 'phone':
            # For phone authentication, no password check needed
            return True
        return super().check_password(raw_password)
    
    def set_unusable_password(self):
        """
        Set unusable password for phone authentication users
        """
        if self.auth_method == 'phone':
            super().set_unusable_password()
        else:
            # For email users, don't automatically set unusable password
            pass
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Ensure every non-superuser has an organization
        if not self.organization and not self.is_superuser:
            raise ValidationError('Every user (except superusers) must be associated with an organization')
        
        # Phone number is MANDATORY for all users
        if not self.phone_number:
            raise ValidationError('Phone number is required for all users')
        
        # Only general users can use phone authentication
        if self.auth_method == 'phone' and self.user_type != 'general_user':
            raise ValidationError('Only general users can use phone authentication. Other user types must use email authentication.')
        
        # General users can use either phone or email, but others must use email
        if self.user_type != 'general_user':
            self.auth_method = 'email'
        
        # Validation based on authentication method
        if self.auth_method == 'phone':
            # Phone authentication: only requires phone number (no password)
            if not self.phone_number:
                raise ValidationError('Phone authentication users must have a phone number')
            # Clear email for phone users (except superusers)
            if self.email and not self.is_superuser:
                self.email = None
        elif self.auth_method == 'email':
            # Email authentication: requires both email and phone (password handled separately)
            if not self.email:
                raise ValidationError('Email authentication users must have an email address')
            # Phone number is still required for email authentication users
    
    def save(self, *args, **kwargs):
        # Only run full_clean if not explicitly skipped
        if not kwargs.pop('skip_validation', False):
            self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        if self.auth_method == 'phone' and self.phone_number:
            return f"{self.get_full_name()} ({self.get_user_type_display()})"
        elif self.auth_method == 'email' and self.email:
            return f"{self.get_full_name()} ({self.get_user_type_display()})"
        else:
            return f"User {self.id} ({self.get_user_type_display()})"
    
    def get_full_name(self):
        """Return the full name of the user"""
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_short_name(self):
        """Return the short name for the user"""
        return self.first_name or self.phone_number or self.email
    
    @property
    def username(self):
        """Return the username based on authentication method"""
        if self.auth_method == 'phone':
            return self.phone_number
        else:
            return self.email
        
    @property
    def is_central_admin(self):
        return self.user_type == 'central_admin'

    @property
    def is_space_admin(self):
        return self.user_type == 'space_admin'

    @property
    def is_maintainer(self):
        return self.user_type == 'maintainer'

    @property
    def is_supervisor(self):
        return self.user_type == 'supervisor'

    @property
    def is_reviewer(self):
        return self.user_type == 'reviewer'

    @property
    def is_general_user(self):
        return self.user_type == 'general_user'
    
    def get_available_spaces(self):
        """Get all spaces this user has access to"""
        if self.is_space_admin:
            return self.spaces.all()
        return Space.objects.none()
    
    def can_access_space(self, space):
        """Check if user can access a specific space"""
        if not self.is_space_admin:
            return False
        return self.spaces.filter(pk=space.pk).exists()
    
    def set_active_space(self, space):
        """Set the active space for this user"""
        if self.can_access_space(space):
            self.active_space = space
            self.save(skip_validation=True)
            return True
        return False



class Organization(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    address_line_one = models.CharField(max_length=255, blank=True, null=True)
    address_line_two = models.CharField(max_length=255, blank=True, null=True)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    
class Space(models.Model):
    name = models.CharField(max_length=255)
    label = models.CharField(max_length=100, blank=True, null=True, help_text="Optional short label for the space")
    description = models.TextField(blank=True, null=True)
    org = models.ForeignKey(Organization, related_name='spaces', on_delete=models.CASCADE)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.org.name})"


class Update(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    related_issue = models.ForeignKey('issue_management.Issue', related_name='updates', on_delete=models.CASCADE, null=True, blank=True)
    org = models.ForeignKey(Organization, related_name='updates', on_delete=models.CASCADE)
    space = models.ForeignKey(Space, related_name='updates', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(unique=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title
