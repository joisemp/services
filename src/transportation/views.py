from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, Avg
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
from django.urls import reverse
from .models import (
    Vehicle, VehicleType, VehicleMake, VehicleModel, 
    VehicleDocument, MaintenanceRecord, VehicleComponent,
    VehicleComponentInstance, ComponentInspection, VehicleChangeLog
)
from .forms import (
    VehicleForm, VehicleDocumentForm, MaintenanceRecordForm,
    VehicleComponentForm, ComponentInspectionForm, VehicleModelForm,
    QuickVehicleModelForm, QuickVehicleMakeForm, QuickVehicleTypeForm
)


@login_required
def transportation_dashboard(request):
    """Dashboard view for transportation management"""
    # Get summary statistics
    total_vehicles = Vehicle.objects.count()
    active_vehicles = Vehicle.objects.filter(status='active').count()
    maintenance_due = Vehicle.objects.filter(
        next_service_due__lte=timezone.now().date()
    ).count()
    insurance_expiring = Vehicle.objects.filter(
        insurance_expiry__lte=timezone.now().date() + timezone.timedelta(days=30)
    ).count()
    
    # Recent maintenance records
    recent_maintenance = MaintenanceRecord.objects.select_related(
        'vehicle', 'performed_by'
    ).order_by('-date')[:5]
    
    # Vehicles needing attention
    vehicles_needing_attention = Vehicle.objects.filter(
        Q(next_service_due__lte=timezone.now().date()) |
        Q(insurance_expiry__lte=timezone.now().date() + timezone.timedelta(days=30)) |
        Q(registration_expiry__lte=timezone.now().date() + timezone.timedelta(days=30))
    ).select_related('vehicle_model__make')[:10]
    
    context = {
        'total_vehicles': total_vehicles,
        'active_vehicles': active_vehicles,
        'maintenance_due': maintenance_due,
        'insurance_expiring': insurance_expiring,
        'recent_maintenance': recent_maintenance,
        'vehicles_needing_attention': vehicles_needing_attention,
    }
    
    return render(request, 'transportation/dashboard.html', context)


