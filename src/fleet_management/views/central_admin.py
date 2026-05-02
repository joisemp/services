"""
Fleet Management views for Central Admin role.
Central admin has full access to vehicle management within their organization.
"""
import json
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView, View
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator

from config.mixins.access_mixin import CentralAdminOnlyAccessMixin
from fleet_management.forms import VehicleForm
from fleet_management.models import Vehicle, VehicleActivity
from fleet_management.views.common import VehicleScopedMixin, get_next_status


class CentralAdminVehicleScopedMixin(CentralAdminOnlyAccessMixin, VehicleScopedMixin):
    sidebar_template = 'central_admin/sidebar.html'


class VehicleListView(CentralAdminVehicleScopedMixin, ListView):
    template_name = 'central_admin/fleet_management/fleet_list.html'
    context_object_name = 'vehicles'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_vehicle_queryset()

        context['vehicle_summary'] = {
            'total_vehicles': queryset.count(),
            'active_vehicles': queryset.filter(status=Vehicle.STATUS_ACTIVE).count(),
            'in_maintenance': queryset.filter(status=Vehicle.STATUS_IN_MAINTENANCE).count(),
            'out_of_service': queryset.filter(status=Vehicle.STATUS_OUT_OF_SERVICE).count(),
        }
        context['organization'] = self.get_user_org()
        return context


class VehicleCreateView(CentralAdminVehicleScopedMixin, CreateView):
    form_class = VehicleForm
    template_name = 'central_admin/fleet_management/vehicle_form.html'

    def form_valid(self, form):
        org = self.get_user_org()
        if org is None:
            messages.error(self.request, 'A vehicle can only be created within an organization context.')
            return redirect('fleet_management:central_admin:vehicle_list')

        form.instance.org = org
        messages.success(self.request, 'Vehicle created successfully.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('fleet_management:central_admin:vehicle_list')


class VehicleDetailView(CentralAdminVehicleScopedMixin, DetailView):
    template_name = 'central_admin/fleet_management/vehicle_detail.html'
    context_object_name = 'vehicle'

    def get_object(self, queryset=None):
        return self.get_vehicle()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vehicle = self.get_vehicle()
        org = self.get_user_org()

        # Get activity logs with pagination
        activities = VehicleActivity.objects.filter(org=org, vehicle=vehicle).order_by('-timestamp')
        paginator = Paginator(activities, 20)
        page_num = self.request.GET.get('activity_page', 1)
        context['activity_logs'] = paginator.get_page(page_num)

        return context


class VehicleUpdateView(CentralAdminVehicleScopedMixin, UpdateView):
    form_class = VehicleForm
    template_name = 'central_admin/fleet_management/vehicle_form.html'
    context_object_name = 'vehicle'

    def get_object(self, queryset=None):
        return self.get_vehicle()

    def get_success_url(self):
        return reverse_lazy('fleet_management:central_admin:vehicle_detail', kwargs={'slug': self.object.slug})


class VehicleDeleteView(CentralAdminVehicleScopedMixin, DeleteView):
    template_name = 'central_admin/fleet_management/vehicle_confirm_delete.html'
    context_object_name = 'vehicle'

    def get_object(self, queryset=None):
        return self.get_vehicle()

    def get_success_url(self):
        return reverse_lazy('fleet_management:central_admin:vehicle_list')


# Tab views - separate pages for each section
class VehicleMaintenanceView(CentralAdminVehicleScopedMixin, DetailView):
    template_name = 'central_admin/fleet_management/vehicle_maintenance.html'
    context_object_name = 'vehicle'

    def get_object(self, queryset=None):
        return self.get_vehicle()


class VehicleTripsView(CentralAdminVehicleScopedMixin, DetailView):
    template_name = 'central_admin/fleet_management/vehicle_trips.html'
    context_object_name = 'vehicle'

    def get_object(self, queryset=None):
        return self.get_vehicle()


class VehicleExpensesView(CentralAdminVehicleScopedMixin, DetailView):
    template_name = 'central_admin/fleet_management/vehicle_expenses.html'
    context_object_name = 'vehicle'

    def get_object(self, queryset=None):
        return self.get_vehicle()


@method_decorator(require_http_methods(["POST"]), name='dispatch')
class VehicleStatusChangeView(CentralAdminVehicleScopedMixin, View):
    """Handle vehicle status changes via AJAX/HTMX."""

    def post(self, request, slug):
        vehicle = self.get_vehicle_from_slug(slug)
        if not vehicle:
            return JsonResponse({'success': False, 'error': 'Vehicle not found'}, status=404)

        # Get the selected status from POST data
        try:
            data = json.loads(request.body) if request.body else {}
            new_status = data.get('status')
        except (json.JSONDecodeError, AttributeError):
            new_status = request.POST.get('status')

        # Validate status
        valid_statuses = [s[0] for s in Vehicle.STATUS_CHOICES]
        if not new_status or new_status not in valid_statuses:
            return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)

        current_status = vehicle.status

        # Update vehicle status
        vehicle.status = new_status
        vehicle.save(update_fields=['status'])

        # Log the status change activity
        org = self.get_user_org()
        VehicleActivity.objects.create(
            vehicle=vehicle,
            org=org,
            action=VehicleActivity.ACTION_STATUS_CHANGED,
            user=request.user,
            field_name='status',
            old_value=current_status,
            new_value=new_status,
            details=f"Status changed from {current_status} to {new_status}",
        )

        # Get the display label for the new status
        status_label = dict(Vehicle.STATUS_CHOICES).get(new_status, new_status)

        # Check if this is an HTMX request
        if request.headers.get('HX-Request'):
            # Return HTML badge for HTMX swap
            status_colors = {
                'active': 'success',
                'maintenance': 'warning',
                'out_of_service': 'danger',
            }
            color = status_colors.get(new_status, 'secondary')
            html = f'<span class="badge rounded-pill bg-{color}">{status_label}</span>'
            return HttpResponse(html)
        
        # Return JSON for AJAX
        return JsonResponse({
            'success': True,
            'new_status': status_label,
            'new_status_value': new_status,
        })

    def get_vehicle_from_slug(self, slug):
        """Get vehicle by slug with org scoping."""
        queryset = self.get_vehicle_queryset()
        return get_object_or_404(queryset, slug=slug)
