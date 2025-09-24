from django.shortcuts import render, redirect
from django.contrib.auth import views as auth_views, authenticate, login, logout
from django.urls import reverse_lazy
from django.views.generic import FormView
from .forms import (
    CustomPasswordResetForm, 
    CustomSetPasswordForm, 
    GeneralUserCreateForm, 
    OtherRoleUserCreateForm,
    PhoneLoginForm,
    EmailLoginForm,
    SpaceCreateForm,
    SpaceUpdateForm
)
from .models import Update, User, Space
from django.views.generic import ListView, CreateView, TemplateView, DetailView, UpdateView


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
    

class PeopleListView(ListView):
    """
    View to list all users in the system
    """
    model = User
    template_name = 'core/people_list.html'
    context_object_name = 'users'

    def get_queryset(self):
        return User.objects.select_related('organization').prefetch_related('spaces').order_by('first_name', 'last_name')
    

class PeopleCreateView(CreateView):
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

    def form_valid(self, form):
        """
        Handle successful form submission
        """
        response = super().form_valid(form)
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
        return response


class CustomLoginView(FormView):
    """
    Custom login view that handles both phone and email authentication
    """
    template_name = 'core/login.html'
    success_url = reverse_lazy('core:people_list')  # Redirect after successful login

    def get_form_class(self):
        """
        Return the appropriate form class based on user_type parameter
        """
        user_type = self.request.GET.get('type', 'email')
        if user_type == 'phone':
            return PhoneLoginForm
        return EmailLoginForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_type = self.request.GET.get('type', 'email')
        context['user_type'] = user_type
        context['form_title'] = 'Phone Login' if user_type == 'phone' else 'Email Login'
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
        else:
            # Email authentication
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
            return redirect(self.success_url)
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


class UpdateListView(ListView):
    """
    View to list all updates in the system
    """
    model = Update
    template_name = 'core/updates_list.html'
    context_object_name = 'updates'

    def get_queryset(self):
        return Update.objects.all().order_by('-created_at')


class SpaceCreateView(CreateView):
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
    
    
class SpaceListView(ListView):
    """
    View to list all spaces
    """
    model = Space
    template_name = 'core/space_list.html'
    context_object_name = 'spaces'

    def get_queryset(self):
        return Space.objects.select_related('org').order_by('name')


class SpaceDetailView(DetailView):
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
        
        # Get issue statistics
        context['open_issues_count'] = issues.filter(status='open').count()
        context['resolved_issues_count'] = issues.filter(status='resolved').count()
        context['in_progress_issues_count'] = issues.filter(status='in_progress').count()
        
        return context


class SpaceUpdateView(UpdateView):
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