@login_required
def vehicle_list(request):
    """List all vehicles with filtering and search"""
    vehicles = Vehicle.objects.select_related(
        'vehicle_model__make', 'owner', 'assigned_to'
    ).order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        vehicles = vehicles.filter(
            Q(license_plate__icontains=search_query) |
            Q(vin__icontains=search_query) |
            Q(vehicle_model__name__icontains=search_query) |
            Q(vehicle_model__make__name__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        vehicles = vehicles.filter(status=status_filter)
    
    # Filter by vehicle type
    type_filter = request.GET.get('type', '')
    if type_filter:
        vehicles = vehicles.filter(vehicle_model__vehicle_type__slug=type_filter)
    
    # Pagination
    paginator = Paginator(vehicles, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    vehicle_types = VehicleType.objects.all()
    status_choices = Vehicle.STATUS_CHOICES
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'vehicle_types': vehicle_types,
        'status_choices': status_choices,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'transportation/vehicle_list_partial.html', context)
    
    return render(request, 'transportation/vehicle_list.html', context)


@login_required
def vehicle_detail(request, slug):
    """Vehicle detail view"""
    vehicle = get_object_or_404(
        Vehicle.objects.select_related(
            'vehicle_model__make', 'owner', 'assigned_to'
        ), slug=slug
    )
    
    # Get related data
    documents = vehicle.documents.order_by('-created_at')
    maintenance_records = vehicle.maintenance_records.select_related(
        'performed_by'
    ).order_by('-date')[:10]
    component_instances = vehicle.component_instances.select_related(
        'component'
    ).filter(is_active=True)
    change_logs = vehicle.change_logs.select_related(
        'changed_by'
    ).order_by('-created_at')[:10]
    
    context = {
        'vehicle': vehicle,
        'documents': documents,
        'maintenance_records': maintenance_records,
        'component_instances': component_instances,
        'change_logs': change_logs,
    }
    
    return render(request, 'transportation/vehicle_detail.html', context)


@login_required
def vehicle_create(request):
    """Create new vehicle"""
    if request.method == 'POST':
        form = VehicleForm(request.POST)
        if form.is_valid():
            vehicle = form.save()
            messages.success(request, f'Vehicle {vehicle.license_plate} created successfully!')
            
            if request.headers.get('HX-Request'):
                return JsonResponse({
                    'success': True,
                    'redirect_url': vehicle.get_absolute_url()
                })
            return redirect('transportation:vehicle_detail', slug=vehicle.slug)
    else:
        form = VehicleForm()
    
    context = {'form': form}
    
    if request.headers.get('HX-Request'):
        return render(request, 'transportation/vehicle_form_partial.html', context)
    
    return render(request, 'transportation/vehicle_form.html', context)


@login_required
def vehicle_edit(request, slug):
    """Edit existing vehicle"""
    vehicle = get_object_or_404(Vehicle, slug=slug)
    
    if request.method == 'POST':
        form = VehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            vehicle = form.save()
            messages.success(request, f'Vehicle {vehicle.license_plate} updated successfully!')
            
            if request.headers.get('HX-Request'):
                return JsonResponse({
                    'success': True,
                    'redirect_url': vehicle.get_absolute_url()
                })
            return redirect('transportation:vehicle_detail', slug=vehicle.slug)
    else:
        form = VehicleForm(instance=vehicle)
    
    context = {'form': form, 'vehicle': vehicle}
    
    if request.headers.get('HX-Request'):
        return render(request, 'transportation/vehicle_form_partial.html', context)
    
    return render(request, 'transportation/vehicle_form.html', context)


@login_required
def vehicle_delete(request, slug):
    """Delete vehicle"""
    vehicle = get_object_or_404(Vehicle, slug=slug)
    
    if request.method == 'POST':
        vehicle_name = vehicle.license_plate
        vehicle.delete()
        messages.success(request, f'Vehicle {vehicle_name} deleted successfully!')
        
        if request.headers.get('HX-Request'):
            return JsonResponse({
                'success': True,
                'redirect_url': reverse('transportation:vehicle_list')
            })
        return redirect('transportation:vehicle_list')
    
    context = {'vehicle': vehicle}
    return render(request, 'transportation/vehicle_confirm_delete.html', context)


@login_required
def maintenance_list(request):
    """List maintenance records with HTMX support"""
    maintenance_records = MaintenanceRecord.objects.select_related(
        'vehicle__vehicle_model__make', 'performed_by'
    ).order_by('-date')
    
    # Get filter parameters
    vehicle_filter = request.GET.get('vehicle', '')
    type_filter = request.GET.get('type', '')
    search_query = request.GET.get('search', '')
    
    # Apply filters
    if vehicle_filter:
        maintenance_records = maintenance_records.filter(vehicle__slug=vehicle_filter)
    
    if type_filter:
        maintenance_records = maintenance_records.filter(maintenance_type=type_filter)
    
    if search_query:
        maintenance_records = maintenance_records.filter(
            Q(vehicle__license_plate__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(service_provider__icontains=search_query) |
            Q(vehicle__vehicle_model__make__name__icontains=search_query) |
            Q(vehicle__vehicle_model__name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(maintenance_records, 12)  # Show 12 records per page for better grid layout
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    vehicles = Vehicle.objects.all().order_by('license_plate')
    maintenance_types = MaintenanceRecord.MAINTENANCE_TYPES
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'vehicle_filter': vehicle_filter,
        'type_filter': type_filter,
        'vehicles': vehicles,
        'maintenance_types': maintenance_types,
    }
    
    # Return partial template for HTMX requests
    if request.headers.get('HX-Request'):
        return render(request, 'transportation/partials/maintenance_list_partial.html', context)
    
    return render(request, 'transportation/maintenance_list.html', context)


@login_required
def maintenance_detail(request, pk):
    """Display maintenance record detail"""
    maintenance = get_object_or_404(MaintenanceRecord, pk=pk)
    
    context = {
        'maintenance': maintenance,
        'vehicle': maintenance.vehicle,
    }
    
    return render(request, 'transportation/maintenance_detail.html', context)


@login_required
def maintenance_create(request, vehicle_slug=None):
    """Create maintenance record"""
    vehicle = None
    if vehicle_slug:
        vehicle = get_object_or_404(Vehicle, slug=vehicle_slug)
    
    if request.method == 'POST':
        form = MaintenanceRecordForm(request.POST)
        if form.is_valid():
            maintenance = form.save(commit=False)
            maintenance.performed_by = request.user
            maintenance.save()
            messages.success(request, 'Maintenance record created successfully!')
            
            if request.headers.get('HX-Request'):
                return JsonResponse({
                    'success': True,
                    'redirect_url': maintenance.vehicle.get_absolute_url()
                })
            return redirect('transportation:vehicle_detail', slug=maintenance.vehicle.slug)
    else:
        form = MaintenanceRecordForm(initial={'vehicle': vehicle} if vehicle else None)
    
    context = {'form': form, 'vehicle': vehicle}
    
    if request.headers.get('HX-Request'):
        return render(request, 'transportation/maintenance_form_partial.html', context)
    
    return render(request, 'transportation/maintenance_form.html', context)


@login_required
def maintenance_edit(request, pk):
    """Edit maintenance record"""
    maintenance = get_object_or_404(MaintenanceRecord, pk=pk)
    
    if request.method == 'POST':
        form = MaintenanceRecordForm(request.POST, instance=maintenance)
        if form.is_valid():
            form.save()
            messages.success(request, 'Maintenance record updated successfully!')
            
            if request.headers.get('HX-Request'):
                return JsonResponse({
                    'success': True,
                    'redirect_url': maintenance.get_absolute_url()
                })
            return redirect('transportation:maintenance_detail', pk=maintenance.pk)
    else:
        form = MaintenanceRecordForm(instance=maintenance)
    
    context = {
        'form': form,
        'maintenance': maintenance,
        'vehicle': maintenance.vehicle,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'transportation/partials/maintenance_form_partial.html', context)
    
    return render(request, 'transportation/maintenance_form.html', context)


@login_required
def maintenance_delete(request, pk):
    """Delete maintenance record"""
    maintenance = get_object_or_404(MaintenanceRecord, pk=pk)
    
    if request.method == 'POST':
        vehicle = maintenance.vehicle
        maintenance.delete()
        messages.success(request, 'Maintenance record deleted successfully!')
        
        if request.headers.get('HX-Request'):
            return JsonResponse({
                'success': True,
                'redirect_url': vehicle.get_absolute_url()
            })
        return redirect('transportation:vehicle_detail', slug=vehicle.slug)
    
    # For GET request, show confirmation page
    context = {
        'maintenance': maintenance,
        'vehicle': maintenance.vehicle,
    }
    
    return render(request, 'transportation/maintenance_confirm_delete.html', context)


@login_required
def document_create(request, vehicle_slug):
    """Create vehicle document"""
    vehicle = get_object_or_404(Vehicle, slug=vehicle_slug)
    
    if request.method == 'POST':
        form = VehicleDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.vehicle = vehicle
            document.save()
            messages.success(request, 'Document uploaded successfully!')
            
            if request.headers.get('HX-Request'):
                return JsonResponse({
                    'success': True,
                    'redirect_url': vehicle.get_absolute_url()
                })
            return redirect('transportation:vehicle_detail', slug=vehicle.slug)
    else:
        form = VehicleDocumentForm()
    
    context = {'form': form, 'vehicle': vehicle}
    
    if request.headers.get('HX-Request'):
        return render(request, 'transportation/document_form_partial.html', context)
    
    return render(request, 'transportation/document_form.html', context)


@login_required
def component_list(request):
    """List vehicle components"""
    components = VehicleComponent.objects.order_by('category', 'name')
    
    # Filter by category
    category_filter = request.GET.get('category', '')
    if category_filter:
        components = components.filter(category=category_filter)
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        components = components.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(components, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    categories = VehicleComponent.COMPONENT_CATEGORIES
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'category_filter': category_filter,
        'categories': categories,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'transportation/component_list_partial.html', context)
    
    return render(request, 'transportation/component_list.html', context)


@login_required
def component_detail(request, slug):
    """Component detail view"""
    component = get_object_or_404(VehicleComponent, slug=slug)
    
    # Get component instances
    instances = component.instances.select_related(
        'vehicle__vehicle_model__make'
    ).filter(is_active=True)
    
    context = {
        'component': component,
        'instances': instances,
    }
    
    return render(request, 'transportation/component_detail.html', context)


@login_required
def inspection_create(request, instance_slug):
    """Create component inspection"""
    instance = get_object_or_404(VehicleComponentInstance, slug=instance_slug)
    
    if request.method == 'POST':
        form = ComponentInspectionForm(request.POST, request.FILES)
        if form.is_valid():
            inspection = form.save(commit=False)
            inspection.component_instance = instance
            inspection.inspector = request.user
            inspection.save()
            messages.success(request, 'Inspection record created successfully!')
            
            if request.headers.get('HX-Request'):
                return JsonResponse({
                    'success': True,
                    'redirect_url': instance.vehicle.get_absolute_url()
                })
            return redirect('transportation:vehicle_detail', slug=instance.vehicle.slug)
    else:
        form = ComponentInspectionForm()
    
    context = {'form': form, 'instance': instance}
    
    if request.headers.get('HX-Request'):
        return render(request, 'transportation/inspection_form_partial.html', context)
    
    return render(request, 'transportation/inspection_form.html', context)


@login_required
def vehicle_model_list(request):
    """List vehicle models"""
    models = VehicleModel.objects.select_related(
        'make', 'vehicle_type'
    ).order_by('make__name', 'name')
    
    # Filter by make
    make_filter = request.GET.get('make', '')
    if make_filter:
        models = models.filter(make__slug=make_filter)
    
    # Filter by type
    type_filter = request.GET.get('type', '')
    if type_filter:
        models = models.filter(vehicle_type__slug=type_filter)
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        models = models.filter(
            Q(name__icontains=search_query) |
            Q(make__name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(models, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    makes = VehicleMake.objects.all().order_by('name')
    vehicle_types = VehicleType.objects.all()
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'make_filter': make_filter,
        'type_filter': type_filter,
        'makes': makes,
        'vehicle_types': vehicle_types,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'transportation/vehicle_model_list_partial.html', context)
    
    return render(request, 'transportation/vehicle_model_list.html', context)


@login_required
def vehicle_model_create(request):
    """Create vehicle model"""
    if request.method == 'POST':
        form = VehicleModelForm(request.POST)
        if form.is_valid():
            model = form.save()
            messages.success(request, f'Vehicle model {model.name} created successfully!')
            
            if request.headers.get('HX-Request'):
                return JsonResponse({
                    'success': True,
                    'redirect_url': reverse('transportation:vehicle_model_list')
                })
            return redirect('transportation:vehicle_model_list')
    else:
        form = VehicleModelForm()
    
    context = {'form': form}
    
    if request.headers.get('HX-Request'):
        return render(request, 'transportation/vehicle_model_form_partial.html', context)
    
    return render(request, 'transportation/vehicle_model_form.html', context)


@login_required
def vehicle_model_create_ajax(request):
    """Create a new vehicle model via HTMX"""
    if request.method == 'POST':
        form = QuickVehicleModelForm(request.POST)
        if form.is_valid():
            try:
                vehicle_model = form.save()
                print(f"DEBUG: Vehicle model created successfully: {vehicle_model}")
                
                # Return JavaScript to update the select and close modal
                context = {
                    'vehicle_model': vehicle_model,
                    'success': True
                }
                return render(request, 'transportation/partials/vehicle_model_success.html', context)
            except Exception as e:
                print(f"DEBUG: Error saving vehicle model: {e}")
                form.add_error(None, f"Error saving vehicle model: {str(e)}")
        else:
            print(f"DEBUG: Form errors: {form.errors}")
            # Return form with errors
            return render(request, 'transportation/partials/vehicle_model_form.html', {'form': form})
    else:
        form = QuickVehicleModelForm()
        return render(request, 'transportation/partials/vehicle_model_form.html', {'form': form})


@login_required
def vehicle_model_form_modal(request):
    """Return the modal form for creating a new vehicle model"""
    form = QuickVehicleModelForm()
    return render(request, 'transportation/partials/vehicle_model_modal.html', {'form': form})


@login_required
def vehicle_make_create_ajax(request):
    """Create a new vehicle make via HTMX"""
    if request.method == 'POST':
        form = QuickVehicleMakeForm(request.POST)
        if form.is_valid():
            try:
                vehicle_make = form.save()
                print(f"DEBUG: Vehicle make created successfully: {vehicle_make}")
                
                # Return JavaScript to update the select and close modal
                context = {
                    'vehicle_make': vehicle_make,
                    'success': True
                }
                return render(request, 'transportation/partials/vehicle_make_success.html', context)
            except Exception as e:
                print(f"DEBUG: Error saving vehicle make: {e}")
                form.add_error(None, f"Error saving vehicle make: {str(e)}")
        else:
            print(f"DEBUG: Form errors: {form.errors}")
        
        # Return form with errors
        return render(request, 'transportation/partials/vehicle_make_form.html', {'form': form})
    else:
        form = QuickVehicleMakeForm()
        return render(request, 'transportation/partials/vehicle_make_form.html', {'form': form})


@login_required
def vehicle_make_form_modal(request):
    """Return the modal form for creating a new vehicle make"""
    form = QuickVehicleMakeForm()
    return render(request, 'transportation/partials/vehicle_make_modal.html', {'form': form})


@login_required
def vehicle_type_create_ajax(request):
    """Create a new vehicle type via HTMX"""
    if request.method == 'POST':
        print(f"DEBUG: POST request received with data: {request.POST}")
        form = QuickVehicleTypeForm(request.POST)
        print(f"DEBUG: Form created, is_valid: {form.is_valid()}")
        if form.is_valid():
            try:
                # Check if this type already exists
                existing_type = VehicleType.objects.filter(name=form.cleaned_data['name']).first()
                if existing_type:
                    print(f"DEBUG: Type already exists: {existing_type}")
                    form.add_error('name', 'This vehicle type already exists.')
                    
                    # Pass context for error case
                    existing_types = VehicleType.objects.values_list('name', flat=True)
                    available_choices = [choice for choice in VehicleType.TYPE_CHOICES if choice[0] not in existing_types]
                    context = {
                        'form': form,
                        'has_available_types': len(available_choices) > 0,
                        'available_count': len(available_choices)
                    }
                    return render(request, 'transportation/partials/vehicle_type_form.html', context)
                
                vehicle_type = form.save()
                print(f"DEBUG: Vehicle type created successfully: {vehicle_type}")
                
                # Return JavaScript to update the select and close modal
                context = {
                    'vehicle_type': vehicle_type,
                    'success': True
                }
                return render(request, 'transportation/partials/vehicle_type_success.html', context)
            except Exception as e:
                print(f"DEBUG: Error saving vehicle type: {e}")
                form.add_error(None, f"Error saving vehicle type: {str(e)}")
        else:
            print(f"DEBUG: Form errors: {form.errors}")
        
        # Return form with errors
        existing_types = VehicleType.objects.values_list('name', flat=True)
        available_choices = [choice for choice in VehicleType.TYPE_CHOICES if choice[0] not in existing_types]
        context = {
            'form': form,
            'has_available_types': len(available_choices) > 0,
            'available_count': len(available_choices)
        }
        return render(request, 'transportation/partials/vehicle_type_form.html', context)
    else:
        print("DEBUG: GET request for vehicle type form")
        form = QuickVehicleTypeForm()
        print(f"DEBUG: Available choices: {form.fields['name'].widget.choices}")
        
        existing_types = VehicleType.objects.values_list('name', flat=True)
        available_choices = [choice for choice in VehicleType.TYPE_CHOICES if choice[0] not in existing_types]
        context = {
            'form': form,
            'has_available_types': len(available_choices) > 0,
            'available_count': len(available_choices)
        }
        return render(request, 'transportation/partials/vehicle_type_form.html', context)


@login_required
def vehicle_type_form_modal(request):
    """Return the modal form for creating a new vehicle type"""
    form = QuickVehicleTypeForm()
    
    # Check if there are available types to create
    existing_types = VehicleType.objects.values_list('name', flat=True)
    available_choices = [choice for choice in VehicleType.TYPE_CHOICES if choice[0] not in existing_types]
    has_available_types = len(available_choices) > 0
    
    context = {
        'form': form,
        'has_available_types': has_available_types,
        'available_count': len(available_choices)
    }
    return render(request, 'transportation/partials/vehicle_type_modal.html', context)


@login_required
def reports(request):
    """Transportation reports and analytics"""
    # Vehicle statistics
    total_vehicles = Vehicle.objects.count()
    by_status = Vehicle.objects.values('status').annotate(count=Count('id'))
    by_type = Vehicle.objects.values(
        'vehicle_model__vehicle_type__name'
    ).annotate(count=Count('id'))
    
    # Maintenance statistics
    maintenance_costs = MaintenanceRecord.objects.aggregate(
        total_cost=Sum('cost'),
        avg_cost=Avg('cost')
    )
    
    # Upcoming maintenance
    upcoming_maintenance = Vehicle.objects.filter(
        next_service_due__gte=timezone.now().date(),
        next_service_due__lte=timezone.now().date() + timezone.timedelta(days=30)
    ).count()
    
    # Expiring documents
    expiring_insurance = Vehicle.objects.filter(
        insurance_expiry__gte=timezone.now().date(),
        insurance_expiry__lte=timezone.now().date() + timezone.timedelta(days=30)
    ).count()
    
    expiring_registration = Vehicle.objects.filter(
        registration_expiry__gte=timezone.now().date(),
        registration_expiry__lte=timezone.now().date() + timezone.timedelta(days=30)
    ).count()
    
    context = {
        'total_vehicles': total_vehicles,
        'by_status': by_status,
        'by_type': by_type,
        'maintenance_costs': maintenance_costs,
        'upcoming_maintenance': upcoming_maintenance,
        'expiring_insurance': expiring_insurance,
        'expiring_registration': expiring_registration,
    }
    
    return render(request, 'transportation/reports.html', context)


# HTMX helper views
@login_required
@require_http_methods(["GET"])
def get_vehicle_models(request):
    """Get vehicle models for a specific make (HTMX endpoint)"""
    make_id = request.GET.get('make_id')
    models = VehicleModel.objects.filter(make_id=make_id).order_by('name')
    
    html = render_to_string('transportation/partials/model_options.html', {
        'models': models
    })
    
    return HttpResponse(html)


@login_required
@require_http_methods(["GET"])
def vehicle_search_autocomplete(request):
    """Vehicle search autocomplete (HTMX endpoint)"""
    query = request.GET.get('q', '')
    vehicles = Vehicle.objects.filter(
        Q(license_plate__icontains=query) |
        Q(vehicle_model__name__icontains=query) |
        Q(vehicle_model__make__name__icontains=query)
    )[:10]
    
    html = render_to_string('transportation/partials/vehicle_autocomplete.html', {
        'vehicles': vehicles
    })
    
    return HttpResponse(html)


@login_required
def vehicle_model_options_ajax(request):
    """Return vehicle model options for select field"""
    vehicle_models = VehicleModel.objects.all().order_by('make__name', 'name')
    context = {
        'vehicle_models': vehicle_models,
        'selected_model_id': None
    }
    return render(request, 'transportation/partials/vehicle_model_options.html', context)


@login_required
def vehicle_make_options_ajax(request):
    """Return vehicle make options for select field"""
    vehicle_makes = VehicleMake.objects.all().order_by('name')
    context = {
        'vehicle_makes': vehicle_makes,
        'selected_make_id': None
    }
    return render(request, 'transportation/partials/vehicle_make_options.html', context)


@login_required
def vehicle_type_options_ajax(request):
    """Return vehicle type options for select field"""
    vehicle_types = VehicleType.objects.all().order_by('name')
    context = {
        'vehicle_types': vehicle_types,
        'selected_type_id': None
    }
    return render(request, 'transportation/partials/vehicle_type_options.html', context)
