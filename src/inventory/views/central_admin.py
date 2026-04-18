from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DetailView, FormView, View
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.db import transaction
from django.db.models import Q, Prefetch
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone

from config.mixins.access_mixin import CentralAdminOnlyAccessMixin
from inventory.models import Brand, Category, Product, Warehouse, Room, Bucket, Size, Variant, StockMovementLine, ProductDeletionRequest
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
	ProductVariantForm,
	ProductAssignRoomForm,
	ProductAssignBucketForm,
	ProductAssignCategoryForm,
	ProductAssignBrandForm,
	ProductEditForm,
	ProductTypeConversionForm,
	ProductImageUploadForm,
	StockMovementCorrectionForm,
)
from inventory.views.common import (
	ProductCreateWizardSessionMixin,
	apply_product_type_conversion,
	apply_stock_movement_correction,
	create_product_images,
	create_variant_images,
	recompute_product_quantities,
)


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
		created_images = create_product_images(created_product, form.cleaned_data.get('image_files'))
		self.clear_wizard_data()
		if created_images:
			messages.success(self.request, f'Product "{created_product.name}" created successfully with {created_images} image(s).')
		else:
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
		).filter(
			is_deleted=False,
		).order_by('-updated_at')[:10]

		# Get users associated with this warehouse
		users = self.object.users.all().order_by('first_name', 'last_name')

		# Get rooms in this warehouse
		rooms = self.object.rooms.all().prefetch_related('buckets')
		
		context.update({
			'summary_cards': summary_cards,
			'warehouse_products': warehouse_products,
			'warehouse_products_count': self.object.products.filter(is_deleted=False).count(),
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

	def get_search_query(self):
		return self.request.GET.get('q', '').strip()

	def get_queryset(self):
		warehouse = get_object_or_404(Warehouse, slug=self.kwargs['slug'])
		user = self.request.user
		org = getattr(user, 'organization', None)
		
		# Check org access
		if not user.is_superuser and (not org or warehouse.org != org):
			return Product.objects.none()

		queryset = warehouse.products.filter(is_deleted=False).select_related(
			'category',
			'brand',
			'room',
		).prefetch_related(
			'images',
			'variants__brand',
			'variants__images',
		)

		search_query = self.get_search_query()
		if search_query:
			queryset = queryset.filter(
				Q(name__icontains=search_query)
				| Q(product_code__icontains=search_query)
				| Q(description__icontains=search_query)
				| Q(category__name__icontains=search_query)
				| Q(brand__name__icontains=search_query)
				| Q(room__name__icontains=search_query)
				| Q(variants__name__icontains=search_query)
				| Q(variants__brand__name__icontains=search_query)
			).distinct()

		return queryset.order_by('-updated_at')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		warehouse = get_object_or_404(Warehouse, slug=self.kwargs['slug'])
		search_query = self.get_search_query()
		for product in context.get('products', []):
			product.card_images = []
			if product.type == 'MULTI_VARIANT':
				product.variant_brand_names = sorted(
					{variant.brand.name for variant in product.variants.all() if variant.brand}
				)
				for variant in product.variants.all():
					product.card_images.extend(list(variant.images.all()))
			else:
				product.variant_brand_names = []
				product.card_images = list(product.images.all())
			product.card_images = product.card_images[:8]
		context['warehouse'] = warehouse
		context['search_query'] = search_query
		return context


class CentralAdminDeletedWarehouseProductListView(CentralAdminOnlyAccessMixin, ListView):
	model = Product
	template_name = 'central_admin/inventory/warehouse_deleted_product_list.html'
	context_object_name = 'products'
	paginate_by = 20

	def get_search_query(self):
		return self.request.GET.get('q', '').strip()

	def get_warehouse(self):
		warehouse = get_object_or_404(Warehouse, slug=self.kwargs['slug'])
		user = self.request.user
		org = getattr(user, 'organization', None)

		if not user.is_superuser and (not org or warehouse.org != org):
			return None

		return warehouse

	def get_queryset(self):
		warehouse = self.get_warehouse()
		if not warehouse:
			return Product.objects.none()

		queryset = Product.all_objects.filter(
			warehouse=warehouse,
			is_deleted=True,
		).select_related(
			'category',
			'brand',
			'room',
		)

		search_query = self.get_search_query()
		if search_query:
			queryset = queryset.filter(
				Q(name__icontains=search_query)
				| Q(product_code__icontains=search_query)
				| Q(description__icontains=search_query)
				| Q(category__name__icontains=search_query)
				| Q(brand__name__icontains=search_query)
			)

		return queryset.order_by('-deleted_at', '-updated_at')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['warehouse'] = self.get_warehouse()
		context['search_query'] = self.get_search_query()
		return context


class CentralAdminProductDetailView(CentralAdminOnlyAccessMixin, DetailView):
	model = Product
	template_name = 'central_admin/inventory/product_detail.html'
	slug_field = 'slug'
	slug_url_kwarg = 'product_slug'
	context_object_name = 'product'

	def get_queryset(self):
		warehouse = get_object_or_404(Warehouse, slug=self.kwargs['slug'])
		user = self.request.user
		org = getattr(user, 'organization', None)

		if not user.is_superuser and (not org or warehouse.org != org):
			return Product.objects.none()

		return Product.all_objects.filter(warehouse=warehouse).select_related(
			'category',
			'brand',
			'warehouse',
			'room',
			'bucket',
		).prefetch_related(
			'images',
			'variants__brand',
			'variants__size',
			'variants__images',
			'sizes',
		)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		warehouse = get_object_or_404(Warehouse, slug=self.kwargs['slug'])
		context['warehouse'] = warehouse
		variants = list(self.object.variants.select_related('brand', 'size').prefetch_related('images').all())
		context['variants'] = variants
		context['product_images'] = self.object.images.all()
		selected_variant_slug = self.request.GET.get('variant', '').strip()
		selected_variant = None
		if self.object.type == 'MULTI_VARIANT' and variants:
			selected_variant = next((variant for variant in variants if variant.slug == selected_variant_slug), variants[0])
		context['selected_variant'] = selected_variant
		context['selected_variant_images'] = selected_variant.images.all() if selected_variant else []
		context['brands'] = Brand.objects.filter(org=self.object.org).order_by('name')
		context['unit_choices'] = Product._meta.get_field('unit').choices
		context['room_assign_form'] = ProductAssignRoomForm(warehouse=warehouse, initial={'room': self.object.room})
		context['bucket_assign_form'] = ProductAssignBucketForm(
			warehouse=warehouse,
			room=self.object.room,
			initial={'bucket': self.object.bucket},
		)
		context['category_assign_form'] = ProductAssignCategoryForm(
			org=self.object.org,
			initial={'category': self.object.category},
		)
		context['brand_assign_form'] = ProductAssignBrandForm(
			org=self.object.org,
			initial={'brand': self.object.brand},
		)
		context['product_edit_form'] = ProductEditForm(
			org=self.object.org,
			initial={
				'name': self.object.name,
				'description': self.object.description,
				'category': self.object.category,
				'unit': self.object.unit,
			},
		)
		context['product_conversion_form'] = ProductTypeConversionForm(product=self.object)

		if self.object.type == 'MULTI_VARIANT':
			org = getattr(self.request.user, 'organization', None)
			context['variant_form'] = ProductVariantForm(org=org)

		stock_movements = StockMovementLine.objects.filter(
			org=self.object.org,
			product=self.object,
			correction_type='ORIGINAL',
		).select_related('batch', 'recorded_by', 'variant').prefetch_related(
			Prefetch(
				'corrections',
				queryset=StockMovementLine.objects.select_related('batch', 'recorded_by').order_by('-created_at'),
			),
		).order_by('-created_at')
		paginator = Paginator(stock_movements, 20)
		context['stock_movement_logs'] = paginator.get_page(self.request.GET.get('log_page', 1))
		context['has_stock_movement_history'] = StockMovementLine.objects.filter(product=self.object).exists()
		context['pending_deletion_request'] = ProductDeletionRequest.objects.filter(
			product=self.object,
			status='pending',
		).select_related('requested_by').first()

		return context


class CentralAdminProductRestoreView(CentralAdminOnlyAccessMixin, View):
	@transaction.atomic
	def post(self, request, *args, **kwargs):
		warehouse = get_object_or_404(Warehouse, slug=self.kwargs['slug'])
		user = request.user
		org = getattr(user, 'organization', None)

		if not user.is_superuser and (not org or warehouse.org != org):
			messages.error(request, 'You do not have permission to restore this product.')
			return redirect('inventory:central_admin:warehouse_products', slug=warehouse.slug)

		product = get_object_or_404(
			Product.all_objects.filter(warehouse=warehouse),
			slug=self.kwargs['product_slug'],
		)

		if not product.is_deleted:
			messages.info(request, f'Product "{product.name}" is already active.')
			return redirect('inventory:central_admin:product_detail', slug=warehouse.slug, product_slug=product.slug)

		product.is_deleted = False
		product.deleted_at = None
		product.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])

		messages.success(request, f'Product "{product.name}" restored successfully.')
		return redirect('inventory:central_admin:product_detail', slug=warehouse.slug, product_slug=product.slug)


