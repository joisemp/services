from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django import forms
from .models import Organization, Space, User


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'address_line_one', 'address_line_two']
    list_filter = ['name']
    search_fields = ['name', 'description', 'address_line_one', 'address_line_two']
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'slug')
        }),
        ('Address Information', {
            'fields': ('address_line_one', 'address_line_two'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('spaces')


@admin.register(Space)
class SpaceAdmin(admin.ModelAdmin):
    list_display = ['name', 'org', 'slug', 'description_preview']
    list_filter = ['org', 'name']
    search_fields = ['name', 'description', 'org__name']
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ['org']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'slug')
        }),
        ('Organization', {
            'fields': ('org',)
        }),
    )
    
    def description_preview(self, obj):
        if obj.description:
            return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
        return 'No description'
    description_preview.short_description = 'Description Preview'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('org').prefetch_related('issues')


class UserCreationForm(forms.ModelForm):
    """A form for creating new users with proper validation"""
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput, required=False)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput, required=False)

    class Meta:
        model = User
        fields = ('phone_number', 'email', 'user_type', 'auth_method', 'organization', 'first_name', 'last_name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make auth_method read-only and set based on user_type
        self.fields['auth_method'].widget.attrs['readonly'] = True
        # Add help text for password fields
        self.fields['password1'].help_text = 'Only required for email authentication users. Phone users login without passwords.'
        self.fields['password2'].help_text = 'Confirm password for email authentication users.'

    def clean(self):
        cleaned_data = super().clean()
        user_type = cleaned_data.get('user_type')
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        phone_number = cleaned_data.get('phone_number')
        email = cleaned_data.get('email')

        # Set auth_method based on user_type and provided data
        if user_type == 'general_user':
            if phone_number and not email:
                cleaned_data['auth_method'] = 'phone'
            else:
                cleaned_data['auth_method'] = 'email'
        else:
            # All other roles must use email authentication
            cleaned_data['auth_method'] = 'email'

        auth_method = cleaned_data.get('auth_method')

        # Validate based on authentication method
        if auth_method == 'phone':
            if user_type != 'general_user':
                raise forms.ValidationError('Only general users can use phone authentication')
            if not phone_number:
                raise forms.ValidationError('Phone number is required for phone authentication')
            # No password required for phone authentication
        elif auth_method == 'email':
            if not email:
                raise forms.ValidationError('Email is required for email authentication')
            if not password1:
                raise forms.ValidationError('Password is required for email authentication')
            if password1 and password2 and password1 != password2:
                raise forms.ValidationError('Passwords do not match')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password1')
        
        if user.auth_method == 'email' and password:
            user.set_password(password)
        elif user.auth_method == 'phone':
            # Set unusable password for phone users
            user.set_unusable_password()
            
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """A form for updating users"""
    password = ReadOnlyPasswordHashField(
        label="Password",
        help_text="Raw passwords are not stored, so there is no way to see this "
                  "user's password, but you can change the password using "
                  "<a href=\"../password/\">this form</a>."
    )

    class Meta:
        model = User
        fields = ('phone_number', 'email', 'user_type', 'auth_method', 'organization', 'spaces', 
                 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make auth_method read-only
        self.fields['auth_method'].widget.attrs['readonly'] = True

    def clean_password(self):
        return self.initial["password"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = ('get_username', 'user_type', 'auth_method', 'organization', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('user_type', 'auth_method', 'is_staff', 'is_superuser', 'is_active', 'organization')
    search_fields = ('phone_number', 'email', 'first_name', 'last_name', 'organization__name')
    ordering = ('-date_joined',)
    filter_horizontal = ('spaces', 'groups', 'user_permissions')

    fieldsets = (
        ('Authentication', {
            'fields': ('phone_number', 'email', 'password', 'user_type', 'auth_method'),
            'description': 'Note: General users with phone authentication login without passwords. Only email authentication requires passwords.'
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name')
        }),
        ('Organization & Spaces', {
            'fields': ('organization', 'spaces')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = (
        ('User Role', {
            'classes': ('wide',),
            'fields': ('user_type',),
            'description': 'Select the user role. Only general users can use phone authentication.'
        }),
        ('Authentication', {
            'classes': ('wide',),
            'fields': ('phone_number', 'email', 'password1', 'password2'),
            'description': 'For general users: provide either phone number (passwordless login) or email+password. For all other roles: email and password are required.'
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name')
        }),
        ('Organization', {
            'fields': ('organization',)
        }),
    )

    def get_username(self, obj):
        return obj.username
    get_username.short_description = 'Username'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('organization').prefetch_related('spaces')
