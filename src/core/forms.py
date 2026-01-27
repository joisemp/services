from django import forms
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.urls import reverse
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm, UserCreationForm
from config.mixins.form_mixin import BootstrapFormMixin
from core.models import Organization, User, Space


class CustomPasswordResetForm(BootstrapFormMixin, PasswordResetForm):
    """
    Custom password reset form with Bootstrap styling
    """
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={
            'autocomplete': 'email'
        }),
        label="Email Address",
        help_text="Enter the email address associated with your account."
    )


class CustomSetPasswordForm(BootstrapFormMixin, SetPasswordForm):
    """
    Custom set password form with Bootstrap styling
    """
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'new-password'
        }),
        label="New Password",
        help_text="Your password must contain at least 8 characters and cannot be entirely numeric."
    )
    
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'new-password'
        }),
        label="Confirm New Password",
        help_text="Enter the same password as before, for verification."
    )


class OrganizationWithAdminForm(BootstrapFormMixin, forms.Form):
    """
    Form for super admins to register an organization along with its central admin
    """
    # Organization fields
    org_name = forms.CharField(
        max_length=255,
        label="Organization Name",
        help_text="Enter the name of the organization"
    )
    org_description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label="Organization Description",
        help_text="Optional description of the organization"
    )
    org_address_line_one = forms.CharField(
        max_length=255,
        required=False,
        label="Address Line 1",
        help_text="First line of organization address"
    )
    org_address_line_two = forms.CharField(
        max_length=255,
        required=False,
        label="Address Line 2",
        help_text="Second line of organization address"
    )
    
    # Central Admin fields
    admin_phone_number = forms.CharField(
        max_length=17,
        label="Central Admin Phone Number",
        help_text="Phone number for the central admin (required for all users)"
    )
    admin_first_name = forms.CharField(
        max_length=30,
        label="Central Admin First Name",
        help_text="First name of the central admin"
    )
    admin_last_name = forms.CharField(
        max_length=30,
        label="Central Admin Last Name",
        help_text="Last name of the central admin"
    )
    admin_email = forms.EmailField(
        label="Central Admin Email",
        help_text="Email address for the central admin (required for login)"
    )
    
    send_welcome_email = forms.BooleanField(
        initial=True,
        required=False,
        label="Send Welcome Email",
        help_text="Send a welcome email with password reset link to the central admin"
    )

    def clean_admin_email(self):
        email = self.cleaned_data['admin_email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def save(self, request=None):
        """
        Create the organization and central admin user
        """
        # Create organization
        organization = Organization.objects.create(
            name=self.cleaned_data['org_name'],
            description=self.cleaned_data['org_description'],
            address_line_one=self.cleaned_data['org_address_line_one'],
            address_line_two=self.cleaned_data['org_address_line_two']
        )
        
        # Create central admin user
        central_admin = User.objects.create_user(
            phone_number=self.cleaned_data['admin_phone_number'],
            email=self.cleaned_data['admin_email'],
            password='temporary_password_will_be_reset',  # Temporary password, will be made unusable
            user_type='central_admin',
            organization=organization,
            first_name=self.cleaned_data['admin_first_name'],
            last_name=self.cleaned_data['admin_last_name']
        )
        
        # Set unusable password immediately - user will set it via password reset link
        central_admin.set_unusable_password()
        central_admin.save()
        
        # Send welcome email if requested
        if self.cleaned_data['send_welcome_email'] and request:
            self._send_welcome_email(central_admin, request)
        
        return organization, central_admin

    def _send_welcome_email(self, user, request):
        """
        Send welcome email with password reset link to the central admin
        """
        current_site = get_current_site(request)
        site_name = current_site.name
        domain = current_site.domain
        
        # Generate password reset token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Create password reset URL
        password_reset_url = request.build_absolute_uri(
            reverse('core:password_reset_confirm', kwargs={
                'uidb64': uid,
                'token': token,
            })
        )
        
        # Email context
        context = {
            'user': user,
            'organization': user.organization,
            'site_name': site_name,
            'domain': domain,
            'password_reset_url': password_reset_url,
            'protocol': 'https' if request.is_secure() else 'http',
        }
        
        # Render email templates
        subject = render_to_string('emails/welcome_central_admin_subject.txt', context)
        subject = ''.join(subject.splitlines())  # Remove newlines
        
        html_message = render_to_string('emails/welcome_central_admin.html', context)
        text_message = render_to_string('emails/welcome_central_admin.txt', context)
        
        # Send email
        send_mail(
            subject=subject,
            message=text_message,
            html_message=html_message,
            from_email=None,  # Uses DEFAULT_FROM_EMAIL
            recipient_list=[user.email],
            fail_silently=False,
        )


class PhoneLoginForm(BootstrapFormMixin, forms.Form):
    """
    Login form for general users using phone number only (passwordless)
    """
    phone_number = forms.CharField(
        max_length=17,
        widget=forms.TextInput(attrs={
            'autocomplete': 'tel'
        }),
        label="Phone Number",
        help_text="Enter your phone number without country code"
    )

    def clean_phone_number(self):
        phone_number = self.cleaned_data['phone_number']
        
        # Check if user exists with this phone number
        try:
            user = User.objects.get(
                phone_number=phone_number,
                auth_method='phone',
                user_type='general_user',
                is_active=True
            )
        except User.DoesNotExist:
            raise forms.ValidationError("No active general user found with this phone number.")
        
        return phone_number


class EmailLoginForm(BootstrapFormMixin, forms.Form):
    """
    Login form for non-general users using email + password
    """
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'autocomplete': 'email'
        }),
        label="Email Address"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'current-password'
        }),
        label="Password"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password'].widget.attrs.pop('placeholder', None)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')
        
        if email and password:
            # Check if user exists and password is correct
            try:
                user = User.objects.get(
                    email=email,
                    auth_method='email',
                    is_active=True
                )
                # Exclude general users
                if user.user_type == 'general_user':
                    raise forms.ValidationError("General users should use phone number login.")
                
                # Check password
                if not user.has_usable_password():
                    raise forms.ValidationError("Please use the password reset link sent to your email to set your password.")
                
                if not user.check_password(password):
                    raise forms.ValidationError("Invalid email or password.")
                    
            except User.DoesNotExist:
                raise forms.ValidationError("Invalid email or password.")
        
        return cleaned_data


