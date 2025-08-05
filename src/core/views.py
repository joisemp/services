from django.shortcuts import render, redirect
from django.db import transaction
from django.contrib import messages
from .models import User, UserProfile, Organisation
from .forms import AccountCreationForm, OrganisationCreationForm, UserLoginForm, GeneralUserLoginForm
from django.contrib.auth import authenticate, login
from django.urls import reverse
from django.contrib.auth import views as auth_views
from django.views.decorators.cache import never_cache


class CustomPasswordResetView(auth_views.PasswordResetView):
    template_name = 'core/password_reset_form.html'
    email_template_name = 'core/password_reset_email.html'
    subject_template_name = 'core/password_reset_subject.txt'
    success_url = '/core/password-reset/done/'


class CustomPasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = 'core/password_reset_done.html'


class CustomPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = 'core/password_reset_confirm.html'
    success_url = '/core/password-reset/complete/'


class CustomPasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = 'core/password_reset_complete.html'


def account_creation_view(request):
    if request.method == 'POST':
        form = AccountCreationForm(request.POST)
        if form.is_valid():
            request.session['account_data'] = form.cleaned_data
            return redirect('core:organisation_creation')
    else:
        form = AccountCreationForm()
    return render(request, 'core/account_creation.html', {'form': form})


def organisation_creation_view(request):
    account_data = request.session.get('account_data')
    if not account_data:
        return redirect('core:account_creation')
    if request.method == 'POST':
        form = OrganisationCreationForm(request.POST)
        if form.is_valid():
            org_data = form.cleaned_data
            try:
                with transaction.atomic():
                    org = Organisation.objects.create(
                        name=org_data['name'],
                        address=org_data['address']
                    )
                    user = User.objects.create_user(
                        email=account_data['email'],
                        phone=account_data['phone'],
                        password=account_data['password']
                    )
                    profile = UserProfile.objects.create(
                        user=user,
                        first_name=account_data['first_name'],
                        last_name=account_data['last_name'],
                        user_type='central_admin',
                        org=org
                    )
                    org.central_admins.add(user)
                messages.success(request, 'Account and organisation created successfully!')
                request.session.pop('account_data', None)
                return redirect('core:account_creation_success')
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
    else:
        form = OrganisationCreationForm()
    return render(request, 'core/organisation_creation.html', {'form': form})


def account_creation_success(request):
    return render(request, 'core/account_creation_success.html')


def user_login_view(request):
    form = UserLoginForm(request.POST or None)
    error = None
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data.get('email')
        password = form.cleaned_data.get('password')
        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)
            return redirect(f"{reverse('dashboard:dashboard')}?user={user.profile.slug}")
        else:
            error = 'Invalid credentials.'
    return render(request, 'core/user_login.html', {'form': form, 'error': error})


def general_user_login_view(request):
    form = GeneralUserLoginForm(request.POST or None)
    error = None
    if request.method == 'POST' and form.is_valid():
        phone = form.cleaned_data.get('phone')
        try:
            user = User.objects.get(phone=phone, profile__user_type='general_user')
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect(f"{reverse('dashboard:dashboard')}?user={user.profile.slug}")
        except User.DoesNotExist:
            error = 'No general user found with this phone number.'
    return render(request, 'core/general_user_login.html', {'form': form, 'error': error})


@never_cache
def landing_view(request):
    """
    Landing page view that redirects authenticated users to their dashboard
    and shows the landing page for anonymous users.
    """
    # If user is authenticated, redirect to dashboard
    if request.user.is_authenticated:
        # Check if user has a profile
        if hasattr(request.user, 'profile'):
            return redirect('dashboard:dashboard')
        else:
            # If user doesn't have a profile, they might need to complete setup
            # For now, redirect to dashboard which will handle the error appropriately
            return redirect('dashboard:dashboard')
    
    # If user is not authenticated, show the landing page
    return render(request, 'landing.html')