class CentralAdminProductVariantBaseMixin(CentralAdminOnlyAccessMixin):
	def get_warehouse_queryset(self):
		user = self.request.user
		org = getattr(user, 'organization', None)

		if user.is_superuser and not org:
			return Warehouse.objects.all()

		if org:
			return Warehouse.objects.filter(org=org)

		return Warehouse.objects.none()

	def get_product(self):
		warehouse = get_object_or_404(self.get_warehouse_queryset(), slug=self.kwargs['slug'])
		return get_object_or_404(
			warehouse.products.filter(is_deleted=False).select_related(
				'category',
				'brand',
				'warehouse',
				'room',
				'bucket',
			).prefetch_related(
				'images',
				'variants__brand',
				'variants__size',
				'variants__images',
				'sizes',
			),
			slug=self.kwargs['product_slug'],
		)

	def get_success_redirect(self):
		return redirect(
			'inventory:central_admin:product_detail',
			slug=self.kwargs['slug'],
			product_slug=self.kwargs['product_slug'],
		)


class CentralAdminProductAssignRoomView(CentralAdminProductVariantBaseMixin, FormView):
	form_class = ProductAssignRoomForm
	template_name = 'central_admin/inventory/product_detail.html'

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		product = self.get_product()
		kwargs['warehouse'] = product.warehouse
		return kwargs

	def form_valid(self, form):
		product = self.get_product()
		room = form.cleaned_data.get('room')

		product.room = room
		if product.bucket and (not room or product.bucket.room != room):
			product.bucket = None
			product.save(update_fields=['room', 'bucket'])
		else:
			product.save(update_fields=['room'])

		messages.success(self.request, 'Product room updated successfully.')
		return self.get_success_redirect()

	def form_invalid(self, form):
		for errors in form.errors.values():
			for error in errors:
				messages.error(self.request, error)
		return self.get_success_redirect()


