from django.test import TestCase
from django.urls import reverse

from core.models import Organization, User
from inventory.models import Warehouse, Category, Brand, Product, Size, Variant


class CentralAdminProductCreateFlowTests(TestCase):
	def setUp(self):
		self.org = Organization.objects.create(name='Test Org')
		self.user = User.objects.create_user(
			email='admin@example.com',
			password='password123',
			phone_number='+15555550123',
			user_type='central_admin',
			organization=self.org,
		)
		self.client.force_login(self.user)

		self.warehouse = Warehouse.objects.create(
			name='Main Warehouse',
			location='HQ',
			org=self.org,
		)
		self.category = Category.objects.create(name='Electronics', org=self.org)
		self.brand = Brand.objects.create(name='Acme', org=self.org)

	def _step1_url(self):
		return reverse('inventory:central_admin:product_create_step1', kwargs={'slug': self.warehouse.slug})

	def _step2_url(self):
		return reverse('inventory:central_admin:product_create_step2', kwargs={'slug': self.warehouse.slug})

	def _step3_url(self):
		return reverse('inventory:central_admin:product_create_step3_single', kwargs={'slug': self.warehouse.slug})

	def _products_url(self):
		return reverse('inventory:central_admin:warehouse_products', kwargs={'slug': self.warehouse.slug})

	def test_multi_variant_creates_product_after_step2(self):
		response_step1 = self.client.post(
			self._step1_url(),
			{
				'name': 'Paint',
				'description': 'Wall paint',
				'category': self.category.id,
				'unit': 'BOTTLES',
			},
		)
		self.assertRedirects(response_step1, self._step2_url())

		response_step2 = self.client.post(self._step2_url(), {'type': 'MULTI_VARIANT'})
		self.assertRedirects(response_step2, self._products_url())

		product = Product.objects.get(name='Paint')
		self.assertEqual(product.type, 'MULTI_VARIANT')
		self.assertEqual(product.warehouse, self.warehouse)
		self.assertEqual(product.org, self.org)
		self.assertEqual(product.universal_available_quantity, 0)

	def test_single_variant_creates_product_and_size(self):
		self.client.post(
			self._step1_url(),
			{
				'name': 'Cement',
				'description': 'Cement product',
				'category': self.category.id,
				'unit': 'BAGS',
			},
		)
		self.client.post(self._step2_url(), {'type': 'SINGLE_VARIANT'})

		response_step3 = self.client.post(
			self._step3_url(),
			{
				'total_quantity': 25,
				'size_name': '50kg',
				'brand': self.brand.id,
			},
		)

		self.assertRedirects(response_step3, self._products_url())

		product = Product.objects.get(name='Cement')
		self.assertEqual(product.type, 'SINGLE_VARIANT')
		self.assertEqual(product.total_incoming_quantity, 25)
		self.assertEqual(product.total_used_quantity, 0)
		self.assertEqual(product.universal_available_quantity, 25)
		self.assertEqual(product.brand, self.brand)

		size = Size.objects.get(product=product, org=self.org, name='50kg')
		self.assertIsNone(size.variant)

	def test_step2_redirects_to_step1_when_step1_missing(self):
		response = self.client.get(self._step2_url())
		self.assertRedirects(response, self._step1_url())
		self.assertFalse(Product.objects.exists())

	def test_single_variant_invalid_step3_does_not_create_product(self):
		self.client.post(
			self._step1_url(),
			{
				'name': 'Tiles',
				'description': 'Floor tiles',
				'category': self.category.id,
				'unit': 'PIECES',
			},
		)
		self.client.post(self._step2_url(), {'type': 'SINGLE_VARIANT'})

		response_step3 = self.client.post(
			self._step3_url(),
			{
				'total_quantity': 50,
				'size_name': '2x2',
				'brand': '',
			},
		)

		self.assertEqual(response_step3.status_code, 200)
		self.assertFalse(Product.objects.filter(name='Tiles').exists())


