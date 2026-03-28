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

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		products = self.object.products.select_related('category', 'brand', 'room').order_by('-updated_at')

		summary_cards = [
			{'label': 'Total Products', 'value': products.count(), 'variant': 'primary', 'icon': 'inventory_2'},
			{
				'label': 'Categories',
				'value': products.exclude(category__isnull=True).values('category').distinct().count(),
				'variant': 'info',
				'icon': 'category',
			},
			{'label': 'Rooms', 'value': self.object.rooms.count(), 'variant': 'success', 'icon': 'door_open'},
			{
				'label': 'Low Stock Items',
				'value': products.filter(universal_available_quantity__lte=10).count(),
				'variant': 'warning',
				'icon': 'warning',
			},
			{
				'label': 'Out of Stock',
				'value': products.filter(universal_available_quantity__lte=0).count(),
				'variant': 'danger',
				'icon': 'error',
			},
			{
				'label': 'Brands',
				'value': products.exclude(brand__isnull=True).values('brand').distinct().count(),
				'variant': 'secondary',
				'icon': 'branding_watermark',
			},
		]

		context.update({
			'summary_cards': summary_cards,
			'warehouse_products': products[:10],
			'warehouse_products_count': products.count(),
		})
		return context