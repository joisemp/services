"""
Shared fleet management views accessible by all roles.
This module contains common view logic used across different roles.
"""
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, DetailView

from fleet_management.models import Vehicle


def get_next_status(current_status):
	"""
	Get the next status in the cycling sequence.
	Cycle: Active → Maintenance → Out of Service → Active
	"""
	status_sequence = [
		Vehicle.STATUS_ACTIVE,
		Vehicle.STATUS_IN_MAINTENANCE,
		Vehicle.STATUS_OUT_OF_SERVICE,
	]

	try:
		current_index = status_sequence.index(current_status)
		next_index = (current_index + 1) % len(status_sequence)
		return status_sequence[next_index]
	except (ValueError, IndexError):
		return Vehicle.STATUS_ACTIVE


# TODO: Add common views here
# Example patterns to follow:
# - ListViews with select_related/prefetch_related optimization
# - DetailViews with organization scoping for multi-tenant support
# - Shared permission checks for cross-role access control


class VehicleScopedMixin:
	model = Vehicle
	slug_url_kwarg = 'slug'
	sidebar_template = 'central_admin/sidebar.html'

	def get_user_org(self):
		return getattr(self.request.user, 'organization', None)

	def get_vehicle_queryset(self):
		user = self.request.user
		org = self.get_user_org()

		if user.is_superuser and not org:
			return Vehicle.objects.select_related('org').all()

		if org:
			return Vehicle.objects.select_related('org').filter(org=org)

		return Vehicle.objects.none()

	def get_queryset(self):
		return self.get_vehicle_queryset()

	def get_vehicle(self):
		return get_object_or_404(self.get_vehicle_queryset(), slug=self.kwargs[self.slug_url_kwarg])

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['sidebar_template'] = self.sidebar_template
		return context
