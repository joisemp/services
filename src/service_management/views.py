from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from .forms import AddGeneralUserForm, AddOtherUserForm
import secrets
from django.core.mail import send_mail
from django.db import transaction

from core.forms import AccountCreationForm
from core.models import Organisation, UserProfile, User

# Helper to check if user is a central admin
def is_central_admin(user):
    return hasattr(user, 'profile') and user.profile.user_type == 'central_admin'

@login_required
@user_passes_test(is_central_admin)
def people_list(request):
    # Get the organisation(s) managed by this central admin
    orgs = Organisation.objects.filter(central_admins=request.user)
    # Get all people in these organisations
    people = UserProfile.objects.filter(org__in=orgs)
    return render(request, 'service_management/people_list.html', {'people': people})

@login_required
@user_passes_test(is_central_admin)
def add_person(request):
    orgs = Organisation.objects.filter(central_admins=request.user)
    if not orgs.exists():
        return redirect('service_management:people_list')
    mode = request.GET.get('mode', 'general')
    if mode not in ['general', 'other']:
        return redirect('service_management:add_person')  # fallback to default
    if request.method == 'POST':
        if request.POST.get('mode') == 'general':
            form = AddGeneralUserForm(request.POST)
            if form.is_valid():
                with transaction.atomic():
                    password = secrets.token_urlsafe(8)
                    user = User.objects.create_user(
                        phone=form.cleaned_data['phone'],
                        password=password
                    )
                    UserProfile.objects.create(
                        user=user,
                        org=orgs.first(),
                        first_name=form.cleaned_data.get('first_name', ''),
                        last_name=form.cleaned_data.get('last_name', ''),
                        user_type='general_user'
                    )
                # Optionally notify user by SMS here
                return redirect('service_management:people_list')
        else:
            form = AddOtherUserForm(request.POST)
            if form.is_valid():
                with transaction.atomic():
                    password = secrets.token_urlsafe(8)
                    user = User.objects.create_user(
                        email=form.cleaned_data['email'],
                        phone=form.cleaned_data['phone'],
                        password=password
                    )
                    UserProfile.objects.create(
                        user=user,
                        org=orgs.first(),
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        user_type=form.cleaned_data['user_type']
                    )
                    send_mail(
                        'Your Account Created',
                        f'Your password is: {password}',
                        'noreply@example.com',
                        [form.cleaned_data['email']],
                        fail_silently=True,
                    )
                return redirect('service_management:people_list')
    else:
        if mode == 'general':
            form = AddGeneralUserForm()
        else:
            form = AddOtherUserForm()
    return render(request, 'service_management/add_person.html', {'form': form, 'mode': mode})

# Create your views here.
