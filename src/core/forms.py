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
from .models import Organization, User, Space


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


class GeneralUserCreateForm(BootstrapFormMixin, forms.ModelForm):
    """
    Form for creating general users with phone-only authentication (passwordless)
    """
    class Meta:
        model = User
        fields = ['phone_number', 'first_name', 'last_name', 'organization']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['phone_number'].help_text = 'Enter phone number without country code'
        self.fields['organization'].queryset = Organization.objects.all()
        self.fields['organization'].empty_label = "Select an organization"

    def clean(self):
        cleaned_data = super().clean()
        # Pre-set the auth_method and user_type for validation
        if hasattr(self, 'instance'):
            self.instance.user_type = 'general_user'
            self.instance.auth_method = 'phone'
            self.instance.email = None  # Clear email for phone users
            # Set a dummy password to pass Django's built-in validation
            self.instance.set_password('dummy_password_for_validation')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        # Set these fields before any validation
        user.user_type = 'general_user'
        user.auth_method = 'phone'
        
        # Clear email field for phone users to avoid validation conflicts
        user.email = None
        
        # Set a dummy password first to pass validation, then make it unusable
        user.set_password('dummy_password_for_validation')
        
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
    """
    USER_TYPE_CHOICES = [
        ('central_admin', 'Central Admin'),
        ('space_admin', 'Space Admin'),
        ('maintainer', 'Maintainer'),
        ('supervisor', 'Supervisor'),
        ('reviewer', 'Reviewer'),
    ]

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
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(),
        required=True,
        empty_label="Select an organization"
    )

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'user_type', 'organization']

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.user_type = self.cleaned_data['user_type']
        user.organization = self.cleaned_data['organization']
        user.auth_method = 'email'
        
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
        fields = ['name', 'label', 'description', 'org']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Map the org field to organization for clarity in the form
        self.fields['org'].label = "Organization"
        self.fields['org'].help_text = "Select the organization this space belongs to"
        self.fields['org'].empty_label = "Select an organization"

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
    
    