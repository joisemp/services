from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import views as auth_views, authenticate, login, logout
from django.urls import reverse_lazy
from django.views.generic import FormView, View
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
import secrets
import string
from .forms import (
    CustomPasswordResetForm, 
    CustomSetPasswordForm, 
    GeneralUserCreateForm, 
    OtherRoleUserCreateForm,
    PhoneLoginForm,
    EmailLoginForm,
    PinLoginForm,
    SetPinForm,
    SpaceCreateForm,
    SpaceUpdateForm,
    SpaceUserAddForm,
    SpaceUserRemoveForm,
    SpaceSwitcherForm
)
from .models import Update, User, Space
from django.views.generic import ListView, CreateView, TemplateView, DetailView, UpdateView, DeleteView
from config.mixins.access_mixin import CentralAdminOnlyAccessMixin, RedirectLoggedinUsers


class CustomPasswordResetView(auth_views.PasswordResetView):
    """
    Custom password reset view with Bootstrap form and custom templates
    """
    template_name = 'registration/password_reset_form.html'
    form_class = CustomPasswordResetForm
    email_template_name = 'emails/password_reset_email.txt'
    html_email_template_name = 'emails/password_reset_email.html'
    subject_template_name = 'emails/password_reset_subject.txt'
    success_url = reverse_lazy('core:password_reset_done')


class CustomPasswordResetDoneView(auth_views.PasswordResetDoneView):
    """
    Custom password reset done view
    """
    template_name = 'registration/password_reset_done.html'


class CustomPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    """
    Custom password reset confirm view with Bootstrap form
    """
    template_name = 'registration/password_reset_confirm.html'
    form_class = CustomSetPasswordForm
    success_url = reverse_lazy('core:password_reset_complete')


class CustomPasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    """
    Custom password reset complete view
    """
    template_name = 'registration/password_reset_complete.html'
    

class PeopleListView(CentralAdminOnlyAccessMixin, ListView):
    """
    View to list users in the same organization as the central admin user
    """
    model = User
    template_name = 'core/people_list.html'
    context_object_name = 'users'

    def get_queryset(self):
        # Filter users by the central admin's organization
        admin_organization = self.request.user.organization
        return User.objects.filter(
            organization=admin_organization
        ).select_related('organization').prefetch_related('spaces').order_by('first_name', 'last_name')
    

