"""
Fleet Management views for Transport Incharge role.
Transport Incharge has full access to all fleet management features.
"""
import json
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView, View
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator

from config.mixins.access_mixin import TransportInchargeOnlyAccessMixin
from ticket_management.models import Ticket
from fleet_management.forms import VehicleForm, WorkshopForm, VehicleExpenseForm
from fleet_management.models import Vehicle, VehicleActivity, Workshop, VehicleExpense
from fleet_management.views.common import VehicleScopedMixin, WorkshopScopedMixin, get_next_status


class TransportInchargeVehicleScopedMixin(TransportInchargeOnlyAccessMixin, VehicleScopedMixin):
	sidebar_template = 'transport_incharge/sidebar.html'


class TransportInchargeWorkshopScopedMixin(TransportInchargeOnlyAccessMixin, WorkshopScopedMixin):
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

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		vehicle = self.get_vehicle()
		
		# Get recent expenses for this vehicle
		expenses = VehicleExpense.objects.filter(vehicle=vehicle).select_related(
			'created_by', 'vehicle'
		).order_by('-expense_date', '-created_at')[:10]
		
		context['expenses'] = expenses
		context['total_expense_amount'] = sum(e.amount for e in VehicleExpense.objects.filter(vehicle=vehicle))
		
		return context


@method_decorator(require_http_methods(["POST"]), name='dispatch')
class VehicleStatusChangeView(TransportInchargeVehicleScopedMixin, View):
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


# Expense Management Views
class ExpenseListView(TransportInchargeVehicleScopedMixin, ListView):
	"""List all expenses for the organization."""
	template_name = 'transport_incharge/fleet_management/expense_list.html'
	context_object_name = 'expenses'
	paginate_by = 20

	def get_queryset(self):
		org = self.get_user_org()
		return VehicleExpense.objects.filter(
			vehicle__org=org
		).select_related('vehicle', 'created_by').order_by('-expense_date', '-created_at')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		queryset = self.get_queryset()
		context['total_expenses'] = queryset.aggregate(total=models.Sum('amount'))['total'] or 0
		context['expense_count'] = queryset.count()
		return context


class VehicleExpenseListView(TransportInchargeVehicleScopedMixin, ListView):
	"""List expenses for a specific vehicle."""
	template_name = 'transport_incharge/fleet_management/vehicle_expense_list.html'
	context_object_name = 'expenses'
	paginate_by = 20

	def get_queryset(self):
		vehicle = self.get_vehicle()
		return VehicleExpense.objects.filter(
			vehicle=vehicle
		).select_related('vehicle', 'created_by').order_by('-expense_date', '-created_at')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		vehicle = self.get_vehicle()
		context['vehicle'] = vehicle
		queryset = self.get_queryset()
		context['total_expenses'] = queryset.aggregate(total=models.Sum('amount'))['total'] or 0
		return context


class ExpenseCreateView(TransportInchargeVehicleScopedMixin, CreateView):
	"""Create a new expense."""
	form_class = VehicleExpenseForm
	template_name = 'transport_incharge/fleet_management/expense_form.html'

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		org = self.get_user_org()
		
		# Filter vehicles to only those in the org
		if self.request.GET.get('vehicle'):
			try:
				vehicle_slug = self.request.GET.get('vehicle')
				vehicle = self.get_vehicle_queryset().get(slug=vehicle_slug)
				# Pre-populate vehicle if provided
				if not kwargs.get('data'):
					kwargs['initial'] = {'vehicle': vehicle}
			except Vehicle.DoesNotExist:
				pass
		
		return kwargs

	def get_form(self, form_class=None):
		form = super().get_form(form_class)
		org = self.get_user_org()
		
		# Filter vehicle queryset to only org vehicles
		form.fields['vehicle'].queryset = self.get_vehicle_queryset()
		
		return form

	def form_valid(self, form):
		form.instance.created_by = self.request.user
		messages.success(self.request, 'Expense created successfully.')
		return super().form_valid(form)

	def get_success_url(self):
		vehicle_slug = self.object.vehicle.slug
		return reverse_lazy('fleet_management:transport_incharge:vehicle_expense_list', kwargs={'slug': vehicle_slug})


