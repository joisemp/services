"""
Fleet Management views for Transport Incharge role.
Transport Incharge has full access to all fleet management features.
"""
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from config.mixins.access_mixin import TransportInchargeOnlyAccessMixin
from fleet_management.forms import VehicleForm
from fleet_management.models import Vehicle
from fleet_management.views.common import VehicleScopedMixin


class TransportInchargeVehicleScopedMixin(TransportInchargeOnlyAccessMixin, VehicleScopedMixin):
	sidebar_template = 'transport_incharge/sidebar.html'


class VehicleListView(TransportInchargeVehicleScopedMixin, ListView):
	template_name = 'transport_incharge/fleet_management/fleet_list.html'
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
		return context


class VehicleCreateView(TransportInchargeVehicleScopedMixin, CreateView):
	form_class = VehicleForm
	template_name = 'transport_incharge/fleet_management/vehicle_form.html'

	def form_valid(self, form):
		org = self.get_user_org()
		if org is None:
			messages.error(self.request, 'A vehicle can only be created within an organization context.')
			return redirect('fleet_management:transport_incharge:fleet_list')

		form.instance.org = org
		messages.success(self.request, 'Vehicle created successfully.')
		return super().form_valid(form)

	def get_success_url(self):
		return reverse_lazy('fleet_management:transport_incharge:fleet_list')


class VehicleDetailView(TransportInchargeVehicleScopedMixin, DetailView):
	template_name = 'transport_incharge/fleet_management/vehicle_detail.html'
	context_object_name = 'vehicle'

	def get_object(self, queryset=None):
		return self.get_vehicle()


class VehicleUpdateView(TransportInchargeVehicleScopedMixin, UpdateView):
	form_class = VehicleForm
	template_name = 'transport_incharge/fleet_management/vehicle_form.html'
	context_object_name = 'vehicle'

	def get_object(self, queryset=None):
		return self.get_vehicle()

	def get_success_url(self):
		return reverse_lazy('fleet_management:transport_incharge:vehicle_detail', kwargs={'slug': self.object.slug})


class VehicleDeleteView(TransportInchargeVehicleScopedMixin, DeleteView):
	template_name = 'transport_incharge/fleet_management/vehicle_confirm_delete.html'
	context_object_name = 'vehicle'

	def get_object(self, queryset=None):
		return self.get_vehicle()

	def get_success_url(self):
		return reverse_lazy('fleet_management:transport_incharge:fleet_list')


# Tab views - separate pages for each section
class VehicleMaintenanceView(TransportInchargeVehicleScopedMixin, DetailView):
	template_name = 'transport_incharge/fleet_management/vehicle_maintenance.html'
	context_object_name = 'vehicle'

	def get_object(self, queryset=None):
		return self.get_vehicle()


class VehicleTripsView(TransportInchargeVehicleScopedMixin, DetailView):
	template_name = 'transport_incharge/fleet_management/vehicle_trips.html'
	context_object_name = 'vehicle'

	def get_object(self, queryset=None):
		return self.get_vehicle()


class VehicleExpensesView(TransportInchargeVehicleScopedMixin, DetailView):
	template_name = 'transport_incharge/fleet_management/vehicle_expenses.html'
	context_object_name = 'vehicle'

	def get_object(self, queryset=None):
		return self.get_vehicle()
