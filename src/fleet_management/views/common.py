"""
Shared fleet management views accessible by all roles.
This module contains common view logic used across different roles.
"""
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, DetailView

from fleet_management.models import Vehicle


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
