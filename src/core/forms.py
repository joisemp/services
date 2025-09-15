from django import forms
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.urls import reverse
from config.mixins.form_mixin import BootstrapFormMixin
from .models import Organization, User


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
            reverse('password_reset_confirm', kwargs={
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