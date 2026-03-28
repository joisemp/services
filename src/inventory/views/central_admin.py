from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DetailView, FormView
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.db import transaction

from config.mixins.access_mixin import CentralAdminOnlyAccessMixin
from inventory.models import Brand, Category, Product, Warehouse, Room, Size
from inventory.forms import (
	WarehouseForm,
	CategoryForm,
	BrandForm,
	WarehouseUserAddForm,
	WarehouseUserRemoveForm,
	RoomForm,
	ProductCreateStepOneForm,
	ProductCreateStepTwoForm,
	ProductCreateSingleVariantForm,
)
from inventory.views.common import ProductCreateWizardSessionMixin


class CentralAdminWarehouseScopedMixin(CentralAdminOnlyAccessMixin):
	def get_warehouse(self):
		return get_object_or_404(self.get_warehouse_queryset(), slug=self.kwargs['slug'])

	def get_warehouse_queryset(self):
		user = self.request.user
		org = getattr(user, 'organization', None)

		if user.is_superuser and not org:
			return Warehouse.objects.all()

		if org:
			return Warehouse.objects.filter(org=org)

		return Warehouse.objects.none()

	def get_user_org(self):
		return getattr(self.request.user, 'organization', None)


class CentralAdminProductCreateStepOneView(CentralAdminWarehouseScopedMixin, ProductCreateWizardSessionMixin, FormView):
	form_class = ProductCreateStepOneForm
	template_name = 'central_admin/inventory/product_create_step1.html'

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs['org'] = self.get_user_org()
		return kwargs

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['warehouse'] = self.get_warehouse()
		context['step'] = 1
		return context

	def get_initial(self):
		initial = super().get_initial()
		wizard_data = self.get_wizard_data()
		step_one_data = wizard_data.get('step1', {})
		if step_one_data:
			initial.update(step_one_data)
		return initial

	def form_valid(self, form):
		step_data = {
			'name': form.cleaned_data['name'],
			'description': form.cleaned_data['description'],
			'category_id': form.cleaned_data['category'].id if form.cleaned_data.get('category') else None,
			'unit': form.cleaned_data['unit'],
		}
		self.set_wizard_step_data('step1', step_data)
		return redirect('inventory:central_admin:product_create_step2', slug=self.kwargs['slug'])


class CentralAdminProductCreateStepTwoView(CentralAdminWarehouseScopedMixin, ProductCreateWizardSessionMixin, FormView):
	form_class = ProductCreateStepTwoForm
	template_name = 'central_admin/inventory/product_create_step2.html'

	def dispatch(self, request, *args, **kwargs):
		if 'step1' not in self.get_wizard_data():
			messages.warning(request, 'Please complete Step 1 first.')
			return redirect('inventory:central_admin:product_create_step1', slug=self.kwargs['slug'])
		return super().dispatch(request, *args, **kwargs)

	def get_initial(self):
		initial = super().get_initial()
		wizard_data = self.get_wizard_data()
		step_two_data = wizard_data.get('step2', {})
		if step_two_data:
			initial.update(step_two_data)
		return initial

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['warehouse'] = self.get_warehouse()
		context['step'] = 2
		return context

	def form_valid(self, form):
		product_type = form.cleaned_data['type']
		self.set_wizard_step_data('step2', {'type': product_type})

		if product_type == 'SINGLE_VARIANT':
			return redirect('inventory:central_admin:product_create_step3_single', slug=self.kwargs['slug'])

		created_product = self.create_product(product_type)
		self.clear_wizard_data()
		messages.success(self.request, f'Product "{created_product.name}" created successfully.')
		return redirect('inventory:central_admin:warehouse_products', slug=self.kwargs['slug'])

	@transaction.atomic
	def create_product(self, product_type):
		warehouse = self.get_warehouse()
		org = warehouse.org
		wizard_data = self.get_wizard_data()
		step_one_data = wizard_data['step1']

		category = None
		category_id = step_one_data.get('category_id')
		if category_id:
			category = Category.objects.filter(id=category_id, org=org).first()

		product = Product.objects.create(
			name=step_one_data['name'],
			description=step_one_data['description'],
			type=product_type,
			unit=step_one_data['unit'],
			org=org,
			warehouse=warehouse,
			category=category,
			universal_available_quantity=0,
			total_incoming_quantity=0,
			total_used_quantity=0,
		)

		return product