class PeopleCreateView(CentralAdminOnlyAccessMixin, CreateView):
    """
    View to create a new user with role-specific forms
    """
    model = User
    template_name = 'core/people_form.html'
    success_url = reverse_lazy('core:people_list')

    def get_form_class(self):
        """
        Return the appropriate form class based on user_type parameter
        """
        user_type = self.request.GET.get('type', 'other')
        if user_type == 'general':
            return GeneralUserCreateForm
        return OtherRoleUserCreateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_type = self.request.GET.get('type', 'other')
        context['user_type'] = user_type
        context['form_title'] = 'Create General User' if user_type == 'general' else 'Create User'
        return context

    def get_form_kwargs(self):
        """
        Return the keyword arguments for instantiating the form.
        """
        kwargs = super().get_form_kwargs()
        kwargs['current_user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        """
        Handle successful form submission
        """
        # Save the user with current user's organization
        self.object = form.save()
        user_type = self.request.GET.get('type', 'other')
        
        # Add success message
        from django.contrib import messages
        if user_type == 'general':
            messages.success(
                self.request, 
                f'General user {self.object.get_full_name()} created successfully. They can login with their phone number.'
            )
        else:
            # Send password reset email for other roles
            try:
                form.send_password_reset_email(self.object, self.request)
                messages.success(
                    self.request, 
                    f'User {self.object.get_full_name()} created successfully. '
                    f'A password reset link has been sent to {self.object.email}. '
                    f'They should check their email to set their password and activate their account.'
                )
            except Exception as e:
                messages.warning(
                    self.request,
                    f'User {self.object.get_full_name()} created successfully, but there was an error sending the password reset email. '
                    f'Please manually send them a password reset link.'
                )
        
        return redirect(self.get_success_url())


class CustomLoginView(RedirectLoggedinUsers, FormView):
    """
    Custom login view that handles phone, email+password, and email+PIN authentication
    """
    template_name = 'core/login.html'

    def get_form_class(self):
        """
        Return the appropriate form class based on user_type parameter
        """
        user_type = self.request.GET.get('type', 'email')
        if user_type == 'phone':
            return PhoneLoginForm
        elif user_type == 'pin':
            return PinLoginForm
        return EmailLoginForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_type = self.request.GET.get('type', 'email')
        context['user_type'] = user_type
        if user_type == 'phone':
            context['form_title'] = 'Phone Login'
        elif user_type == 'pin':
            context['form_title'] = 'PIN Login'
        else:
            context['form_title'] = 'Email Login'
        return context

    def form_valid(self, form):
        """
        Handle successful form submission and authenticate user
        """
        user_type = self.request.GET.get('type', 'email')
        
        if user_type == 'phone':
            # Phone authentication
            phone_number = form.cleaned_data['phone_number']
            user = authenticate(
                self.request,
                phone_number=phone_number
            )
        elif user_type == 'pin':
            # PIN authentication
            email = form.cleaned_data['email']
            pin = form.cleaned_data['pin']
            user = authenticate(
                self.request,
                username=email,
                pin=pin
            )
        else:
            # Email + password authentication
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(
                self.request,
                username=email,
                password=password
            )

        if user is not None:
            login(self.request, user)
            from django.contrib import messages
            messages.success(
                self.request,
                f'Welcome back, {user.get_full_name() or user.get_short_name()}!'
            )
            return super().form_valid(form)
        else:
            # Authentication failed
            from django.contrib import messages
            messages.error(
                self.request,
                'Authentication failed. Please check your credentials and try again.'
            )
            return self.form_invalid(form)

    def dispatch(self, request, *args, **kwargs):
        """
        Redirect already authenticated users
        """
        if request.user.is_authenticated:
            # Let the RedirectLoggedinUsers mixin handle it
            return super().dispatch(request, *args, **kwargs)
        return super().dispatch(request, *args, **kwargs)


def custom_logout_view(request):
    """
    Custom logout view that handles logout and redirects to login page
    """
    if request.user.is_authenticated:
        user_name = request.user.get_full_name() or request.user.get_short_name()
        logout(request)
        from django.contrib import messages
        messages.success(request, f'You have been successfully logged out. Goodbye, {user_name}!')
    
    return redirect('core:login')


class SetPinView(FormView):
    """
    View for users to set or change their 4-digit PIN
    Only available for eligible user types (not general_user or superuser)
    """
    template_name = 'core/set_pin.html'
    form_class = SetPinForm
    
    def _get_redirect_url_for_user(self, user):
        """Get the appropriate redirect URL based on user role"""
        if user.is_central_admin:
            return 'dashboard:central_admin_dashboard'
        elif user.is_space_admin:
            return 'core:switch_space'
        elif user.is_supervisor:
            return 'issue_management:supervisor:issue_list'
        elif user.is_maintainer:
            return 'issue_management:maintainer:work_task_list'
        else:
            return 'home'
    
    def get_success_url(self):
        """Redirect to the previous page or role-specific dashboard"""
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        # Get role-specific redirect
        return reverse_lazy(self._get_redirect_url_for_user(self.request.user))
    
    def dispatch(self, request, *args, **kwargs):
        # Only allow authenticated users
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to set a PIN.")
            return redirect('core:login')
        
        # Only allow eligible user types (not general_user)
        if request.user.user_type == 'general_user':
            messages.error(request, "General users cannot set a PIN.")
            return redirect(self._get_redirect_url_for_user(request.user))
        
        # Allow central admins even if they're superusers (created via createsuperuser)
        # Only block "pure" superusers without a proper role
        if request.user.is_superuser and not request.user.is_central_admin:
            messages.error(request, "Superusers without a role cannot set a PIN.")
            return redirect(self._get_redirect_url_for_user(request.user))
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['has_pin'] = self.request.user.has_pin()
        return context
    
    def form_valid(self, form):
        """
        Handle successful form submission and set the PIN
        """
        pin = form.cleaned_data['pin']
        
        try:
            self.request.user.set_pin(pin)
            self.request.user.save(skip_validation=True)
            
            messages.success(
                self.request,
                'Your PIN has been set successfully! You can now use it to login quickly.'
            )
        except Exception as e:
            messages.error(
                self.request,
                f'Error setting PIN: {str(e)}'
            )
            return self.form_invalid(form)
        
        return super().form_valid(form)  


class UpdateListView(ListView):
    """
    View to list all updates in the system
    """
    model = Update
    template_name = 'core/updates_list.html'
    context_object_name = 'updates'

    def get_queryset(self):
        return Update.objects.all().order_by('-created_at')


class SpaceCreateView(CentralAdminOnlyAccessMixin, CreateView):
    """
    View to create a new space
    """
    model = Space
    template_name = 'core/space_create.html'
    form_class = SpaceCreateForm
    success_url = reverse_lazy('core:space_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        from django.contrib import messages
        messages.success(self.request, f'Space {self.object.name} created successfully.')
        return response
    
    
class SpaceListView(CentralAdminOnlyAccessMixin, ListView):
    """
    View to list all spaces
    """
    model = Space
    template_name = 'core/space_list.html'
    context_object_name = 'spaces'

    def get_queryset(self):
        return Space.objects.select_related('org').prefetch_related('users').order_by('name')


class SpaceDetailView(CentralAdminOnlyAccessMixin, DetailView):
    """
    View to display space details with related issues and users
    """
    model = Space
    template_name = 'core/space_detail.html'
    context_object_name = 'space'
    slug_field = 'slug'
    slug_url_kwarg = 'space_slug'

    def get_queryset(self):
        return Space.objects.select_related('org').prefetch_related(
            'users',
            'issues__reporter',
            'issues__images'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get related issues for this space
        issues = self.object.issues.select_related('reporter').prefetch_related('images').order_by('-created_at')
        context['issues'] = issues
        context['issues_count'] = issues.count()
        
        # Get users associated with this space
        users = self.object.users.all().order_by('first_name', 'last_name')
        context['users'] = users
        context['users_count'] = users.count()
        
        # Add user addition form
        context['user_add_form'] = SpaceUserAddForm(space=self.object)
        
        # Get issue statistics
        context['open_issues_count'] = issues.filter(status='open').count()
        context['resolved_issues_count'] = issues.filter(status='resolved').count()
        context['in_progress_issues_count'] = issues.filter(status='in_progress').count()
        
        return context


class SpaceUserAddView(CentralAdminOnlyAccessMixin, FormView):
    """
    View to handle adding users to a space
    """
    form_class = SpaceUserAddForm
    template_name = 'core/space_detail.html'  # Will handle form in the same template

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Get space instance for the form
        self.space = get_object_or_404(Space, slug=self.kwargs['space_slug'])
        kwargs['space'] = self.space
        return kwargs
    
    def form_valid(self, form):
        # Add selected users to space
        users = form.cleaned_data['users']
        self.space.users.add(*users)
        
        # Add success message
        messages.success(self.request, f"Successfully added {len(users)} user(s) to {self.space.name}")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Error adding users to space. Please try again.")
        return redirect('core:space_detail', space_slug=self.kwargs['space_slug'])
    
    def get_success_url(self):
        return reverse_lazy('core:space_detail', kwargs={'space_slug': self.kwargs['space_slug']})


class SpaceUpdateView(CentralAdminOnlyAccessMixin, UpdateView):
    """
    View to update an existing space
    """
    model = Space
    template_name = 'core/space_update.html'
    form_class = SpaceUpdateForm
    slug_field = 'slug'
    slug_url_kwarg = 'space_slug'

    def get_queryset(self):
        return Space.objects.select_related('org')

    def get_success_url(self):
        return reverse_lazy('core:space_detail', kwargs={'space_slug': self.object.slug})

    def form_valid(self, form):
        response = super().form_valid(form)
        from django.contrib import messages
        messages.success(self.request, f'Space "{self.object.name}" updated successfully.')
        return response


class SpaceDeleteView(CentralAdminOnlyAccessMixin, DeleteView):
    """
    View to delete a space and all its related data
    """
    model = Space
    template_name = 'core/space_delete.html'
    slug_field = 'slug'
    slug_url_kwarg = 'space_slug'
    success_url = reverse_lazy('core:space_list')

    def get_queryset(self):
        return Space.objects.select_related('org').prefetch_related(
            'users', 
            'issues__images', 
            'issues__comments', 
            'issues__work_tasks__shares'
        )

    def delete(self, request, *args, **kwargs):
        """Override delete to add success message and handle related objects"""
        self.object = self.get_object()
        space_name = self.object.name
        
        # Clear active_space for all users who have this space selected
        User.objects.filter(active_space=self.object).update(active_space=None)
        
        # Django's CASCADE will automatically delete:
        # - Issues (related via space)
        # - IssueImage instances (related via issues)
        # - IssueComment instances (related via issues)
        # - WorkTask instances (related via issues)
        # - WorkTaskShare instances (related via work_tasks)
        
        success_url = self.get_success_url()
        self.object.delete()
        
        messages.success(request, f'Space "{space_name}" and all its related data have been permanently deleted.')
        
        return redirect(success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add counts of related objects that will be deleted
        from issue_management.models import WorkTask
        
        issues = self.object.issues.all()
        all_work_tasks = WorkTask.objects.filter(issue__in=issues)
        
        context['related_counts'] = {
            'users': self.object.users.count(),
            'issues': issues.count(),
            'images': sum(issue.images.count() for issue in issues),
            'comments': sum(issue.comments.count() for issue in issues),
            'work_tasks': all_work_tasks.count(),
            'work_task_shares': sum(task.shares.count() for task in all_work_tasks),
        }
        return context


class SpaceUserRemoveView(CentralAdminOnlyAccessMixin, FormView):
    """
    View to handle removing users from a space
    """
    form_class = SpaceUserRemoveForm
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Get space instance for the form
        self.space = get_object_or_404(Space, slug=self.kwargs['space_slug'])
        kwargs['space'] = self.space
        return kwargs
    
    def form_valid(self, form):
        # Remove the user from space
        user = form.cleaned_data['user_id']
        self.space.users.remove(user)

        # If the user had this space selected as active, clear it so they must pick again
        if user.active_space_id == self.space.id:
            user.active_space = None
            user.save(update_fields=['active_space'], skip_validation=True)
        
        # Add success message
        messages.success(self.request, f"Successfully removed {user.get_full_name() or user.get_short_name()} from {self.space.name}")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Error removing user from space. Please try again.")
        return redirect('core:space_detail', space_slug=self.kwargs['space_slug'])
    
    def get_success_url(self):
        return reverse_lazy('core:space_detail', kwargs={'space_slug': self.kwargs['space_slug']})


class RegeneratePasswordView(CentralAdminOnlyAccessMixin, View):
    """
    View to regenerate password for users with email authentication
    Sends a new password reset email to the user
    """
    
    def post(self, request, *args, **kwargs):
        """
        Handle POST request to regenerate password for a specific user
        """
        try:
            user_id = request.POST.get('user_id')
            if not user_id:
                return JsonResponse({
                    'success': False, 
                    'message': 'User ID is required'
                }, status=400)
            
            # Get the user
            user = get_object_or_404(User, id=user_id)
            
            # Only allow password regeneration for email authentication users
            if user.auth_method != 'email':
                return JsonResponse({
                    'success': False, 
                    'message': 'Password regeneration is only available for users with email authentication'
                }, status=400)
            
            # Don't allow regeneration for general users
            if user.user_type == 'general_user':
                return JsonResponse({
                    'success': False, 
                    'message': 'General users use phone authentication and do not have passwords'
                }, status=400)
            
            # Send password reset email
            self._send_password_reset_email(user, request)
            
            messages.success(
                request, 
                f'Password reset email sent to {user.email}. '
                f'{user.get_full_name()} should check their email to set a new password.'
            )
            
            return JsonResponse({
                'success': True, 
                'message': f'Password reset email sent to {user.email}'
            })
            
        except User.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'message': 'User not found'
            }, status=404)
        except Exception as e:
            messages.error(request, f'Error sending password reset email: {str(e)}')
            return JsonResponse({
                'success': False, 
                'message': f'Error sending password reset email: {str(e)}'
            }, status=500)

    def _send_password_reset_email(self, user, request):
        """
        Send password reset email to the user
        """
        current_site = get_current_site(request)
        site_name = current_site.name
        domain = current_site.domain
        
        # Generate password reset token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Create password reset URL
        password_reset_url = request.build_absolute_uri(
            reverse_lazy('core:password_reset_confirm', kwargs={
                'uidb64': uid,
                'token': token,
            })
        )
        
        # Email context
        context = {
            'user': user,
            'site_name': site_name,
            'domain': domain,
            'password_reset_url': password_reset_url,
            'protocol': 'https' if request.is_secure() else 'http',
        }
        
        # Render email subject and body
        subject = f'{site_name} - Password Reset Request'
        
        # Simple text email
        message = f"""
Hi {user.get_full_name()},

A password reset has been requested for your account:

Account Details:
- Name: {user.get_full_name()}
- Email: {user.email}
- Role: {user.get_user_type_display()}

Please click the link below to set your new password:
{password_reset_url}

This link will expire in 24 hours for security reasons.

If you did not request this password reset, please ignore this email.

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


class GeneratePasswordView(CentralAdminOnlyAccessMixin, View):
    """
    View to generate a new password for users with email authentication
    Returns the generated password for manual sharing
    """
    
    def post(self, request, *args, **kwargs):
        """
        Handle POST request to generate a new password for a specific user
        """
        try:
            user_id = request.POST.get('user_id')
            if not user_id:
                return JsonResponse({
                    'success': False, 
                    'message': 'User ID is required'
                }, status=400)
            
            # Get the user
            user = get_object_or_404(User, id=user_id)
            
            # Only allow password generation for email authentication users
            if user.auth_method != 'email':
                return JsonResponse({
                    'success': False, 
                    'message': 'Password generation is only available for users with email authentication'
                }, status=400)
            
            # Don't allow generation for general users
            if user.user_type == 'general_user':
                return JsonResponse({
                    'success': False, 
                    'message': 'General users use phone authentication and do not have passwords'
                }, status=400)
            
            # Generate a secure password
            password = self._generate_secure_password()
            
            # Set the new password for the user
            user.set_password(password)
            user.save()
            
            messages.success(
                request, 
                f'New password generated for {user.get_full_name()}. '
                f'The password has been set and is ready to use.'
            )
            
            return JsonResponse({
                'success': True, 
                'password': password,
                'message': f'New password generated for {user.get_full_name()}'
            })
            
        except User.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'message': 'User not found'
            }, status=404)
        except Exception as e:
            messages.error(request, f'Error generating password: {str(e)}')
            return JsonResponse({
                'success': False, 
                'message': f'Error generating password: {str(e)}'
            }, status=500)

    def _generate_secure_password(self, length=12):
        """
        Generate a secure random password
        """
        # Define character sets
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special_chars = "!@#$%^&*"
        
        # Ensure at least one character from each set
        password = [
            secrets.choice(uppercase),      # At least one uppercase
            secrets.choice(lowercase),      # At least one lowercase
            secrets.choice(digits),         # At least one digit
            secrets.choice(special_chars)   # At least one special character
        ]
        
        # Fill the rest with random characters from all sets
        all_chars = lowercase + uppercase + digits + special_chars
        for _ in range(length - 4):
            password.append(secrets.choice(all_chars))
        
        # Shuffle the password list to avoid predictable patterns
        secrets.SystemRandom().shuffle(password)
        
        return ''.join(password)


