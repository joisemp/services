from django.views.generic import ListView, DetailView, View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

from config.mixins.access_mixin import SupervisorOnlyAccessMixin
from inventory.models import Warehouse, Room
from inventory.forms import RoomForm, BucketForm


def _get_supervisor_warehouse_queryset(user):
	queryset = user.warehouses.select_related('org').all()

	if not user.is_superuser and user.organization:
		queryset = queryset.filter(org=user.organization)

	return queryset


class InventoryDashboardView(SupervisorOnlyAccessMixin, ListView):
	model = Warehouse
	template_name = 'supervisor/inventory/dashboard.html'
	context_object_name = 'warehouses'

	def get_queryset(self):
		return _get_supervisor_warehouse_queryset(self.request.user).order_by('name')


class InventoryWarehouseDetailView(SupervisorOnlyAccessMixin, DetailView):
	model = Warehouse
	template_name = 'supervisor/inventory/warehouse_detail.html'
	context_object_name = 'warehouse'
	slug_field = 'slug'
	slug_url_kwarg = 'slug'

	def get_queryset(self):
		return _get_supervisor_warehouse_queryset(self.request.user)

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
			'rooms': self.object.rooms.prefetch_related('buckets').order_by('name'),
			'room_form': RoomForm(),
			'bucket_form': BucketForm(),
			'warehouse_products': products[:10],
			'warehouse_products_count': products.count(),
		})
		return context


class InventoryWarehouseProductListView(SupervisorOnlyAccessMixin, ListView):
	model = Warehouse
	template_name = 'supervisor/inventory/warehouse_product_list.html'
	context_object_name = 'products'
	paginate_by = 20

	def get_warehouse(self):
		return get_object_or_404(_get_supervisor_warehouse_queryset(self.request.user), slug=self.kwargs['slug'])

	def get_queryset(self):
		warehouse = self.get_warehouse()
		return warehouse.products.select_related('category', 'brand', 'room').order_by('-updated_at')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['warehouse'] = self.get_warehouse()
		return context


class SupervisorCreateRoomView(SupervisorOnlyAccessMixin, View):
	def post(self, request, *args, **kwargs):
		warehouse = get_object_or_404(_get_supervisor_warehouse_queryset(request.user), slug=kwargs['slug'])
		form = RoomForm(request.POST)

		if form.is_valid():
			room = form.save(commit=False)
			room.warehouse = warehouse
			room.save()
			messages.success(request, f"Room '{room.name}' created successfully.")
		else:
			messages.error(request, form.errors.get('name', ['Unable to create room.'])[0])

		return redirect('inventory:supervisor:warehouse_detail', slug=warehouse.slug)


class SupervisorCreateBucketView(SupervisorOnlyAccessMixin, View):
	def post(self, request, *args, **kwargs):
		warehouse = get_object_or_404(_get_supervisor_warehouse_queryset(request.user), slug=kwargs['slug'])
		room = get_object_or_404(Room.objects.filter(warehouse=warehouse), slug=kwargs['room_slug'])
		form = BucketForm(request.POST)

		if form.is_valid():
			bucket = form.save(commit=False)
			bucket.room = room
			bucket.save()
			messages.success(request, f"Bucket '{bucket.name}' created in room '{room.name}'.")
		else:
			messages.error(request, form.errors.get('name', ['Unable to create bucket.'])[0])

		return redirect('inventory:supervisor:warehouse_detail', slug=warehouse.slug)