class ExpenseUpdateView(TransportInchargeVehicleScopedMixin, UpdateView):
	"""Update an existing expense."""
	model = VehicleExpense
	form_class = VehicleExpenseForm
	template_name = 'transport_incharge/fleet_management/expense_form.html'

	def get_queryset(self):
		org = self.get_user_org()
		return VehicleExpense.objects.filter(vehicle__org=org)

	def get_form(self, form_class=None):
		form = super().get_form(form_class)
		org = self.get_user_org()
		form.fields['vehicle'].queryset = self.get_vehicle_queryset()
		return form

	def form_valid(self, form):
		messages.success(self.request, 'Expense updated successfully.')
		return super().form_valid(form)

	def get_success_url(self):
		vehicle_slug = self.object.vehicle.slug
		return reverse_lazy('fleet_management:transport_incharge:vehicle_expense_list', kwargs={'slug': vehicle_slug})


class ExpenseDeleteView(TransportInchargeVehicleScopedMixin, DeleteView):
	"""Delete an expense."""
	model = VehicleExpense
	template_name = 'transport_incharge/fleet_management/expense_confirm_delete.html'

	def get_queryset(self):
		org = self.get_user_org()
		return VehicleExpense.objects.filter(vehicle__org=org)

	def delete(self, request, *args, **kwargs):
		self.object = self.get_object()
		vehicle_slug = self.object.vehicle.slug
		response = super().delete(request, *args, **kwargs)
		messages.success(request, 'Expense deleted successfully.')
		return response

	def get_success_url(self):
		vehicle_slug = self.object.vehicle.slug
		return reverse_lazy('fleet_management:transport_incharge:vehicle_expense_list', kwargs={'slug': vehicle_slug})


class WorkshopListView(TransportInchargeWorkshopScopedMixin, ListView):
	template_name = 'transport_incharge/fleet_management/workshop_list.html'
	context_object_name = 'workshops'
	paginate_by = 20

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		queryset = self.get_workshop_queryset()
		context['workshop_summary'] = {
			'total_workshops': queryset.count(),
			'with_incharges': queryset.filter(incharges__isnull=False).distinct().count(),
		}
		return context


class WorkshopCreateView(TransportInchargeWorkshopScopedMixin, CreateView):
	form_class = WorkshopForm
	template_name = 'transport_incharge/fleet_management/workshop_form.html'

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs['org'] = self.get_user_org()
		return kwargs

	def form_valid(self, form):
		org = self.get_user_org()
		if org is None:
			messages.error(self.request, 'A workshop can only be created within an organization context.')
			return redirect('fleet_management:transport_incharge:workshop_list')

		form.instance.org = org
		response = super().form_valid(form)
		messages.success(self.request, 'Workshop created successfully.')
		return response

	def get_success_url(self):
		return reverse_lazy('fleet_management:transport_incharge:workshop_list')


class WorkshopDetailView(TransportInchargeWorkshopScopedMixin, DetailView):
	template_name = 'transport_incharge/fleet_management/workshop_detail.html'
	context_object_name = 'workshop'

	def get_object(self, queryset=None):
		return self.get_workshop()

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		workshop = self.get_workshop()
		context['tickets'] = Ticket.objects.filter(workshop=workshop).select_related(
			'reporter', 'vehicle', 'workshop'
		).order_by('-created_at')
		context['tickets_count'] = context['tickets'].count()
		return context


class WorkshopUpdateView(TransportInchargeWorkshopScopedMixin, UpdateView):
	form_class = WorkshopForm
	template_name = 'transport_incharge/fleet_management/workshop_form.html'
	context_object_name = 'workshop'

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs['org'] = self.get_user_org()
		return kwargs

	def get_object(self, queryset=None):
		return self.get_workshop()

	def get_success_url(self):
		return reverse_lazy('fleet_management:transport_incharge:workshop_detail', kwargs={'slug': self.object.slug})


class WorkshopDeleteView(TransportInchargeWorkshopScopedMixin, DeleteView):
	model = Workshop
	template_name = 'transport_incharge/fleet_management/workshop_confirm_delete.html'
	context_object_name = 'workshop'

	def get_object(self, queryset=None):
		return self.get_workshop()

	def get_success_url(self):
		return reverse_lazy('fleet_management:transport_incharge:workshop_list')
