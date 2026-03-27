from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DetailView, FormView
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect

from config.mixins.access_mixin import CentralAdminOnlyAccessMixin
from inventory.models import Brand, Category, Product, Warehouse, Room
from inventory.forms import WarehouseForm, CategoryForm, BrandForm, WarehouseUserAddForm, WarehouseUserRemoveForm, RoomForm


class CentralAdminInventoryDashboardView(CentralAdminOnlyAccessMixin, TemplateView):
	template_name = 'central_admin/inventory/dashboard.html'

	def get_org_filter(self):
		user = self.request.user
		org = getattr(user, 'organization', None)

		if user.is_superuser and not org:
			return {}

		if org:
			return {'org': org}

		return {'pk__in': []}

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		org_filter = self.get_org_filter()

		products = Product.objects.filter(**org_filter).select_related(
			'category',
			'brand',
			'warehouse',
		)
		categories = Category.objects.filter(**org_filter)
		brands = Brand.objects.filter(**org_filter)
		warehouses = Warehouse.objects.filter(**org_filter)

		low_stock_count = products.filter(universal_available_quantity__lte=10).count()
		out_of_stock_count = products.filter(universal_available_quantity__lte=0).count()

		summary_cards = [
			{'label': 'Total Products', 'value': products.count(), 'variant': 'primary', 'icon': 'inventory_2'},
			{'label': 'Categories', 'value': categories.count(), 'variant': 'info', 'icon': 'category'},
			{'label': 'Warehouses', 'value': warehouses.count(), 'variant': 'success', 'icon': 'warehouse'},
			{'label': 'Low Stock Items', 'value': low_stock_count, 'variant': 'warning', 'icon': 'warning'},
			{'label': 'Out of Stock', 'value': out_of_stock_count, 'variant': 'danger', 'icon': 'error'},
			{'label': 'Brands', 'value': brands.count(), 'variant': 'secondary', 'icon': 'branding_watermark'},
		]

		context.update(
			{
				'summary_cards': summary_cards,
				'warehouses': warehouses,
				'low_stock_count': low_stock_count,
				'out_of_stock_count': out_of_stock_count,
			}
		)
		return context


class CentralAdminCategoryListView(CentralAdminOnlyAccessMixin, ListView):
	model = Category
	template_name = 'central_admin/inventory/category_list.html'
	context_object_name = 'categories'
	paginate_by = 20

	def get_org_filter(self):
		user = self.request.user
		org = getattr(user, 'organization', None)

		if user.is_superuser and not org:
			return {}

		if org:
			return {'org': org}

		return {'pk__in': []}

	def get_queryset(self):
		org_filter = self.get_org_filter()
		return Category.objects.filter(**org_filter)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		org_filter = self.get_org_filter()

		products = Product.objects.filter(**org_filter).select_related(
			'category',
			'brand',
			'warehouse',
		)
		categories = Category.objects.filter(**org_filter)
		brands = Brand.objects.filter(**org_filter)
		warehouses = Warehouse.objects.filter(**org_filter)

		low_stock_count = products.filter(universal_available_quantity__lte=10).count()
		out_of_stock_count = products.filter(universal_available_quantity__lte=0).count()

		summary_cards = [
			{'label': 'Total Products', 'value': products.count(), 'variant': 'primary', 'icon': 'inventory_2'},
			{'label': 'Categories', 'value': categories.count(), 'variant': 'info', 'icon': 'category'},
			{'label': 'Warehouses', 'value': warehouses.count(), 'variant': 'success', 'icon': 'warehouse'},
			{'label': 'Low Stock Items', 'value': low_stock_count, 'variant': 'warning', 'icon': 'warning'},
			{'label': 'Out of Stock', 'value': out_of_stock_count, 'variant': 'danger', 'icon': 'error'},
			{'label': 'Brands', 'value': brands.count(), 'variant': 'secondary', 'icon': 'branding_watermark'},
		]

		context.update(
			{
				'summary_cards': summary_cards,
			}
		)
		return context


class CentralAdminBrandListView(CentralAdminOnlyAccessMixin, ListView):
	model = Brand
	template_name = 'central_admin/inventory/brand_list.html'
	context_object_name = 'brands'
	paginate_by = 20

	def get_org_filter(self):
		user = self.request.user
		org = getattr(user, 'organization', None)

		if user.is_superuser and not org:
			return {}

		if org:
			return {'org': org}

		return {'pk__in': []}

	def get_queryset(self):
		org_filter = self.get_org_filter()
		return Brand.objects.filter(**org_filter)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		org_filter = self.get_org_filter()

		products = Product.objects.filter(**org_filter).select_related(
			'category',
			'brand',
			'warehouse',
		)
		categories = Category.objects.filter(**org_filter)
		brands = Brand.objects.filter(**org_filter)
		warehouses = Warehouse.objects.filter(**org_filter)

		low_stock_count = products.filter(universal_available_quantity__lte=10).count()
		out_of_stock_count = products.filter(universal_available_quantity__lte=0).count()

		summary_cards = [
			{'label': 'Total Products', 'value': products.count(), 'variant': 'primary', 'icon': 'inventory_2'},
			{'label': 'Categories', 'value': categories.count(), 'variant': 'info', 'icon': 'category'},
			{'label': 'Warehouses', 'value': warehouses.count(), 'variant': 'success', 'icon': 'warehouse'},
			{'label': 'Low Stock Items', 'value': low_stock_count, 'variant': 'warning', 'icon': 'warning'},
			{'label': 'Out of Stock', 'value': out_of_stock_count, 'variant': 'danger', 'icon': 'error'},
			{'label': 'Brands', 'value': brands.count(), 'variant': 'secondary', 'icon': 'branding_watermark'},
		]

		context.update(
			{
				'summary_cards': summary_cards,
			}
		)
		return context


