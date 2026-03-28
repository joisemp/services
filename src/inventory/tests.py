from django.test import TestCase
from django.urls import reverse

from core.models import Organization, User
from inventory.models import Warehouse, Category, Brand, Product, Size


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

