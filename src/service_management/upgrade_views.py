from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.core.mail import send_mail
from django.db import transaction
from core.models import UserProfile, User
from .upgrade_forms import UserTypeSelectForm, UserEmailUpdateForm
import threading
from config.helpers import is_central_admin

@login_required
@user_passes_test(is_central_admin)
def upgrade_user(request, profile_id):
    profile = get_object_or_404(UserProfile, pk=profile_id)
    user = profile.user
    step = request.GET.get('step', 'type')
    if step == 'type':
        if request.method == 'POST':
            form = UserTypeSelectForm(request.POST)
            if form.is_valid():
                new_type = form.cleaned_data['user_type']
                request.session['upgrade_user_type'] = new_type
                return redirect(request.path + f'?step=email')
        else:
            form = UserTypeSelectForm(initial={'user_type': profile.user_type})
        return render(request, 'service_management/upgrade_user_type.html', {'form': form, 'profile': profile})
    elif step == 'email':
        if request.method == 'POST':
            form = UserEmailUpdateForm(request.POST)
            if form.is_valid():
                email = form.cleaned_data['email']
                if User.objects.filter(email=email).exclude(pk=user.pk).exists():
                    form.add_error('email', 'This email is already in use.')
                    return render(request, 'service_management/upgrade_user_email.html', {'form': form, 'profile': profile})
                else:
                    request.session['upgrade_user_email'] = email
                    return redirect(request.path + f'?step=confirm')
        else:
            form = UserEmailUpdateForm(initial={'email': user.email})
        return render(request, 'service_management/upgrade_user_email.html', {'form': form, 'profile': profile})
    elif step == 'confirm':
        new_type = request.session.get('upgrade_user_type', profile.user_type)
        new_email = request.session.get('upgrade_user_email', user.email)
        old_type = profile.user_type
        email_error = None
        # Remove duplicate email check here, since it's now handled in the email step
        if request.method == 'POST':
            with transaction.atomic():
                profile.user_type = new_type
                if new_type != 'general_user':
                    user.email = new_email
                profile.save()
                user.save()
                if old_type == 'general_user' and new_type != 'general_user':
                    reset_url = "hello_change_this_to_your_reset_url"  # Placeholder for actual reset URL
                    threading.Thread(target=send_mail, args=(
                        'Set your password',
                        f'You have been upgraded. Set your password here: {reset_url}',
                        'noreply@example.com',
                        [user.email],
                    ), kwargs={'fail_silently': True}).start()
                else:
                    threading.Thread(target=send_mail, args=(
                        'Your account was updated',
                        'Your user type or email was updated by the admin.',
                        'noreply@example.com',
                        [user.email],
                    ), kwargs={'fail_silently': True}).start()
            # Clean up session
            request.session.pop('upgrade_user_type', None)
            request.session.pop('upgrade_user_email', None)
            return redirect('service_management:people_list')
        return render(request, 'service_management/upgrade_user_confirm.html', {
            'profile': profile,
            'new_type': new_type,
            'new_email': new_email,
            'old_type': old_type,
            'email_error': email_error,
        })
