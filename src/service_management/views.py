from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from .forms import (AddGeneralUserForm, AddOtherUserForm, WorkCategoryForm, SpaceForm)
from .edit_forms import EditUserForm
import secrets
from django.core.mail import send_mail
from django.db import transaction
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponseForbidden, JsonResponse
from django.utils import timezone
from decimal import Decimal

from core.forms import AccountCreationForm
from core.models import Organisation, UserProfile, User
from .models import WorkCategory, Spaces, SpaceSettings
from config.helpers import is_central_admin, is_space_admin

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
    org = orgs.first()
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
                        org=org,
                        first_name=form.cleaned_data.get('first_name', ''),
                        last_name=form.cleaned_data.get('last_name', ''),
                        user_type='general_user'
                    )
                # Optionally notify user by SMS here
                return redirect('service_management:people_list')
        else:
            form = AddOtherUserForm(request.POST, org=org)
            if form.is_valid():
                with transaction.atomic():
                    password = secrets.token_urlsafe(8)
                    user = User.objects.create_user(
                        email=form.cleaned_data['email'],
                        phone=form.cleaned_data['phone'],
                        password=password
                    )
                    profile = UserProfile.objects.create(
                        user=user,
                        org=org,
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        user_type=form.cleaned_data['user_type']
                    )
                    # Assign skills if maintainer
                    if form.cleaned_data['user_type'] == 'maintainer':
                        selected_skills = list(form.cleaned_data['skills'])
                        general_skill = WorkCategory.objects.filter(org=org, name__iexact='general').first()
                        if general_skill and general_skill not in selected_skills:
                            selected_skills.append(general_skill)
                        profile.skills.set(selected_skills)
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
            form = AddOtherUserForm(org=org)
    return render(request, 'service_management/add_person.html', {'form': form, 'mode': mode})

@login_required
@user_passes_test(is_central_admin)
def edit_person(request, profile_id):
    profile = get_object_or_404(UserProfile, pk=profile_id)
    orgs = Organisation.objects.filter(central_admins=request.user)
    if not orgs.exists() or profile.org not in orgs:
        return redirect('service_management:people_list')
    org = orgs.first()
    if request.method == 'POST':
        form = EditUserForm(request.POST, instance=profile)
        if form.is_valid():
            profile = form.save()
            # If maintainer, verify/confirm skills
            if profile.user_type == 'maintainer':
                selected_skills = request.POST.getlist('skills')
                general_skill = WorkCategory.objects.filter(org=org, name__iexact='general').first()
                if general_skill and str(general_skill.pk) not in selected_skills:
                    selected_skills.append(str(general_skill.pk))
                profile.skills.set(selected_skills)
            return redirect('service_management:people_list')
    else:
        form = EditUserForm(instance=profile)
    # If maintainer, show skills for confirmation
    skills_field = None
    if profile.user_type == 'maintainer':
        all_skills = WorkCategory.objects.filter(org=org)
        current_skills = profile.skills.values_list('pk', flat=True)
        skills_field = {'all_skills': all_skills, 'current_skills': current_skills}
    return render(request, 'service_management/edit_person.html', {'form': form, 'profile': profile, 'skills_field': skills_field})

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

@login_required
@user_passes_test(is_central_admin)
def create_work_category(request):
    org = getattr(request.user.profile, 'org', None)
    if not org:
        return redirect('service_management:work_category_list')
    if request.method == 'POST':
        form = WorkCategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.org = org
            category.save()
            return redirect('service_management:work_category_list')
    else:
        form = WorkCategoryForm()
    return render(request, 'service_management/create_work_category.html', {'form': form})

@login_required
@user_passes_test(is_central_admin)
def update_work_category(request, category_slug):
    org = getattr(request.user.profile, 'org', None)
    category = get_object_or_404(WorkCategory, slug=category_slug, org=org)
    if request.method == 'POST':
        form = WorkCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect('service_management:work_category_list')
    else:
        form = WorkCategoryForm(instance=category)
    return render(request, 'service_management/update_work_category.html', {'form': form, 'category': category})

@login_required
@user_passes_test(is_central_admin)
def delete_work_category(request, category_slug):
    org = getattr(request.user.profile, 'org', None)
    category = get_object_or_404(WorkCategory, slug=category_slug, org=org)
    if request.method == 'POST':
        category.delete()
        return redirect('service_management:work_category_list')
    return render(request, 'service_management/delete_work_category_confirm.html', {'category': category})