class CentralAdminProductDetailVariantManagementTests(TestCase):
	def setUp(self):
		self.org = Organization.objects.create(name='Detail Org')
		self.user = User.objects.create_user(
			email='detail-admin@example.com',
			password='password123',
			phone_number='+15555550124',
			user_type='central_admin',
			organization=self.org,
		)
		self.client.force_login(self.user)

		self.warehouse = Warehouse.objects.create(name='Detail Warehouse', location='HQ', org=self.org)
		self.category = Category.objects.create(name='Hardware', org=self.org)
		self.brand = Brand.objects.create(name='Brand X', org=self.org)

		self.single_product = Product.objects.create(
			name='Single Product',
			description='Single description',
			type='SINGLE_VARIANT',
			unit='PIECES',
			org=self.org,
			warehouse=self.warehouse,
			category=self.category,
			brand=self.brand,
			total_incoming_quantity=20,
			total_used_quantity=5,
			universal_available_quantity=15,
		)

		self.multi_product = Product.objects.create(
			name='Multi Product',
			description='Multi description',
			type='MULTI_VARIANT',
			unit='PIECES',
			org=self.org,
			warehouse=self.warehouse,
			category=self.category,
		)

	def _detail_url(self, product):
		return reverse('inventory:central_admin:product_detail', kwargs={'slug': self.warehouse.slug, 'product_slug': product.slug})

	def _create_variant_url(self):
		return reverse('inventory:central_admin:product_variant_create', kwargs={'slug': self.warehouse.slug, 'product_slug': self.multi_product.slug})

	def _update_variant_url(self, variant):
		return reverse(
			'inventory:central_admin:product_variant_update',
			kwargs={'slug': self.warehouse.slug, 'product_slug': self.multi_product.slug, 'variant_slug': variant.slug},
		)

	def _delete_variant_url(self, variant):
		return reverse(
			'inventory:central_admin:product_variant_delete',
			kwargs={'slug': self.warehouse.slug, 'product_slug': self.multi_product.slug, 'variant_slug': variant.slug},
		)

	def test_single_variant_detail_page_shows_product_tracking_message(self):
		response = self.client.get(self._detail_url(self.single_product))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, self.single_product.name)
		self.assertContains(response, 'Stock for this product is tracked at product level.')

	def test_create_variant_updates_multi_product_totals(self):
		response = self.client.post(
			self._create_variant_url(),
			{
				'name': 'Variant A',
				'brand': self.brand.id,
				'size_name': 'Large',
				'total_incoming_quantity': 100,
				'total_used_quantity': 30,
			},
		)
		self.assertRedirects(response, self._detail_url(self.multi_product))

		self.multi_product.refresh_from_db()
		variant = Variant.objects.get(product=self.multi_product, name='Variant A')
		self.assertEqual(variant.unit, self.multi_product.unit)
		self.assertEqual(variant.universal_available_quantity, 70)
		self.assertEqual(self.multi_product.total_incoming_quantity, 100)
		self.assertEqual(self.multi_product.total_used_quantity, 30)
		self.assertEqual(self.multi_product.universal_available_quantity, 70)

	def test_update_variant_recomputes_multi_product_totals(self):
		variant = Variant.objects.create(
			name='Variant B',
			unit='PIECES',
			product=self.multi_product,
			total_incoming_quantity=50,
			total_used_quantity=10,
			universal_available_quantity=40,
		)

		response = self.client.post(
			self._update_variant_url(variant),
			{
				'name': 'Variant B Updated',
				'brand': self.brand.id,
				'size_name': 'Medium',
				'total_incoming_quantity': 80,
				'total_used_quantity': 25,
			},
		)

		self.assertRedirects(response, self._detail_url(self.multi_product))
		variant.refresh_from_db()
		self.multi_product.refresh_from_db()

		self.assertEqual(variant.name, 'Variant B Updated')
		self.assertEqual(variant.unit, self.multi_product.unit)
		self.assertEqual(variant.universal_available_quantity, 55)
		self.assertEqual(self.multi_product.total_incoming_quantity, 80)
		self.assertEqual(self.multi_product.total_used_quantity, 25)
		self.assertEqual(self.multi_product.universal_available_quantity, 55)

	def test_delete_last_variant_resets_multi_product_totals_to_zero(self):
		variant = Variant.objects.create(
			name='Variant C',
			unit='PIECES',
			product=self.multi_product,
			total_incoming_quantity=20,
			total_used_quantity=5,
			universal_available_quantity=15,
		)

		response = self.client.post(self._delete_variant_url(variant))
		self.assertRedirects(response, self._detail_url(self.multi_product))

		self.multi_product.refresh_from_db()
		self.assertFalse(self.multi_product.variants.exists())
		self.assertEqual(self.multi_product.total_incoming_quantity, 0)
		self.assertEqual(self.multi_product.total_used_quantity, 0)
		self.assertEqual(self.multi_product.universal_available_quantity, 0)

