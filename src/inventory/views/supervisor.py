from django.views.generic import ListView, DetailView, FormView, View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import ValidationError

from config.mixins.access_mixin import SupervisorOnlyAccessMixin
from inventory.models import Warehouse, Room, Product, Brand, Category, Size, Variant, StockMovementBatch, StockMovementLine
from inventory.forms import (
	RoomForm,
	BucketForm,
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
	StockMovementRecordForm,
)
from inventory.views.common import (
	ProductCreateWizardSessionMixin,
	recompute_product_quantities,
	apply_stock_movement_line,
	apply_product_type_conversion,
)


def _get_supervisor_warehouse_queryset(user):
	queryset = user.warehouses.select_related('org').all()

	if not user.is_superuser and user.organization:
		queryset = queryset.filter(org=user.organization)

	return queryset


class SupervisorWarehouseScopedMixin(SupervisorOnlyAccessMixin):
	def get_warehouse(self):
		return get_object_or_404(self.get_warehouse_queryset(), slug=self.kwargs['slug'])

	def get_warehouse_queryset(self):
		return _get_supervisor_warehouse_queryset(self.request.user)

	def get_user_org(self):
		return getattr(self.request.user, 'organization', None)


class SupervisorProductCreateStepOneView(SupervisorWarehouseScopedMixin, ProductCreateWizardSessionMixin, FormView):
	form_class = ProductCreateStepOneForm
	template_name = 'supervisor/inventory/product_create_step1.html'

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
		return redirect('inventory:supervisor:product_create_step2', slug=self.kwargs['slug'])


class SupervisorProductCreateStepTwoView(SupervisorWarehouseScopedMixin, ProductCreateWizardSessionMixin, FormView):
	form_class = ProductCreateStepTwoForm
	template_name = 'supervisor/inventory/product_create_step2.html'

	def dispatch(self, request, *args, **kwargs):
		if 'step1' not in self.get_wizard_data():
			messages.warning(request, 'Please complete Step 1 first.')
			return redirect('inventory:supervisor:product_create_step1', slug=self.kwargs['slug'])
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
			return redirect('inventory:supervisor:product_create_step3_single', slug=self.kwargs['slug'])

		created_product = self.create_product(product_type)
		self.clear_wizard_data()
		messages.success(self.request, f'Product "{created_product.name}" created successfully.')
		return redirect('inventory:supervisor:warehouse_products', slug=self.kwargs['slug'])

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


class SupervisorProductCreateSingleVariantStepView(SupervisorWarehouseScopedMixin, ProductCreateWizardSessionMixin, FormView):
	form_class = ProductCreateSingleVariantForm
	template_name = 'supervisor/inventory/product_create_step3_single_variant.html'

	def dispatch(self, request, *args, **kwargs):
		wizard_data = self.get_wizard_data()
		if 'step1' not in wizard_data:
			messages.warning(request, 'Please complete Step 1 first.')
			return redirect('inventory:supervisor:product_create_step1', slug=self.kwargs['slug'])
		if 'step2' not in wizard_data:
			messages.warning(request, 'Please complete Step 2 first.')
			return redirect('inventory:supervisor:product_create_step2', slug=self.kwargs['slug'])
		if wizard_data.get('step2', {}).get('type') != 'SINGLE_VARIANT':
			messages.warning(request, 'Selected product type is not single variant.')
			return redirect('inventory:supervisor:product_create_step2', slug=self.kwargs['slug'])
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
		return redirect('inventory:supervisor:warehouse_products', slug=self.kwargs['slug'])

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
		return warehouse.products.select_related('category', 'brand', 'room').prefetch_related('variants__brand').order_by('-updated_at')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		warehouse = self.get_warehouse()
		for product in context.get('products', []):
			if product.type == 'MULTI_VARIANT':
				product.variant_brand_names = sorted({variant.brand.name for variant in product.variants.all() if variant.brand})
			else:
				product.variant_brand_names = []
		context['warehouse'] = warehouse
		return context