class CentralAdminProductAssignBucketView(CentralAdminProductVariantBaseMixin, FormView):
	form_class = ProductAssignBucketForm
	template_name = 'central_admin/inventory/product_detail.html'

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		product = self.get_product()
		kwargs['warehouse'] = product.warehouse
		kwargs['room'] = product.room
		return kwargs

	def form_valid(self, form):
		product = self.get_product()
		bucket = form.cleaned_data.get('bucket')

		product.bucket = bucket
		if bucket and product.room != bucket.room:
			product.room = bucket.room
			product.save(update_fields=['bucket', 'room'])
		else:
			product.save(update_fields=['bucket'])

		messages.success(self.request, 'Product bucket updated successfully.')
		return self.get_success_redirect()

	def form_invalid(self, form):
		for errors in form.errors.values():
			for error in errors:
				messages.error(self.request, error)
		return self.get_success_redirect()


class CentralAdminProductAssignCategoryView(CentralAdminProductVariantBaseMixin, FormView):
	form_class = ProductAssignCategoryForm
	template_name = 'central_admin/inventory/product_detail.html'

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		product = self.get_product()
		kwargs['org'] = product.org
		return kwargs

	def form_valid(self, form):
		product = self.get_product()
		product.category = form.cleaned_data.get('category')
		product.save(update_fields=['category'])

		messages.success(self.request, 'Product category updated successfully.')
		return self.get_success_redirect()

	def form_invalid(self, form):
		for errors in form.errors.values():
			for error in errors:
				messages.error(self.request, error)
		return self.get_success_redirect()


