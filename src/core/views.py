from django.shortcuts import render, redirect
from django.db import transaction
from django.contrib import messages
from .models import User, UserProfile, Organisation
from .forms import AccountCreationForm, OrganisationCreationForm


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