class SupervisorProductDetailView(SupervisorOnlyAccessMixin, DetailView):
	model = Product
	template_name = 'supervisor/inventory/product_detail.html'
	slug_field = 'slug'
	slug_url_kwarg = 'product_slug'
	context_object_name = 'product'

	def get_queryset(self):
		warehouse = get_object_or_404(_get_supervisor_warehouse_queryset(self.request.user), slug=self.kwargs['slug'])
		return warehouse.products.select_related(
			'category',
			'brand',
			'warehouse',
			'room',
			'bucket',
		).prefetch_related(
			'variants__brand',
			'variants__size',
			'sizes',
		)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		warehouse = get_object_or_404(_get_supervisor_warehouse_queryset(self.request.user), slug=self.kwargs['slug'])
		context['warehouse'] = warehouse
		context['variants'] = self.object.variants.select_related('brand', 'size').all()
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

		context['recent_stock_movements'] = StockMovementLine.objects.filter(
			org=self.object.org,
			product=self.object,
		).select_related('batch', 'recorded_by', 'variant').order_by('-created_at')[:8]

		return context


class SupervisorStockMovementCreateView(SupervisorWarehouseScopedMixin, FormView):
	form_class = StockMovementRecordForm
	template_name = 'supervisor/inventory/stock_movement_create.html'

	def get_movement_mode(self):
		movement_mode = self.request.GET.get('movement_type', '').upper()
		if movement_mode in {'INCOMING', 'OUTGOING'}:
			return movement_mode
		return ''

	def get_product(self):
		warehouse = self.get_warehouse()
		return get_object_or_404(warehouse.products.all(), slug=self.kwargs['product_slug'])

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs['org'] = self.get_user_org()
		kwargs['warehouse'] = self.get_warehouse()
		kwargs['product'] = self.get_product()
		kwargs['force_movement_type'] = self.get_movement_mode()
		return kwargs

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['warehouse'] = self.get_warehouse()
		context['product'] = self.get_product()
		movement_mode = self.get_movement_mode()
		context['movement_mode'] = movement_mode
		context['movement_mode_label'] = movement_mode.title() if movement_mode else 'Movement'
		return context

	@transaction.atomic
	def form_valid(self, form):
		product = self.get_product()
		warehouse = self.get_warehouse()
		batch = StockMovementBatch.objects.create(
			org=warehouse.org,
			warehouse=warehouse,
			recorded_by=self.request.user,
			reference_code=form.cleaned_data.get('reference_code', '').strip(),
			notes=form.cleaned_data.get('notes', ''),
		)

		try:
			apply_stock_movement_line(
				batch=batch,
				product=product,
				variant=form.cleaned_data.get('variant'),
				movement_type=form.cleaned_data['movement_type'],
				quantity=form.cleaned_data['quantity'],
				notes=form.cleaned_data.get('notes', ''),
				actor=self.request.user,
			)
		except ValidationError as exc:
			form.add_error(None, exc.messages[0] if exc.messages else str(exc))
			batch.delete()
			return self.render_to_response(self.get_context_data(form=form))

		messages.success(self.request, f'Stock movement {batch.reference_code} recorded successfully for {product.name}.')
		return redirect(
			'inventory:supervisor:product_detail',
			slug=warehouse.slug,
			product_slug=product.slug,
		)


class SupervisorStockMovementHistoryView(SupervisorWarehouseScopedMixin, ListView):
	model = StockMovementLine
	template_name = 'supervisor/inventory/stock_movement_history.html'
	context_object_name = 'movements'
	paginate_by = 30

	def get_queryset(self):
		warehouse = self.get_warehouse()
		queryset = StockMovementLine.objects.filter(
			org=warehouse.org,
			warehouse=warehouse,
		).select_related('batch', 'product', 'variant', 'recorded_by').order_by('-created_at')

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


class SupervisorProductVariantBaseMixin(SupervisorOnlyAccessMixin):
	def get_warehouse_queryset(self):
		return _get_supervisor_warehouse_queryset(self.request.user)

	def get_product(self):
		warehouse = get_object_or_404(self.get_warehouse_queryset(), slug=self.kwargs['slug'])
		return get_object_or_404(
			warehouse.products.select_related(
				'category',
				'brand',
				'warehouse',
				'room',
				'bucket',
			).prefetch_related(
				'variants__brand',
				'variants__size',
				'sizes',
			),
			slug=self.kwargs['product_slug'],
		)

	def get_success_redirect(self):
		return redirect(
			'inventory:supervisor:product_detail',
			slug=self.kwargs['slug'],
			product_slug=self.kwargs['product_slug'],
		)