class CentralAdminProductAssignBrandView(CentralAdminProductVariantBaseMixin, FormView):
	form_class = ProductAssignBrandForm
	template_name = 'central_admin/inventory/product_detail.html'

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		product = self.get_product()
		kwargs['org'] = product.org
		return kwargs

	def form_valid(self, form):
		product = self.get_product()

		if product.type != 'SINGLE_VARIANT':
			messages.warning(self.request, 'Brand can only be assigned at product level for single-variant products.')
			return self.get_success_redirect()

		product.brand = form.cleaned_data.get('brand')
		product.save(update_fields=['brand'])

		messages.success(self.request, 'Product brand updated successfully.')
		return self.get_success_redirect()

	def form_invalid(self, form):
		for errors in form.errors.values():
			for error in errors:
				messages.error(self.request, error)
		return self.get_success_redirect()


class CentralAdminProductEditView(CentralAdminProductVariantBaseMixin, FormView):
	form_class = ProductEditForm
	template_name = 'central_admin/inventory/product_detail.html'

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs['org'] = self.get_product().org
		return kwargs

	@transaction.atomic
	def form_valid(self, form):
		product = self.get_product()
		updated_unit = form.cleaned_data['unit']
		old_unit = product.unit
		image_files = form.cleaned_data.get('image_files') or []

		product.name = form.cleaned_data['name']
		product.description = form.cleaned_data['description']
		product.category = form.cleaned_data.get('category')
		product.unit = updated_unit
		product.save(update_fields=['name', 'description', 'category', 'unit'])

		if product.type == 'MULTI_VARIANT' and old_unit != updated_unit:
			product.variants.update(unit=updated_unit)

		if image_files:
			if product.type != 'SINGLE_VARIANT':
				messages.warning(self.request, 'Images can only be added at product level for single-variant products.')
			else:
				created_images = create_product_images(product, image_files)
				if created_images:
					messages.success(self.request, f'Added {created_images} product image(s).')

		messages.success(self.request, 'Product details updated successfully.')
		return self.get_success_redirect()

	def form_invalid(self, form):
		for errors in form.errors.values():
			for error in errors:
				messages.error(self.request, error)
		return self.get_success_redirect()


class CentralAdminProductTypeConvertView(CentralAdminProductVariantBaseMixin, FormView):
	form_class = ProductTypeConversionForm
	template_name = 'central_admin/inventory/product_detail.html'

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs['product'] = self.get_product()
		return kwargs

	@transaction.atomic
	def form_valid(self, form):
		product = self.get_product()
		target_type = form.cleaned_data['target_type']
		source_variant = form.cleaned_data.get('source_variant')

		try:
			apply_product_type_conversion(product, target_type, source_variant=source_variant)
		except ValidationError as exc:
			messages.error(self.request, exc.messages[0] if exc.messages else str(exc))
			return self.get_success_redirect()

		messages.success(self.request, 'Product type converted successfully.')
		return self.get_success_redirect()

	def form_invalid(self, form):
		for errors in form.errors.values():
			for error in errors:
				messages.error(self.request, error)
		for error in form.non_field_errors():
			messages.error(self.request, error)
		return self.get_success_redirect()


class CentralAdminProductDeleteView(CentralAdminProductVariantBaseMixin, View):
	def get_success_redirect(self):
		return redirect('inventory:central_admin:warehouse_products', slug=self.kwargs['slug'])

	@transaction.atomic
	def post(self, request, *args, **kwargs):
		product = self.get_product()

		has_stock_movement_history = StockMovementLine.objects.filter(product=product).exists()
		if has_stock_movement_history:
			messages.warning(request, 'Product cannot be deleted because it has stock movement history.')
			return redirect(
				'inventory:central_admin:product_detail',
				slug=self.kwargs['slug'],
				product_slug=self.kwargs['product_slug'],
			)

		product_name = product.name
		product.soft_delete()
		messages.success(request, f'Product "{product_name}" deleted successfully.')
		return self.get_success_redirect()