class PinLoginForm(BootstrapFormMixin, forms.Form):
    """
    Login form for non-general users using email + 4-digit PIN
    """
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'autocomplete': 'email'
        }),
        label="Email Address"
    )
    pin = forms.CharField(
        max_length=4,
        min_length=4,
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'off',
            'inputmode': 'numeric',
            'pattern': '[0-9]{4}',
            'maxlength': '4'
        }),
        label="4-Digit PIN",
        help_text="Enter your 4-digit PIN"
    )

    def clean_pin(self):
        pin = self.cleaned_data.get('pin')
        if pin and (not pin.isdigit() or len(pin) != 4):
            raise forms.ValidationError("PIN must be exactly 4 digits.")
        return pin

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        pin = cleaned_data.get('pin')
        
        if email and pin:
            # Check if user exists and PIN is correct
            try:
                user = User.objects.get(
                    email=email,
                    auth_method='email',
                    is_active=True
                )
                # Exclude general users and superusers
                if user.user_type == 'general_user':
                    raise forms.ValidationError("General users should use phone number login.")
                
                if user.is_superuser:
                    raise forms.ValidationError("Superusers cannot use PIN login. Please use password login.")
                
                # Check if user has a PIN set
                if not user.has_pin():
                    raise forms.ValidationError("You haven't set up a PIN yet. Please login with your password first to set up your PIN.")
                
                # Check PIN
                if not user.check_pin(pin):
                    raise forms.ValidationError("Invalid email or PIN.")
                    
            except User.DoesNotExist:
                raise forms.ValidationError("Invalid email or PIN.")
        
        return cleaned_data


class SetPinForm(BootstrapFormMixin, forms.Form):
    """
    Form for users to set or change their 4-digit PIN
    """
    pin = forms.CharField(
        max_length=4,
        min_length=4,
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'off',
            'inputmode': 'numeric',
            'pattern': '[0-9]{4}',
            'maxlength': '4'
        }),
        label="New PIN",
        help_text="Enter a 4-digit PIN (numbers only)"
    )
    confirm_pin = forms.CharField(
        max_length=4,
        min_length=4,
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'off',
            'inputmode': 'numeric',
            'pattern': '[0-9]{4}',
            'maxlength': '4'
        }),
        label="Confirm PIN",
        help_text="Re-enter your 4-digit PIN"
    )

    def clean_pin(self):
        pin = self.cleaned_data.get('pin')
        if pin and (not pin.isdigit() or len(pin) != 4):
            raise forms.ValidationError("PIN must be exactly 4 digits.")
        return pin

    def clean_confirm_pin(self):
        confirm_pin = self.cleaned_data.get('confirm_pin')
        if confirm_pin and (not confirm_pin.isdigit() or len(confirm_pin) != 4):
            raise forms.ValidationError("PIN must be exactly 4 digits.")
        return confirm_pin

    def clean(self):
        cleaned_data = super().clean()
        pin = cleaned_data.get('pin')
        confirm_pin = cleaned_data.get('confirm_pin')
        
        if pin and confirm_pin:
            if pin != confirm_pin:
                raise forms.ValidationError("The two PIN fields didn't match.")
        
        return cleaned_data