@login_required
@user_passes_test(is_central_admin)
def spaces_list(request):
    """List all spaces for central admin"""
    # Get the organisation(s) managed by this central admin
    orgs = Organisation.objects.filter(central_admins=request.user)
    # Get all spaces in these organisations
    spaces = Spaces.objects.filter(org__in=orgs).select_related('org').prefetch_related('space_admins')
    
    # Initialize space context variables
    selected_space = None
    space_settings = None
    user_spaces = None
    
    # Handle space context for different user types
    if (request.user.is_authenticated and hasattr(request.user, 'profile') and 
        request.user.profile.user_type == 'space_admin'):
        user_spaces = request.user.administered_spaces.all()
        selected_space = request.user.profile.current_active_space
        
        # If no active space is set or user can't access it, set to first available
        if not selected_space or not user_spaces.filter(id=selected_space.id).exists():
            if user_spaces.exists():
                selected_space = user_spaces.first()
                request.user.profile.switch_active_space(selected_space)
        
        if selected_space:
            space_settings = selected_space.settings
    elif (request.user.is_authenticated and hasattr(request.user, 'profile') and 
          request.user.profile.user_type == 'central_admin'):
        # For central admin, check if filtering by specific space
        space_filter = request.GET.get('space_filter')
        if space_filter and space_filter != 'no_space':
            try:
                selected_space = Spaces.objects.get(slug=space_filter, org__in=orgs)
            except Spaces.DoesNotExist:
                pass
    
    # Add search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        spaces = spaces.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(spaces, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'spaces': page_obj,
        'search_query': search_query,
        'orgs': orgs,
        # Add space context
        'selected_space': selected_space,
        'space_settings': space_settings,
        'user_spaces': user_spaces,
    }
    return render(request, 'service_management/spaces_list.html', context)


@login_required
def space_detail(request, slug):
    """View details of a specific space"""
    space = get_object_or_404(Spaces, slug=slug)
    
    # Check permissions: central admin of the org OR space admin of this space
    user_is_central_admin = is_central_admin(request.user) and space.org.central_admins.filter(id=request.user.id).exists()
    user_is_space_admin = is_space_admin(request.user) and space.space_admins.filter(id=request.user.id).exists()
    
    if not (user_is_central_admin or user_is_space_admin):
        return HttpResponseForbidden('You do not have permission to view this space.')
    
    # Initialize space context variables
    selected_space = None
    space_settings = None
    user_spaces = None
    
    # Handle space context for different user types
    if (request.user.is_authenticated and hasattr(request.user, 'profile') and 
        request.user.profile.user_type == 'space_admin'):
        user_spaces = request.user.administered_spaces.all()
        selected_space = request.user.profile.current_active_space
        
        # If no active space is set or user can't access it, set to first available
        if not selected_space or not user_spaces.filter(id=selected_space.id).exists():
            if user_spaces.exists():
                selected_space = user_spaces.first()
                request.user.profile.switch_active_space(selected_space)
        
        if selected_space:
            space_settings = selected_space.settings
    elif (request.user.is_authenticated and hasattr(request.user, 'profile') and 
          request.user.profile.user_type == 'central_admin'):
        # For central admin, check if filtering by specific space
        space_filter = request.GET.get('space_filter')
        if space_filter and space_filter != 'no_space':
            try:
                selected_space = Spaces.objects.get(slug=space_filter, org=space.org)
            except Spaces.DoesNotExist:
                pass
    
    context = {
        'space': space,
        'settings': space.settings,
        'admin_count': space.get_admin_count(),
        'user_is_central_admin': user_is_central_admin,
        'user_is_space_admin': user_is_space_admin,
        # Add space context
        'selected_space': selected_space,
        'space_settings': space_settings,
        'user_spaces': user_spaces,
    }
    return render(request, 'service_management/space_detail.html', context)


@login_required
@user_passes_test(is_central_admin)
def create_space(request):
    """Create a new space"""
    # Get the user's organization automatically
    user_org = request.user.profile.org
    
    if not user_org:
        messages.error(request, 'You must be associated with an organization to create spaces.')
        return redirect('service_management:spaces_list')
    
    if request.method == 'POST':
        form = SpaceForm(request.POST, user_org=user_org)
        if form.is_valid():
            try:
                space = form.save(commit=False)
                space.created_by = request.user
                space.save()
                messages.success(request, f'Space "{space.name}" created successfully!')
                return redirect('service_management:space_detail', slug=space.slug)
            except Exception as e:
                messages.error(request, f'Error creating space: {str(e)}')
    else:
        form = SpaceForm(user_org=user_org)
    
    context = {
        'form': form,
        'user_org': user_org,  # Pass user's organization for display
    }
    return render(request, 'service_management/create_space.html', context)