class CentralAdminProductDeletionRequestQuerysetMixin(CentralAdminOnlyAccessMixin):
	def get_deletion_request_queryset(self):
		queryset = ProductDeletionRequest.objects.select_related(
			'product',
			'org',
			'warehouse',
			'requested_by',
			'reviewed_by',
		)

		user = self.request.user
		org = getattr(user, 'organization', None)
		if user.is_superuser and not org:
			return queryset
		if org:
			return queryset.filter(org=org)
		return ProductDeletionRequest.objects.none()


class CentralAdminProductDeletionRequestListView(CentralAdminProductDeletionRequestQuerysetMixin, ListView):
	model = ProductDeletionRequest
	template_name = 'central_admin/inventory/product_deletion_request_list.html'
	context_object_name = 'deletion_requests'
	paginate_by = 25

	def get_status_filter(self):
		status = self.request.GET.get('status', 'pending').strip().lower()
		if status in {'pending', 'approved', 'rejected'}:
			return status
		return 'pending'

	def get_queryset(self):
		return self.get_deletion_request_queryset().filter(status=self.get_status_filter()).order_by('-requested_at')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		all_requests = self.get_deletion_request_queryset()
		context['current_status_filter'] = self.get_status_filter()
		context['pending_count'] = all_requests.filter(status='pending').count()
		context['approved_count'] = all_requests.filter(status='approved').count()
		context['rejected_count'] = all_requests.filter(status='rejected').count()
		return context


class CentralAdminProductDeletionRequestDetailView(CentralAdminProductDeletionRequestQuerysetMixin, DetailView):
	model = ProductDeletionRequest
	template_name = 'central_admin/inventory/product_deletion_request_detail.html'
	context_object_name = 'deletion_request'
	slug_field = 'slug'
	slug_url_kwarg = 'deletion_slug'

	def get_queryset(self):
		return self.get_deletion_request_queryset()


class CentralAdminProductDeletionRequestApproveView(CentralAdminProductDeletionRequestQuerysetMixin, View):
	def post(self, request, *args, **kwargs):
		deletion_request = get_object_or_404(
			self.get_deletion_request_queryset(),
			slug=self.kwargs['deletion_slug'],
		)

		if deletion_request.status != 'pending':
			messages.error(request, 'Only pending deletion requests can be approved.')
			return redirect('inventory:central_admin:product_deletion_request_detail', deletion_slug=deletion_request.slug)

		if not deletion_request.product:
			messages.error(request, 'This request cannot be approved because the product no longer exists.')
			return redirect('inventory:central_admin:product_deletion_request_detail', deletion_slug=deletion_request.slug)

		review_reason = request.POST.get('review_reason', '').strip()
		product = deletion_request.product
		product_name = deletion_request.product_name

		with transaction.atomic():
			deletion_request.status = 'approved'
			deletion_request.reviewed_by = request.user
			deletion_request.reviewed_at = timezone.now()
			deletion_request.review_reason = review_reason
			deletion_request.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_reason'])

			product.soft_delete()

		messages.success(request, f'Product "{product_name}" has been deleted.')
		return redirect('inventory:central_admin:product_deletion_request_list')


class CentralAdminProductDeletionRequestRejectView(CentralAdminProductDeletionRequestQuerysetMixin, View):
	def post(self, request, *args, **kwargs):
		deletion_request = get_object_or_404(
			self.get_deletion_request_queryset(),
			slug=self.kwargs['deletion_slug'],
		)

		if deletion_request.status != 'pending':
			messages.error(request, 'Only pending deletion requests can be rejected.')
			return redirect('inventory:central_admin:product_deletion_request_detail', deletion_slug=deletion_request.slug)

		review_reason = request.POST.get('review_reason', '').strip()
		if not review_reason:
			messages.error(request, 'Please provide a reason for rejection.')
			return redirect('inventory:central_admin:product_deletion_request_detail', deletion_slug=deletion_request.slug)

		deletion_request.status = 'rejected'
		deletion_request.reviewed_by = request.user
		deletion_request.reviewed_at = timezone.now()
		deletion_request.review_reason = review_reason
		deletion_request.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_reason'])

		messages.success(request, 'Deletion request rejected.')
		return redirect('inventory:central_admin:product_deletion_request_detail', deletion_slug=deletion_request.slug)