class GeneralUserCreateForm(BootstrapFormMixin, forms.ModelForm):
    """
    Form for creating general users with phone-only authentication (passwordless)
    """
    class Meta:
        model = User
        fields = ['phone_number', 'first_name', 'last_name']
        
    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)
        self.fields['phone_number'].help_text = 'Phone number is required for all users (enter without country code)'

    def clean(self):
        cleaned_data = super().clean()
        # Pre-set the auth_method and user_type for validation
        if hasattr(self, 'instance'):
            self.instance.user_type = 'general_user'
            self.instance.auth_method = 'phone'
            self.instance.email = None  # Clear email for phone users
            # Assign organization before validation
            if self.current_user and self.current_user.organization:
                self.instance.organization = self.current_user.organization
            # Set a dummy password to pass Django's built-in validation
            self.instance.set_password('dummy_password_for_validation')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        
        if commit:
            user.save()
            # Now make the password unusable after saving
            user.set_unusable_password()
            user.save(skip_validation=True)
        return user


class OtherRoleUserCreateForm(BootstrapFormMixin, forms.ModelForm):
    """
    Form for creating users with email + auto-generated password authentication
    (central_admin, space_admin, maintainer, supervisor, reviewer)
    Phone number is now required for all user types
    """
    USER_TYPE_CHOICES = [
        ('central_admin', 'Central Admin'),
        ('space_admin', 'Space Admin'),
        ('maintainer', 'Maintainer'),
        ('supervisor', 'Supervisor'),
        ('reviewer', 'Reviewer'),
    ]

    phone_number = forms.CharField(
        max_length=17,
        required=True,
        label="Phone Number",
        help_text="Phone number is required for all users (enter without country code)"
    )
    email = forms.EmailField(
        required=True,
    )
    first_name = forms.CharField(
        max_length=30, 
        required=True,
    )
    last_name = forms.CharField(
        max_length=30, 
        required=True,
    )
    user_type = forms.ChoiceField(
        choices=USER_TYPE_CHOICES, 
        required=True,
        label="User Role"
    )

    class Meta:
        model = User
        fields = ['phone_number', 'email', 'first_name', 'last_name', 'user_type']

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        # Set organization and other fields on instance before validation
        if hasattr(self, 'instance'):
            self.instance.auth_method = 'email'
            # Assign organization before validation
            if self.current_user and self.current_user.organization:
                self.instance.organization = self.current_user.organization
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Set a dummy password first to pass validation
        user.set_password('dummy_password_for_validation')
        
        if commit:
            user.save()
            # Now set unusable password - user will set it via password reset link
            user.set_unusable_password()
            user.save(skip_validation=True)
        return user

    def send_password_reset_email(self, user, request):
        """
        Send password reset email to the newly created user
        """
        current_site = get_current_site(request)
        site_name = current_site.name
        domain = current_site.domain
        
        # Generate password reset token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Create password reset URL
        password_reset_url = request.build_absolute_uri(
            reverse('core:password_reset_confirm', kwargs={
                'uidb64': uid,
                'token': token,
            })
        )
        
        # Email context
        context = {
            'user': user,
            'organization': user.organization,
            'site_name': site_name,
            'domain': domain,
            'password_reset_url': password_reset_url,
            'protocol': 'https' if request.is_secure() else 'http',
        }
        
        # Render email templates
        subject = f'Welcome to {site_name} - Set Your Password'
        
        # Simple text email for now
        message = f"""
Welcome to {site_name}!

Your account has been created with the following details:
- Name: {user.get_full_name()}
- Email: {user.email}
- Role: {user.get_user_type_display()}
- Organization: {user.organization.name}

Please click the link below to set your password and activate your account:
{password_reset_url}

This link will expire in 24 hours for security reasons.

If you have any questions, please contact your administrator.

Best regards,
{site_name} Team
        """
        
        # Send email
        send_mail(
            subject=subject,
            message=message,
            from_email=None,  # Uses DEFAULT_FROM_EMAIL
            recipient_list=[user.email],
            fail_silently=False,
        )
        