class CentralAdminCreateWarehouseView(CentralAdminOnlyAccessMixin, CreateView):
	model = Warehouse
	form_class = WarehouseForm
	template_name = 'central_admin/inventory/create_warehouse.html'

	def get_success_url(self):
		return reverse_lazy('inventory:central_admin:inventory_dashboard')

	def form_valid(self, form):
		warehouse = form.save(commit=False)
		org = self.request.user.organization if hasattr(self.request.user, 'organization') else None
		
		if org:
			warehouse.org = org
		
		warehouse.save()
		return HttpResponseRedirect(self.get_success_url())


class CentralAdminCreateCategoryView(CentralAdminOnlyAccessMixin, CreateView):
	model = Category
	form_class = CategoryForm
	template_name = 'central_admin/inventory/create_category.html'

	def get_success_url(self):
		return reverse_lazy('inventory:central_admin:category_list')

	def form_valid(self, form):
		category = form.save(commit=False)
		org = self.request.user.organization if hasattr(self.request.user, 'organization') else None
		
		if org:
			category.org = org
		
		category.save()
		return HttpResponseRedirect(self.get_success_url())


class CentralAdminCreateBrandView(CentralAdminOnlyAccessMixin, CreateView):
	model = Brand
	form_class = BrandForm
	template_name = 'central_admin/inventory/create_brand.html'

	def get_success_url(self):
		return reverse_lazy('inventory:central_admin:brand_list')

	def form_valid(self, form):
		brand = form.save(commit=False)
		org = self.request.user.organization if hasattr(self.request.user, 'organization') else None
		
		if org:
			brand.org = org
		
		brand.save()
		return HttpResponseRedirect(self.get_success_url())


class CentralAdminEditWarehouseView(CentralAdminOnlyAccessMixin, UpdateView):
	model = Warehouse
	form_class = WarehouseForm
	template_name = 'central_admin/inventory/edit_warehouse.html'
	slug_field = 'slug'
	slug_url_kwarg = 'slug'

	def get_success_url(self):
		return reverse_lazy('inventory:central_admin:inventory_dashboard')

	def get_queryset(self):
		user = self.request.user
		org = getattr(user, 'organization', None)
		
		if user.is_superuser and not org:
			return Warehouse.objects.all()
		
		if org:
			return Warehouse.objects.filter(org=org)
		
		return Warehouse.objects.none()

	def form_valid(self, form):
		warehouse = form.save()
		return HttpResponseRedirect(self.get_success_url())


class CentralAdminEditCategoryView(CentralAdminOnlyAccessMixin, UpdateView):
	model = Category
	form_class = CategoryForm
	template_name = 'central_admin/inventory/edit_category.html'
	slug_field = 'slug'
	slug_url_kwarg = 'slug'

	def get_success_url(self):
		return reverse_lazy('inventory:central_admin:category_list')

	def get_queryset(self):
		user = self.request.user
		org = getattr(user, 'organization', None)
		
		if user.is_superuser and not org:
			return Category.objects.all()
		
		if org:
			return Category.objects.filter(org=org)
		
		return Category.objects.none()

	def form_valid(self, form):
		category = form.save()
		return HttpResponseRedirect(self.get_success_url())


class CentralAdminEditBrandView(CentralAdminOnlyAccessMixin, UpdateView):
	model = Brand
	form_class = BrandForm
	template_name = 'central_admin/inventory/edit_brand.html'
	slug_field = 'slug'
	slug_url_kwarg = 'slug'

	def get_success_url(self):
		return reverse_lazy('inventory:central_admin:brand_list')

	def get_queryset(self):
		user = self.request.user
		org = getattr(user, 'organization', None)
		
		if user.is_superuser and not org:
			return Brand.objects.all()
		
		if org:
			return Brand.objects.filter(org=org)
		
		return Brand.objects.none()