class DeleteUserView(CentralAdminOnlyAccessMixin, View):
    """
    View to delete a user with proper validation and safety checks
    """
    
    def post(self, request, *args, **kwargs):
        """
        Handle POST request to delete a specific user
        """
        try:
            user_id = request.POST.get('user_id')
            confirm_text = request.POST.get('confirm_text', '').strip()
            
            if not user_id:
                return JsonResponse({
                    'success': False, 
                    'message': 'User ID is required'
                }, status=400)
            
            # Get the user
            user = get_object_or_404(User, id=user_id)
            
            # Safety checks - prevent deletion of important users
            if user.is_superuser:
                return JsonResponse({
                    'success': False, 
                    'message': 'Cannot delete superuser accounts'
                }, status=400)
            
            # Prevent self-deletion if implemented in the future
            if hasattr(request, 'user') and request.user.id == user.id:
                return JsonResponse({
                    'success': False, 
                    'message': 'You cannot delete your own account'
                }, status=400)
            
            # Require confirmation text to match user's name or email
            expected_confirmation = user.get_full_name() or user.email or user.phone_number or f"User {user.id}"
            if confirm_text.lower() != expected_confirmation.lower():
                return JsonResponse({
                    'success': False, 
                    'message': f'Confirmation text must match exactly: "{expected_confirmation}"'
                }, status=400)
            
            # Check for related data that might prevent deletion
            related_issues_count = 0
            related_comments_count = 0
            
            # Check if user has reported issues
            if hasattr(user, 'reported_issues'):
                related_issues_count = user.reported_issues.count()
            
            # Check if user has comments (if comment model exists)
            if hasattr(user, 'comments'):
                related_comments_count = user.comments.count()
            
            # Store user info for success message before deletion
            user_name = user.get_full_name() or user.email or user.phone_number
            user_email = user.email
            user_org = user.organization.name if user.organization else "No organization"
            
            # Perform the deletion
            user.delete()
            
            messages.success(
                request, 
                f'User "{user_name}" has been successfully deleted. '
                f'Organization: {user_org}. '
                f'Related data: {related_issues_count} issues, {related_comments_count} comments were also removed.'
            )
            
            return JsonResponse({
                'success': True, 
                'message': f'User "{user_name}" has been successfully deleted.',
                'redirect': True  # Signal to reload the page
            })
            
        except User.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'message': 'User not found'
            }, status=404)
        except Exception as e:
            messages.error(request, f'Error deleting user: {str(e)}')
            return JsonResponse({
                'success': False, 
                'message': f'Error deleting user: {str(e)}'
            }, status=500)