class CentralAdminProductCreateSingleVariantStepView(CentralAdminWarehouseScopedMixin, ProductCreateWizardSessionMixin, FormView):
	form_class = ProductCreateSingleVariantForm
	template_name = 'central_admin/inventory/product_create_step3_single_variant.html'

	def dispatch(self, request, *args, **kwargs):
		wizard_data = self.get_wizard_data()
		if 'step1' not in wizard_data:
			messages.warning(request, 'Please complete Step 1 first.')
			return redirect('inventory:central_admin:product_create_step1', slug=self.kwargs['slug'])
		if 'step2' not in wizard_data:
			messages.warning(request, 'Please complete Step 2 first.')
			return redirect('inventory:central_admin:product_create_step2', slug=self.kwargs['slug'])
		if wizard_data.get('step2', {}).get('type') != 'SINGLE_VARIANT':
			messages.warning(request, 'Selected product type is not single variant.')
			return redirect('inventory:central_admin:product_create_step2', slug=self.kwargs['slug'])
		return super().dispatch(request, *args, **kwargs)

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs['org'] = self.get_user_org()
		return kwargs

	def get_initial(self):
		initial = super().get_initial()
		wizard_data = self.get_wizard_data()
		step_three_data = wizard_data.get('step3', {})
		if step_three_data:
			initial.update(step_three_data)
		return initial

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['warehouse'] = self.get_warehouse()
		context['step'] = 3
		return context

	def form_valid(self, form):
		step_data = {
			'total_quantity': form.cleaned_data['total_quantity'],
			'size_name': form.cleaned_data['size_name'],
			'brand_id': form.cleaned_data['brand'].id,
		}
		self.set_wizard_step_data('step3', step_data)

		created_product = self.create_single_variant_product()
		self.clear_wizard_data()
		messages.success(self.request, f'Product "{created_product.name}" created successfully.')
		return redirect('inventory:central_admin:warehouse_products', slug=self.kwargs['slug'])

	@transaction.atomic
	def create_single_variant_product(self):
		warehouse = self.get_warehouse()
		org = warehouse.org
		wizard_data = self.get_wizard_data()
		step_one_data = wizard_data['step1']
		step_three_data = wizard_data['step3']

		category = None
		category_id = step_one_data.get('category_id')
		if category_id:
			category = Category.objects.filter(id=category_id, org=org).first()

		brand = Brand.objects.filter(id=step_three_data['brand_id'], org=org).first()

		total_incoming_quantity = step_three_data['total_quantity']
		total_used_quantity = 0
		universal_available_quantity = total_incoming_quantity - total_used_quantity

		product = Product.objects.create(
			name=step_one_data['name'],
			description=step_one_data['description'],
			type='SINGLE_VARIANT',
			unit=step_one_data['unit'],
			org=org,
			warehouse=warehouse,
			category=category,
			brand=brand,
			total_incoming_quantity=total_incoming_quantity,
			total_used_quantity=total_used_quantity,
			universal_available_quantity=universal_available_quantity,
		)

		size_name = step_three_data['size_name'].strip()
		if size_name:
			Size.objects.get_or_create(
				org=org,
				product=product,
				name=size_name,
				defaults={'description': '', 'variant': None},
			)

		return product


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
		
		warehouse_products = self.object.products.all().select_related(
			'category',
			'brand',
		).order_by('-updated_at')[:10]

		# Get users associated with this warehouse
		users = self.object.users.all().order_by('first_name', 'last_name')

		# Get rooms in this warehouse
		rooms = self.object.rooms.all().prefetch_related('buckets')
		
		context.update({
			'summary_cards': summary_cards,
			'warehouse_products': warehouse_products,
			'warehouse_products_count': self.object.products.count(),
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


class CentralAdminEditRoomView(CentralAdminOnlyAccessMixin, UpdateView):
	"""
	View to edit an existing room
	"""
	model = Room
	form_class = RoomForm
	template_name = 'central_admin/inventory/edit_room.html'
	slug_field = 'slug'
	slug_url_kwarg = 'room_slug'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		warehouse = self.object.warehouse
		context['warehouse'] = warehouse
		return context

	def get_queryset(self):
		user = self.request.user
		org = getattr(user, 'organization', None)
		
		if user.is_superuser and not org:
			return Room.objects.all()
		
		if org:
			# Only allow editing rooms in warehouses owned by this org
			return Room.objects.filter(warehouse__org=org)
		
		return Room.objects.none()

	def form_valid(self, form):
		room = form.save()
		messages.success(self.request, f"Successfully updated room '{room.name}'")
		return redirect('inventory:central_admin:warehouse_detail', slug=room.warehouse.slug)

	def get_success_url(self):
		warehouse = self.object.warehouse
		return reverse_lazy('inventory:central_admin:warehouse_detail', kwargs={'slug': warehouse.slug})


class CentralAdminWarehouseProductListView(CentralAdminOnlyAccessMixin, ListView):
	"""
	View to list all products in a warehouse
	"""
	model = Product
	template_name = 'central_admin/inventory/warehouse_product_list.html'
	context_object_name = 'products'
	paginate_by = 20

	def get_queryset(self):
		warehouse = get_object_or_404(Warehouse, slug=self.kwargs['slug'])
		user = self.request.user
		org = getattr(user, 'organization', None)
		
		# Check org access
		if not user.is_superuser and (not org or warehouse.org != org):
			return Product.objects.none()
		
		return warehouse.products.select_related(
			'category',
			'brand',
			'room',
		).order_by('-updated_at')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		warehouse = get_object_or_404(Warehouse, slug=self.kwargs['slug'])
		context['warehouse'] = warehouse
		return context