@login_required
def edit_space(request, slug):
    """Edit an existing space"""
    space = get_object_or_404(Spaces, slug=slug)
    
    # Check permissions: central admin of the org OR space admin of this space
    user_is_central_admin = is_central_admin(request.user) and space.org.central_admins.filter(id=request.user.id).exists()
    user_is_space_admin = is_space_admin(request.user) and space.space_admins.filter(id=request.user.id).exists()
    
    if not (user_is_central_admin or user_is_space_admin):
        return HttpResponseForbidden('You do not have permission to edit this space.')
    
    if request.method == 'POST':
        form = SpaceForm(request.POST, instance=space, user_org=space.org)
        if form.is_valid():
            try:
                # Handle additional fields not in the form
                space.is_access_enabled = request.POST.get('is_access_enabled') == 'on'
                space.require_approval = request.POST.get('require_approval') == 'on'
                
                # Save the form data
                form.save()
                space.save()  # Save the additional fields
                
                messages.success(request, f'Space "{space.name}" updated successfully!')
                return redirect('service_management:space_detail', slug=space.slug)
            except Exception as e:
                messages.error(request, f'Error updating space: {str(e)}')
    else:
        form = SpaceForm(instance=space, user_org=space.org)
    
    context = {
        'form': form,
        'space': space,
        'user_is_central_admin': user_is_central_admin,
        'user_is_space_admin': user_is_space_admin,
    }
    return render(request, 'service_management/edit_space.html', context)


@login_required
def space_settings(request, slug):
    """Manage space settings"""
    space = get_object_or_404(Spaces, slug=slug)
    
    # Check permissions: central admin of the org OR space admin of this space
    user_is_central_admin = is_central_admin(request.user) and space.org.central_admins.filter(id=request.user.id).exists()
    user_is_space_admin = is_space_admin(request.user) and space.space_admins.filter(id=request.user.id).exists()
    
    if not (user_is_central_admin or user_is_space_admin):
        return HttpResponseForbidden('You do not have permission to manage settings for this space.')
    
    settings = space.settings
    
    # Initialize space context variables (for UI consistency, but no switching allowed)
    selected_space = space  # Always the current space being configured
    space_settings = settings  # Settings for the current space
    user_spaces = None
    
    # For space admins, get their spaces for context (but don't allow switching)
    if (request.user.is_authenticated and hasattr(request.user, 'profile') and 
        request.user.profile.user_type == 'space_admin'):
        user_spaces = request.user.administered_spaces.all()
    
    if request.method == 'POST':
        # Update module access settings
        settings.enable_issue_management = request.POST.get('enable_issue_management') == 'on'
        settings.enable_service_management = request.POST.get('enable_service_management') == 'on'
        settings.enable_transportation = request.POST.get('enable_transportation') == 'on'
        settings.enable_finance = request.POST.get('enable_finance') == 'on'
        settings.enable_marketplace = request.POST.get('enable_marketplace') == 'on'
        settings.enable_asset_management = request.POST.get('enable_asset_management') == 'on'
        settings.updated_by = request.user
        settings.save()
        
        messages.success(request, f'Settings for "{space.name}" updated successfully!')
        
        # Redirect based on user type  
        if user_is_space_admin:
            # Update the user's active space and redirect to dashboard
            request.user.profile.switch_active_space(space)
            return redirect('dashboard:dashboard')
        else:
            return redirect('service_management:space_detail', slug=space.slug)
    
    context = {
        'space': space,
        'settings': settings,
        'user_is_central_admin': user_is_central_admin,
        'user_is_space_admin': user_is_space_admin,
        # Add space context (but disable switching for this specific view)
        'selected_space': selected_space,
        'space_settings': space_settings,
        'user_spaces': user_spaces,
        'disable_space_switching': True,  # Flag to disable space switcher in this view
    }
    return render(request, 'service_management/space_settings.html', context)


@login_required
@user_passes_test(is_central_admin)
def manage_space_admins(request, slug):
    """Manage space administrators"""
    orgs = Organisation.objects.filter(central_admins=request.user)
    space = get_object_or_404(Spaces, slug=slug, org__in=orgs)
    
    # Get potential space admins (users with space_admin user_type in the same org)
    potential_admins = User.objects.filter(
        profile__user_type='space_admin',
        profile__org=space.org
    ).exclude(administered_spaces=space)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')
        
        try:
            user = User.objects.get(id=user_id, profile__org=space.org)
            
            if action == 'add':
                space.space_admins.add(user)
                messages.success(request, f'Added {user.profile.first_name} {user.profile.last_name} as space admin.')
            elif action == 'remove':
                space.space_admins.remove(user)
                messages.success(request, f'Removed {user.profile.first_name} {user.profile.last_name} from space admins.')
                
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
        
        return redirect('service_management:manage_space_admins', slug=space.slug)
    
    context = {
        'space': space,
        'current_admins': space.space_admins.all(),
        'potential_admins': potential_admins,
    }
    return render(request, 'service_management/manage_space_admins.html', context)


@login_required
def no_spaces_assigned(request):
    """View for space admins who have no assigned spaces"""
    # Only space admins should see this page
    if not request.user.is_authenticated or not is_space_admin(request.user):
        # Redirect non-space admins to the landing page instead of dashboard
        return redirect('landing')  # This should be a safe fallback
    
    # Get the user's organization for contact info
    user_org = request.user.profile.org if hasattr(request.user, 'profile') else None
    
    context = {
        'user_org': user_org,
    }
    return render(request, 'service_management/no_spaces_assigned.html', context)

