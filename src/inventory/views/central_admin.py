from django.views.generic import TemplateView

from config.mixins.access_mixin import CentralAdminOnlyAccessMixin
from inventory.models import Brand, Category, Product, Warehouse


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

		recent_products = products.order_by('-id')[:6]

		context.update(
			{
				'summary_cards': summary_cards,
				'recent_products': recent_products,
				'low_stock_count': low_stock_count,
				'out_of_stock_count': out_of_stock_count,
			}
		)
		return context