class CentralAdminProductVariantCreateView(CentralAdminProductVariantBaseMixin, FormView):
	form_class = ProductVariantForm
	template_name = 'central_admin/inventory/product_detail.html'

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs['org'] = getattr(self.request.user, 'organization', None)
		return kwargs

	@transaction.atomic
	def form_valid(self, form):
		product = self.get_product()

		if product.type != 'MULTI_VARIANT':
			messages.warning(self.request, 'Variants can only be managed for multi-variant products.')
			return self.get_success_redirect()

		total_incoming_quantity = form.cleaned_data['total_incoming_quantity']
		total_used_quantity = form.cleaned_data['total_used_quantity']
		universal_available_quantity = total_incoming_quantity - total_used_quantity

		size = None
		size_name = form.cleaned_data.get('size_name', '').strip()
		if size_name:
			size, _ = Size.objects.get_or_create(
				org=product.org,
				product=product,
				name=size_name,
				defaults={'description': '', 'variant': None},
			)

		variant = Variant.objects.create(
			name=form.cleaned_data['name'],
			unit=product.unit,
			product=product,
			brand=form.cleaned_data.get('brand'),
			size=size,
			total_incoming_quantity=total_incoming_quantity,
			total_used_quantity=total_used_quantity,
			universal_available_quantity=universal_available_quantity,
		)

		created_images = create_variant_images(variant, form.cleaned_data.get('image_files') or [])

		recompute_product_quantities(product)
		if created_images:
			messages.success(self.request, f'Variant created successfully with {created_images} image(s).')
		else:
			messages.success(self.request, 'Variant created successfully.')
		return self.get_success_redirect()

	def form_invalid(self, form):
		for errors in form.errors.values():
			for error in errors:
				messages.error(self.request, error)
		return self.get_success_redirect()


class CentralAdminProductVariantUpdateView(CentralAdminProductVariantBaseMixin, FormView):
	form_class = ProductVariantForm
	template_name = 'central_admin/inventory/product_detail.html'

	def get_variant(self):
		product = self.get_product()
		return get_object_or_404(product.variants.select_related('brand', 'size'), slug=self.kwargs['variant_slug'])

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs['org'] = getattr(self.request.user, 'organization', None)
		return kwargs

	def get_initial(self):
		variant = self.get_variant()
		return {
			'name': variant.name,
			'brand': variant.brand,
			'size_name': variant.size.name if variant.size else '',
			'total_incoming_quantity': variant.total_incoming_quantity,
			'total_used_quantity': variant.total_used_quantity,
		}

	@transaction.atomic
	def form_valid(self, form):
		product = self.get_product()

		if product.type != 'MULTI_VARIANT':
			messages.warning(self.request, 'Variants can only be managed for multi-variant products.')
			return self.get_success_redirect()

		variant = self.get_variant()
		size = None
		size_name = form.cleaned_data.get('size_name', '').strip()
		if size_name:
			size, _ = Size.objects.get_or_create(
				org=product.org,
				product=product,
				name=size_name,
				defaults={'description': '', 'variant': None},
			)

		variant.name = form.cleaned_data['name']
		variant.unit = product.unit
		variant.brand = form.cleaned_data.get('brand')
		variant.size = size
		variant.total_incoming_quantity = form.cleaned_data['total_incoming_quantity']
		variant.total_used_quantity = form.cleaned_data['total_used_quantity']
		variant.universal_available_quantity = variant.total_incoming_quantity - variant.total_used_quantity
		variant.save()

		created_images = create_variant_images(variant, form.cleaned_data.get('image_files') or [])

		recompute_product_quantities(product)
		if created_images:
			messages.success(self.request, f'Variant updated successfully and {created_images} image(s) added.')
		else:
			messages.success(self.request, 'Variant updated successfully.')
		return self.get_success_redirect()

	def form_invalid(self, form):
		for errors in form.errors.values():
			for error in errors:
				messages.error(self.request, error)
		return self.get_success_redirect()


class CentralAdminProductVariantDeleteView(CentralAdminProductVariantBaseMixin, View):
	@transaction.atomic
	def post(self, request, *args, **kwargs):
		product = self.get_product()

		if product.type != 'MULTI_VARIANT':
			messages.warning(request, 'Variants can only be managed for multi-variant products.')
			return self.get_success_redirect()

		variant = get_object_or_404(product.variants.all(), slug=self.kwargs['variant_slug'])
		variant.delete()
		recompute_product_quantities(product)
		messages.success(request, 'Variant deleted successfully.')
		return self.get_success_redirect()


