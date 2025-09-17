from django.shortcuts import render
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from .forms import (
    CustomPasswordResetForm, 
    CustomSetPasswordForm, 
    GeneralUserCreateForm, 
    OtherRoleUserCreateForm
)
from .models import User
from django.views.generic import ListView, CreateView


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
        return User.objects.all().order_by('first_name', 'last_name')
    

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