class SpaceCreateForm(BootstrapFormMixin, forms.ModelForm):
    """
    Form for creating a new space
    """
    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': 'Space Name'}),
        label="Space Name",
        help_text="Enter the name of the space"
    )
    label = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Optional short label'}),
        label="Label",
        help_text="Optional short label for the space"
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Space Description'}),
        required=False,
        label="Description",
        help_text="Optional description of the space"
    )

    class Meta:
        model = Space
        fields = ['name', 'label', 'description']

    def clean_name(self):
        name = self.cleaned_data['name']
        if Space.objects.filter(name=name).exists():
            raise forms.ValidationError("A space with this name already exists.")
        return name
    

class SpaceUpdateForm(BootstrapFormMixin, forms.ModelForm):
    """
    Form for updating an existing space
    """
    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': 'Space Name'}),
        label="Space Name",
        help_text="Enter the name of the space"
    )
    label = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Optional short label'}),
        label="Label",
        help_text="Optional short label for the space"
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Space Description'}),
        required=False,
        label="Description",
        help_text="Optional description of the space"
    )

    class Meta:
        model = Space
        fields = ['name', 'label', 'description']

    def clean_name(self):
        name = self.cleaned_data['name']
        # Exclude current instance from validation
        qs = Space.objects.filter(name=name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A space with this name already exists.")
        return name


class SpaceUserAddForm(BootstrapFormMixin, forms.Form):
    """
    Form for adding existing users to a space
    """
    users = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        label="Select Users",
        help_text="Choose users to add to this space"
    )

    def __init__(self, space, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.space = space
        # Get only space_admin users from the same organization who aren't already in this space
        available_users = User.objects.filter(
            organization=space.org,
            user_type='space_admin'
        ).exclude(
            spaces=space
        ).order_by('first_name', 'last_name')
        
        # Set choices for the multiple choice field (ensure keys are strings)
        self.fields['users'].choices = [
            (str(user.id), str(user)) for user in available_users
        ]
        
        # Store available users for validation (use string keys to match choices)
        self.available_users = {str(user.id): user for user in available_users}
    
    def clean_users(self):
        """
        Custom validation and conversion for users field
        """
        user_ids = self.cleaned_data.get('users', [])
        if not user_ids:
            return []
        
        # Get user objects from string IDs
        users = []
        for user_id in user_ids:
            if user_id in self.available_users:
                users.append(self.available_users[user_id])
            else:
                raise forms.ValidationError(f"Invalid user selection: {user_id}")
        
        return users


class SpaceUserRemoveForm(BootstrapFormMixin, forms.Form):
    """
    Form for removing users from a space
    """
    user_id = forms.IntegerField(widget=forms.HiddenInput())

    def __init__(self, space, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.space = space
    
    def clean_user_id(self):
        """
        Validate that the user exists and is in the space
        """
        user_id = self.cleaned_data.get('user_id')
        if not user_id:
            raise forms.ValidationError("User ID is required.")
        
        try:
            user = User.objects.get(id=user_id)
            if user not in self.space.users.all():
                raise forms.ValidationError("User is not in this space.")
            return user
        except User.DoesNotExist:
            raise forms.ValidationError("User not found.")


class SpaceSwitcherForm(BootstrapFormMixin, forms.Form):
    """
    Form for space admins to switch their active space context
    """
    space = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        # Set the current active space slug as initial value
        if user.active_space:
            self.fields['space'].initial = user.active_space.slug

    def clean_space(self):
        """
        Validate that the space exists and user has access to it
        """
        space_slug = self.cleaned_data['space']
        try:
            space = Space.objects.get(slug=space_slug)
            if not self.user.can_access_space(space):
                raise forms.ValidationError("You do not have access to this space.")
            return space_slug
        except Space.DoesNotExist:
            raise forms.ValidationError("The selected space does not exist.")

    def save(self):
        """Set the selected space as the user's active space"""
        if self.is_valid():
            space_slug = self.cleaned_data['space']
            try:
                space = Space.objects.get(slug=space_slug)
                return self.user.set_active_space(space)
            except Space.DoesNotExist:
                return False
        return False