class CentralAdminProductImageManagementView(CentralAdminProductVariantBaseMixin, FormView):
	form_class = ProductImageUploadForm
	template_name = 'central_admin/inventory/image_management.html'

	def dispatch(self, request, *args, **kwargs):
		product = self.get_product()
		if product.type != 'SINGLE_VARIANT':
			messages.warning(request, 'Product-level image management is available only for single-variant products.')
			return self.get_success_redirect()
		return super().dispatch(request, *args, **kwargs)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		product = self.get_product()
		context['warehouse'] = get_object_or_404(self.get_warehouse_queryset(), slug=self.kwargs['slug'])
		context['product'] = product
		context['image_items'] = product.images.all()
		context['image_scope'] = 'product'
		context['image_scope_title'] = 'Product Images'
		context['back_url_name'] = 'inventory:central_admin:product_detail'
		return context

	def get_success_url(self):
		return reverse_lazy(
			'inventory:central_admin:product_images_manage',
			kwargs={'slug': self.kwargs['slug'], 'product_slug': self.kwargs['product_slug']},
		)

	def form_valid(self, form):
		product = self.get_product()
		created_images = create_product_images(product, form.cleaned_data.get('images') or [])
		if created_images:
			messages.success(self.request, f'Uploaded {created_images} product image(s).')
		return HttpResponseRedirect(self.get_success_url())

	def form_invalid(self, form):
		for errors in form.errors.values():
			for error in errors:
				messages.error(self.request, error)
		return HttpResponseRedirect(self.get_success_url())


class CentralAdminProductImageDeleteView(CentralAdminProductVariantBaseMixin, View):
	def post(self, request, *args, **kwargs):
		product = self.get_product()
		image = get_object_or_404(product.images.all(), slug=self.kwargs['image_slug'])
		image.delete()
		messages.success(request, 'Product image deleted successfully.')
		return redirect(
			'inventory:central_admin:product_images_manage',
			slug=self.kwargs['slug'],
			product_slug=self.kwargs['product_slug'],
		)


class CentralAdminVariantImageManagementView(CentralAdminProductVariantBaseMixin, FormView):
	form_class = ProductImageUploadForm
	template_name = 'central_admin/inventory/image_management.html'

	def get_variant(self):
		product = self.get_product()
		return get_object_or_404(product.variants.select_related('brand', 'size'), slug=self.kwargs['variant_slug'])

	def dispatch(self, request, *args, **kwargs):
		product = self.get_product()
		if product.type != 'MULTI_VARIANT':
			messages.warning(request, 'Variant image management is available only for multi-variant products.')
			return self.get_success_redirect()
		return super().dispatch(request, *args, **kwargs)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		product = self.get_product()
		variant = self.get_variant()
		context['warehouse'] = get_object_or_404(self.get_warehouse_queryset(), slug=self.kwargs['slug'])
		context['product'] = product
		context['variant'] = variant
		context['variants'] = product.variants.all()
		context['image_items'] = variant.images.all()
		context['image_scope'] = 'variant'
		context['image_scope_title'] = f'Variant Images - {variant.name}'
		context['back_url_name'] = 'inventory:central_admin:product_detail'
		return context

	def get_success_url(self):
		return reverse_lazy(
			'inventory:central_admin:variant_images_manage',
			kwargs={
				'slug': self.kwargs['slug'],
				'product_slug': self.kwargs['product_slug'],
				'variant_slug': self.kwargs['variant_slug'],
			},
		)

	def form_valid(self, form):
		variant = self.get_variant()
		created_images = create_variant_images(variant, form.cleaned_data.get('images') or [])
		if created_images:
			messages.success(self.request, f'Uploaded {created_images} variant image(s).')
		return HttpResponseRedirect(self.get_success_url())

	def form_invalid(self, form):
		for errors in form.errors.values():
			for error in errors:
				messages.error(self.request, error)
		return HttpResponseRedirect(self.get_success_url())