class CentralAdminWarehouseDetailView(CentralAdminOnlyAccessMixin, DetailView):
	model = Warehouse
	template_name = 'central_admin/inventory/warehouse_detail.html'
	context_object_name = 'warehouse'
	slug_field = 'slug'
	slug_url_kwarg = 'slug'

	def get_queryset(self):
		user = self.request.user
		org = getattr(user, 'organization', None)
		
		if user.is_superuser and not org:
			return Warehouse.objects.all()
		
		if org:
			return Warehouse.objects.filter(org=org)
		
		return Warehouse.objects.none()

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		org_filter = self.get_org_filter()

		products = Product.objects.filter(**org_filter).select_related(
			'category',
			'brand',
			'warehouse',
		)
		categories = Category.objects.filter(**org_filter)
		brands = Brand.objects.filter(**org_filter)
		warehouses_count = Warehouse.objects.filter(**org_filter).count()

		low_stock_count = products.filter(universal_available_quantity__lte=10).count()
		out_of_stock_count = products.filter(universal_available_quantity__lte=0).count()

		summary_cards = [
			{'label': 'Total Products', 'value': products.count(), 'variant': 'primary', 'icon': 'inventory_2'},
			{'label': 'Categories', 'value': categories.count(), 'variant': 'info', 'icon': 'category'},
			{'label': 'Warehouses', 'value': warehouses_count, 'variant': 'success', 'icon': 'warehouse'},
			{'label': 'Low Stock Items', 'value': low_stock_count, 'variant': 'warning', 'icon': 'warning'},
			{'label': 'Out of Stock', 'value': out_of_stock_count, 'variant': 'danger', 'icon': 'error'},
			{'label': 'Brands', 'value': brands.count(), 'variant': 'secondary', 'icon': 'branding_watermark'},
		]
		
		warehouse_products = self.object.products.all().prefetch_related('category', 'brand')

		# Get users associated with this warehouse
		users = self.object.users.all().order_by('first_name', 'last_name')

		# Get rooms in this warehouse
		rooms = self.object.rooms.all().prefetch_related('buckets')
		
		context.update({
			'summary_cards': summary_cards,
			'warehouse_products': warehouse_products,
			'warehouse_products_count': warehouse_products.count(),
			'users': users,
			'users_count': users.count(),
			'user_add_form': WarehouseUserAddForm(warehouse=self.object),
			'rooms': rooms,
			'rooms_count': rooms.count(),
		})
		return context

	def get_org_filter(self):
		user = self.request.user
		org = getattr(user, 'organization', None)

		if user.is_superuser and not org:
			return {}

		if org:
			return {'org': org}

		return {'pk__in': []}


class CentralAdminWarehouseUserAddView(CentralAdminOnlyAccessMixin, FormView):
	"""
	View to handle adding users to a warehouse
	"""
	form_class = WarehouseUserAddForm
	
	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		# Get warehouse instance for the form
		self.warehouse = get_object_or_404(Warehouse, slug=self.kwargs['slug'])
		kwargs['warehouse'] = self.warehouse
		return kwargs
	
	def form_valid(self, form):
		# Add selected users to warehouse
		users = form.cleaned_data['users']
		self.warehouse.users.add(*users)
		
		# Add success message
		messages.success(self.request, f"Successfully added {len(users)} user(s) to {self.warehouse.name}")
		return redirect('inventory:central_admin:warehouse_detail', slug=self.warehouse.slug)

	def form_invalid(self, form):
		messages.error(self.request, "Error adding users to warehouse. Please try again.")
		return redirect('inventory:central_admin:warehouse_detail', slug=self.kwargs['slug'])


class CentralAdminWarehouseUserRemoveView(CentralAdminOnlyAccessMixin, FormView):
	"""
	View to handle removing users from a warehouse
	"""
	form_class = WarehouseUserRemoveForm
	
	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		# Get warehouse instance for the form
		self.warehouse = get_object_or_404(Warehouse, slug=self.kwargs['slug'])
		kwargs['warehouse'] = self.warehouse
		return kwargs
	
	def form_valid(self, form):
		# Remove the user from warehouse
		user = form.cleaned_data['user_id']
		self.warehouse.users.remove(user)
		
		# Add success message
		messages.success(self.request, f"Successfully removed {user.get_full_name() or user.get_short_name()} from {self.warehouse.name}")
		return redirect('inventory:central_admin:warehouse_detail', slug=self.warehouse.slug)

	def form_invalid(self, form):
		messages.error(self.request, "Error removing user from warehouse. Please try again.")
		return redirect('inventory:central_admin:warehouse_detail', slug=self.kwargs['slug'])


class CentralAdminCreateRoomView(CentralAdminOnlyAccessMixin, CreateView):
	"""
	View to create a new room in a warehouse
	"""
	model = Room
	form_class = RoomForm
	template_name = 'central_admin/inventory/create_room.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		warehouse = get_object_or_404(Warehouse, slug=self.kwargs['slug'])
		context['warehouse'] = warehouse
		return context

	def form_valid(self, form):
		room = form.save(commit=False)
		warehouse = get_object_or_404(Warehouse, slug=self.kwargs['slug'])
		room.warehouse = warehouse
		room.save()
		
		messages.success(self.request, f"Successfully created room '{room.name}' in {warehouse.name}")
		return redirect('inventory:central_admin:warehouse_detail', slug=warehouse.slug)

	def get_success_url(self):
		warehouse = get_object_or_404(Warehouse, slug=self.kwargs['slug'])
		return reverse_lazy('inventory:central_admin:warehouse_detail', kwargs={'slug': warehouse.slug})
