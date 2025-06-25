from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from .forms import AddGeneralUserForm, AddOtherUserForm
from .edit_forms import EditUserForm
import secrets
from django.core.mail import send_mail
from django.db import transaction
from django.contrib import messages

from core.forms import AccountCreationForm
from core.models import Organisation, UserProfile, User
from .models import WorkCategory
from config.helpers import is_central_admin

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

@login_required
@user_passes_test(is_central_admin)
def edit_person(request, profile_id):
    profile = get_object_or_404(UserProfile, pk=profile_id)
    orgs = Organisation.objects.filter(central_admins=request.user)
    if not orgs.exists() or profile.org not in orgs:
        return redirect('service_management:people_list')
    if request.method == 'POST':
        form = EditUserForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('service_management:people_list')
    else:
        form = EditUserForm(instance=profile)
    return render(request, 'service_management/edit_person.html', {'form': form, 'profile': profile})

@login_required
@user_passes_test(is_central_admin)
def delete_person(request, profile_id):
    profile = get_object_or_404(UserProfile, pk=profile_id)
    orgs = Organisation.objects.filter(central_admins=request.user)
    if not orgs.exists() or profile.org not in orgs:
        messages.error(request, 'You do not have permission to delete this user.')
        return redirect('service_management:people_list')
    if request.method == 'POST':
        user_email = profile.user.email
        profile.delete()  # This will also delete the user due to signal
        messages.success(request, f'User {user_email} deleted successfully.')
        return redirect('service_management:people_list')
    return render(request, 'service_management/delete_person_confirm.html', {'profile': profile})

@login_required
@user_passes_test(is_central_admin)
def work_category_list(request):
    org = getattr(request.user.profile, 'org', None)
    categories = WorkCategory.objects.filter(org=org).order_by('name') if org else WorkCategory.objects.none()
    return render(request, 'service_management/work_category_list.html', {'categories': categories})

# Create your views here.