class CentralAdminVariantImageDeleteView(CentralAdminProductVariantBaseMixin, View):
	def get_variant(self):
		product = self.get_product()
		return get_object_or_404(product.variants.select_related('brand', 'size'), slug=self.kwargs['variant_slug'])

	def post(self, request, *args, **kwargs):
		variant = self.get_variant()
		image = get_object_or_404(variant.images.all(), slug=self.kwargs['image_slug'])
		image.delete()
		messages.success(request, 'Variant image deleted successfully.')
		return redirect(
			'inventory:central_admin:variant_images_manage',
			slug=self.kwargs['slug'],
			product_slug=self.kwargs['product_slug'],
			variant_slug=self.kwargs['variant_slug'],
		)


class CentralAdminStockMovementCorrectView(CentralAdminWarehouseScopedMixin, FormView):
	form_class = StockMovementCorrectionForm
	template_name = 'central_admin/inventory/stock_movement_correct.html'

	def get_next_url(self):
		next_url = self.request.POST.get('next') or self.request.GET.get('next')
		if next_url and url_has_allowed_host_and_scheme(
			next_url,
			allowed_hosts={self.request.get_host()},
			require_https=self.request.is_secure(),
		):
			return next_url
		return ''

	def get_success_redirect(self):
		next_url = self.get_next_url()
		if next_url:
			return redirect(next_url)
		return redirect('inventory:central_admin:stock_movement_history', slug=self.kwargs['slug'])

	def get_stock_movement(self):
		warehouse = self.get_warehouse()
		return get_object_or_404(
			StockMovementLine.objects.select_related('product', 'variant', 'batch', 'recorded_by'),
			id=self.kwargs['movement_id'],
			org=warehouse.org,
			warehouse=warehouse,
		)

	def dispatch(self, request, *args, **kwargs):
		movement = self.get_stock_movement()
		if movement.correction_type != 'ORIGINAL' or movement.corrections.exists():
			messages.error(request, 'Only non-corrected original entries can be corrected.')
			return self.get_success_redirect()
		return super().dispatch(request, *args, **kwargs)

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs['movement'] = self.get_stock_movement()
		return kwargs

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['warehouse'] = self.get_warehouse()
		context['movement'] = self.get_stock_movement()
		context['next_url'] = self.get_next_url()
		return context

	@transaction.atomic
	def form_valid(self, form):
		movement = self.get_stock_movement()
		try:
			apply_stock_movement_correction(
				movement=movement,
				corrected_quantity=form.cleaned_data['corrected_quantity'],
				correction_reason=form.cleaned_data.get('correction_reason', ''),
				actor=self.request.user,
				reference_code=form.cleaned_data.get('reference_code', ''),
			)
		except ValidationError as exc:
			form.add_error(None, exc.messages[0] if exc.messages else str(exc))
			return self.render_to_response(self.get_context_data(form=form))

		messages.success(self.request, 'Stock movement corrected successfully.')
		return self.get_success_redirect()


class CentralAdminStockMovementHistoryView(CentralAdminWarehouseScopedMixin, ListView):
	model = StockMovementLine
	template_name = 'central_admin/inventory/stock_movement_history.html'
	context_object_name = 'movements'
	paginate_by = 30

	def get_queryset(self):
		warehouse = self.get_warehouse()
		queryset = StockMovementLine.objects.filter(
			org=warehouse.org,
			warehouse=warehouse,
		).select_related('batch', 'product', 'variant', 'recorded_by', 'corrects_movement__batch').prefetch_related('corrections').order_by('-created_at')

		product_slug = self.request.GET.get('product')
		movement_type = self.request.GET.get('movement_type')
		reference_code = self.request.GET.get('reference_code')

		if product_slug:
			queryset = queryset.filter(product__slug=product_slug)

		if movement_type in {'INCOMING', 'OUTGOING'}:
			queryset = queryset.filter(movement_type=movement_type)

		if reference_code:
			queryset = queryset.filter(batch__reference_code__icontains=reference_code.strip())

		return queryset

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		warehouse = self.get_warehouse()
		context['warehouse'] = warehouse
		context['products'] = Product.objects.filter(org=warehouse.org, warehouse=warehouse).order_by('name')
		context['selected_product'] = self.request.GET.get('product', '')
		context['selected_movement_type'] = self.request.GET.get('movement_type', '')
		context['reference_code'] = self.request.GET.get('reference_code', '')
		return context
