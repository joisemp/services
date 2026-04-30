"""
Fleet Management views for Central Admin role.
Central admin has full access to vehicle management within their organization.
"""
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from config.mixins.access_mixin import CentralAdminOnlyAccessMixin
from fleet_management.forms import VehicleForm
from fleet_management.models import Vehicle
from fleet_management.views.common import VehicleScopedMixin


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
