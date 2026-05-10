from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from config.mixins.access_mixin import TransportInchargeOnlyAccessMixin
from core.models import Space
from fleet_management.models import Vehicle, Workshop

from . import central_admin as central_admin_views

from ..forms import IssueForm
from ..models import Issue, IssueActivity, IssueImage


class TransportInchargeIssueScopedMixin(TransportInchargeOnlyAccessMixin):
	sidebar_template = 'transport_incharge/sidebar.html'


class VehicleIssueListView(TransportInchargeIssueScopedMixin, ListView):
	template_name = 'transport_incharge/issue_management/vehicle_issue_list.html'
	context_object_name = 'issues'

	def dispatch(self, request, *args, **kwargs):
		self.vehicle = get_object_or_404(Vehicle, slug=kwargs.get('vehicle_slug'))
		if request.user.organization and self.vehicle.org != request.user.organization:
			return redirect('fleet_management:transport_incharge:fleet_list')
		return super().dispatch(request, *args, **kwargs)

	def get_queryset(self):
		return self.vehicle.issues.select_related('reporter', 'vehicle', 'workshop', 'org').order_by('-created_at')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['vehicle'] = self.vehicle
		return context


class IssueCreateView(TransportInchargeIssueScopedMixin, CreateView):
	template_name = 'transport_incharge/issue_management/issue_create.html'
	form_class = IssueForm

	def _get_vehicle_from_query(self):
		vehicle_slug = self.request.GET.get('vehicle')
		if not vehicle_slug or not self.request.user.organization:
			return None
		try:
			return Vehicle.objects.get(slug=vehicle_slug, org=self.request.user.organization)
		except Vehicle.DoesNotExist:
			return None

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs['current_user'] = self.request.user
		return kwargs

	def get_form(self, form_class=None):
		form = super().get_form(form_class)
		if self.request.user.organization:
			form.fields['space'].queryset = Space.objects.filter(org=self.request.user.organization).order_by('name')

		vehicle = self._get_vehicle_from_query()
		if 'vehicle' in form.fields:
			form.fields['vehicle'].required = False
			form.fields['vehicle'].queryset = Vehicle.objects.filter(org=self.request.user.organization).order_by('registration_number')
			if vehicle:
				form.initial['vehicle'] = vehicle.pk

		if 'workshop' in form.fields:
			form.fields['workshop'].required = bool(vehicle)
			form.fields['workshop'].queryset = Workshop.objects.filter(org=self.request.user.organization).order_by('name')

		return form

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['show_workshop_field'] = bool(self._get_vehicle_from_query())
		return context

	def form_valid(self, form):
		form.instance.reporter = self.request.user
		vehicle = self._get_vehicle_from_query()
		if vehicle:
			form.instance.vehicle = vehicle

		response = super().form_valid(form)

		for field_name in ['image1', 'image2', 'image3']:
			image_file = form.cleaned_data.get(field_name)
			if image_file:
				issue_image = IssueImage(issue=self.object, image=image_file)
				issue_image._uploaded_by = self.request.user
				issue_image.save()

		messages.success(self.request, f'Issue "{self.object.title}" created successfully!')
		return response

	def get_success_url(self):
		return reverse_lazy('issue_management:transport_incharge:issue_detail', kwargs={'issue_slug': self.object.slug})


class IssueDetailView(central_admin_views.IssueDetailView):
	template_name = 'central_admin/issue_management/issue_detail.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['sidebar_template'] = 'transport_incharge/sidebar.html'
		if self.object.vehicle:
			context['back_url'] = reverse('fleet_management:transport_incharge:vehicle_detail', kwargs={'slug': self.object.vehicle.slug})
		else:
			context['back_url'] = reverse('fleet_management:transport_incharge:fleet_list')
		return context


class IssueWorkshopTransferView(TransportInchargeIssueScopedMixin, UpdateView):
	model = Issue
	slug_field = 'slug'
	slug_url_kwarg = 'issue_slug'
	fields = ['workshop']
	template_name = 'transport_incharge/issue_management/issue_change_workshop.html'

	def get_queryset(self):
		return Issue.objects.select_related('org', 'vehicle', 'workshop')

	def get_form(self, form_class=None):
		form = super().get_form(form_class)
		if self.request.user.organization and 'workshop' in form.fields:
			form.fields['workshop'].queryset = Workshop.objects.filter(
				org=self.request.user.organization
			).order_by('name')
		return form

	def form_valid(self, form):
		form.instance._changed_by = self.request.user
		old_workshop = self.object.workshop
		response = super().form_valid(form)
		IssueActivity.objects.create(
			issue=self.object,
			activity_type='workshop_changed',
			user=self.request.user,
			description=f'Workshop changed from {old_workshop.name if old_workshop else "None"} to {self.object.workshop.name if self.object.workshop else "None"}',
		)
		messages.success(self.request, 'Workshop assignment updated.')
		return response

	def get_success_url(self):
		return reverse_lazy('issue_management:transport_incharge:issue_detail', kwargs={'issue_slug': self.object.slug})


class IssueDeleteView(central_admin_views.IssueDeleteView):
	"""Transport-incharge specific delete view that redirects to a transport-incharge landing page."""

	def get_success_url(self):
		# If issue is tied to a vehicle, go back to that vehicle's issue list; otherwise go to fleet list
		if self.object and getattr(self.object, 'vehicle', None):
			return reverse_lazy('issue_management:transport_incharge:vehicle_issue_list', kwargs={'vehicle_slug': self.object.vehicle.slug})
		return reverse_lazy('fleet_management:transport_incharge:fleet_list')
