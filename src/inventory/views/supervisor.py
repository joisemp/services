from django.views.generic import ListView, DetailView

from config.mixins.access_mixin import SupervisorOnlyAccessMixin
from inventory.models import Warehouse


class InventoryDashboardView(SupervisorOnlyAccessMixin, ListView):
	model = Warehouse
	template_name = 'supervisor/inventory/dashboard.html'
	context_object_name = 'warehouses'

	def get_queryset(self):
		user = self.request.user
		queryset = user.warehouses.select_related('org').all()

		if not user.is_superuser and user.organization:
			queryset = queryset.filter(org=user.organization)

		return queryset.order_by('name')


class InventoryWarehouseDetailView(SupervisorOnlyAccessMixin, DetailView):
	model = Warehouse
	template_name = 'supervisor/inventory/warehouse_detail.html'
	context_object_name = 'warehouse'
	slug_field = 'slug'
	slug_url_kwarg = 'slug'

	def get_queryset(self):
		user = self.request.user
		queryset = user.warehouses.select_related('org').all()

		if not user.is_superuser and user.organization:
			queryset = queryset.filter(org=user.organization)

		return queryset