class SupervisorProductAssignRoomView(SupervisorProductVariantBaseMixin, FormView):
	form_class = ProductAssignRoomForm
	template_name = 'supervisor/inventory/product_detail.html'

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


class SupervisorProductAssignBucketView(SupervisorProductVariantBaseMixin, FormView):
	form_class = ProductAssignBucketForm
	template_name = 'supervisor/inventory/product_detail.html'

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


class SupervisorProductAssignCategoryView(SupervisorProductVariantBaseMixin, FormView):
	form_class = ProductAssignCategoryForm
	template_name = 'supervisor/inventory/product_detail.html'

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


class SupervisorProductAssignBrandView(SupervisorProductVariantBaseMixin, FormView):
	form_class = ProductAssignBrandForm
	template_name = 'supervisor/inventory/product_detail.html'

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


class SupervisorProductEditView(SupervisorProductVariantBaseMixin, FormView):
	form_class = ProductEditForm
	template_name = 'supervisor/inventory/product_detail.html'

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs['org'] = self.get_product().org
		return kwargs

	@transaction.atomic
	def form_valid(self, form):
		product = self.get_product()
		updated_unit = form.cleaned_data['unit']
		old_unit = product.unit

		product.name = form.cleaned_data['name']
		product.description = form.cleaned_data['description']
		product.category = form.cleaned_data.get('category')
		product.unit = updated_unit
		product.save(update_fields=['name', 'description', 'category', 'unit'])

		if product.type == 'MULTI_VARIANT' and old_unit != updated_unit:
			product.variants.update(unit=updated_unit)

		messages.success(self.request, 'Product details updated successfully.')
		return self.get_success_redirect()

	def form_invalid(self, form):
		for errors in form.errors.values():
			for error in errors:
				messages.error(self.request, error)
		return self.get_success_redirect()


class SupervisorProductTypeConvertView(SupervisorProductVariantBaseMixin, FormView):
	form_class = ProductTypeConversionForm
	template_name = 'supervisor/inventory/product_detail.html'

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


class SupervisorProductDeleteView(SupervisorProductVariantBaseMixin, View):
	def get_success_redirect(self):
		return redirect('inventory:supervisor:warehouse_products', slug=self.kwargs['slug'])

	@transaction.atomic
	def post(self, request, *args, **kwargs):
		product = self.get_product()

		has_stock_movement_history = StockMovementLine.objects.filter(product=product).exists()
		if has_stock_movement_history:
			messages.warning(request, 'Product cannot be deleted because it has stock movement history.')
			return redirect(
				'inventory:supervisor:product_detail',
				slug=self.kwargs['slug'],
				product_slug=self.kwargs['product_slug'],
			)

		product_name = product.name
		product.delete()
		messages.success(request, f'Product "{product_name}" deleted successfully.')
		return self.get_success_redirect()


class SupervisorProductVariantCreateView(SupervisorProductVariantBaseMixin, FormView):
	form_class = ProductVariantForm
	template_name = 'supervisor/inventory/product_detail.html'

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

		Variant.objects.create(
			name=form.cleaned_data['name'],
			unit=product.unit,
			product=product,
			brand=form.cleaned_data.get('brand'),
			size=size,
			total_incoming_quantity=total_incoming_quantity,
			total_used_quantity=total_used_quantity,
			universal_available_quantity=universal_available_quantity,
		)

		recompute_product_quantities(product)
		messages.success(self.request, 'Variant created successfully.')
		return self.get_success_redirect()

	def form_invalid(self, form):
		for errors in form.errors.values():
			for error in errors:
				messages.error(self.request, error)
		return self.get_success_redirect()


class SupervisorProductVariantUpdateView(SupervisorProductVariantBaseMixin, FormView):
	form_class = ProductVariantForm
	template_name = 'supervisor/inventory/product_detail.html'

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

		recompute_product_quantities(product)
		messages.success(self.request, 'Variant updated successfully.')
		return self.get_success_redirect()

	def form_invalid(self, form):
		for errors in form.errors.values():
			for error in errors:
				messages.error(self.request, error)
		return self.get_success_redirect()


class SupervisorProductVariantDeleteView(SupervisorProductVariantBaseMixin, View):
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