class SpaceSwitcherView(FormView):
    """
    View for space admins to switch their active space context
    """
    form_class = SpaceSwitcherForm
    template_name = 'core/space_switcher.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Only allow space admins to access this view
        if not request.user.is_authenticated or not request.user.is_space_admin:
            messages.error(request, "Only space admins can switch spaces.")
            return redirect('core:login')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def post(self, request, *args, **kwargs):
        """
        Handle POST request for space switching
        """
        space_slug = request.POST.get('space')
        if space_slug:
            try:
                # Get the space by slug
                space = Space.objects.get(slug=space_slug)
                
                # Verify user can access this space
                if request.user.can_access_space(space):
                    # Set as active space
                    if request.user.set_active_space(space):
                        messages.success(
                            request,
                            f'Successfully switched to space: {space.name}. Welcome to your workspace!'
                        )
                        # Redirect to space admin dashboard
                        return redirect('dashboard:space_admin_dashboard')
                    else:
                        messages.error(request, 'Failed to switch space due to access restrictions.')
                else:
                    messages.error(request, 'You do not have access to that space.')
            except Space.DoesNotExist:
                messages.error(request, 'The selected space could not be found.')
        else:
            messages.error(request, 'Please select a space.')
        
        # If we get here, something went wrong, show form again
        return self.get(request, *args, **kwargs)

    def form_valid(self, form):
        """
        Handle form-based space switching (fallback for dropdown)
        """
        if form.save():
            space = form.cleaned_data['space']
            messages.success(
                self.request, 
                f'Successfully switched to space: {space.name}'
            )
            # Redirect to space admin dashboard
            return redirect('dashboard:space_admin_dashboard')
        else:
            messages.error(self.request, 'Failed to switch space.')
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_space'] = self.request.user.active_space
        context['available_spaces'] = self.request.user.get_available_spaces()
        return context
