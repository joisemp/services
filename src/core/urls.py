from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from .forms import CustomPasswordResetForm, CustomSetPasswordForm
from . import views

app_name = "core"

urlpatterns = [
    # Password Reset URLs with custom forms
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='registration/password_reset_form.html',
             form_class=CustomPasswordResetForm,
             email_template_name='emails/password_reset_email.txt',
             html_email_template_name='emails/password_reset_email.html',
             subject_template_name='emails/password_reset_subject.txt',
             success_url=reverse_lazy('core:password_reset_done')
         ), 
         name='password_reset'),
    
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='registration/password_reset_done.html'
         ), 
         name='password_reset_done'),
    
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='registration/password_reset_confirm.html',
             form_class=CustomSetPasswordForm,
             success_url=reverse_lazy('core:password_reset_complete')
         ), 
         name='password_reset_confirm'),
    
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='registration/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
]