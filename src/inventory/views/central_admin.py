from django.views.generic import TemplateView, ListView, CreateView
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy

from config.mixins.access_mixin import CentralAdminOnlyAccessMixin
from inventory.models import Brand, Category, Product, Warehouse
from inventory.forms import WarehouseForm, CategoryForm, BrandForm


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
