from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from core.models import Organization, User
from inventory.models import Warehouse, Category, Brand, Product, Room, Bucket, Size, Variant, StockMovementBatch, StockMovementLine, ProductDeletionRequest


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
		self.room_one = Room.objects.create(name='Room A', warehouse=self.warehouse)
		self.room_two = Room.objects.create(name='Room B', warehouse=self.warehouse)
		self.bucket_one = Bucket.objects.create(name='Bucket A1', room=self.room_one)
		self.bucket_two = Bucket.objects.create(name='Bucket B1', room=self.room_two)
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

	def _assign_room_url(self, product):
		return reverse('inventory:central_admin:product_assign_room', kwargs={'slug': self.warehouse.slug, 'product_slug': product.slug})

	def _assign_bucket_url(self, product):
		return reverse('inventory:central_admin:product_assign_bucket', kwargs={'slug': self.warehouse.slug, 'product_slug': product.slug})

	def _assign_category_url(self, product):
		return reverse('inventory:central_admin:product_assign_category', kwargs={'slug': self.warehouse.slug, 'product_slug': product.slug})

	def _assign_brand_url(self, product):
		return reverse('inventory:central_admin:product_assign_brand', kwargs={'slug': self.warehouse.slug, 'product_slug': product.slug})

	def _product_edit_url(self, product):
		return reverse('inventory:central_admin:product_edit', kwargs={'slug': self.warehouse.slug, 'product_slug': product.slug})

	def _product_delete_url(self, product):
		return reverse('inventory:central_admin:product_delete', kwargs={'slug': self.warehouse.slug, 'product_slug': product.slug})

	def _product_restore_url(self, product):
		return reverse('inventory:central_admin:product_restore', kwargs={'slug': self.warehouse.slug, 'product_slug': product.slug})

	def _product_convert_url(self, product):
		return reverse('inventory:central_admin:product_convert_type', kwargs={'slug': self.warehouse.slug, 'product_slug': product.slug})

	def _deletion_request_list_url(self):
		return reverse('inventory:central_admin:product_deletion_request_list')

	def _deletion_request_detail_url(self, deletion_request):
		return reverse('inventory:central_admin:product_deletion_request_detail', kwargs={'deletion_slug': deletion_request.slug})

	def _deletion_request_approve_url(self, deletion_request):
		return reverse('inventory:central_admin:product_deletion_request_approve', kwargs={'deletion_slug': deletion_request.slug})

	def _deletion_request_reject_url(self, deletion_request):
		return reverse('inventory:central_admin:product_deletion_request_reject', kwargs={'deletion_slug': deletion_request.slug})

	def _product_list_url(self):
		return reverse('inventory:central_admin:warehouse_products', kwargs={'slug': self.warehouse.slug})

	def _deleted_product_list_url(self):
		return reverse('inventory:central_admin:warehouse_deleted_products', kwargs={'slug': self.warehouse.slug})

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

	def test_assign_room_updates_product_room(self):
		response = self.client.post(self._assign_room_url(self.single_product), {'room': self.room_one.id})
		self.assertRedirects(response, self._detail_url(self.single_product))
		self.single_product.refresh_from_db()
		self.assertEqual(self.single_product.room, self.room_one)

	def test_assign_room_clears_bucket_if_bucket_not_in_room(self):
		self.single_product.room = self.room_one
		self.single_product.bucket = self.bucket_one
		self.single_product.save(update_fields=['room', 'bucket'])

		response = self.client.post(self._assign_room_url(self.single_product), {'room': self.room_two.id})
		self.assertRedirects(response, self._detail_url(self.single_product))
		self.single_product.refresh_from_db()
		self.assertEqual(self.single_product.room, self.room_two)
		self.assertIsNone(self.single_product.bucket)

	def test_assign_bucket_updates_product_bucket_and_room(self):
		response = self.client.post(self._assign_bucket_url(self.single_product), {'bucket': self.bucket_two.id})
		self.assertRedirects(response, self._detail_url(self.single_product))
		self.single_product.refresh_from_db()
		self.assertEqual(self.single_product.bucket, self.bucket_two)
		self.assertEqual(self.single_product.room, self.room_two)

	def test_assign_category_updates_product_category(self):
		new_category = Category.objects.create(name='Electrical', org=self.org)

		response = self.client.post(self._assign_category_url(self.single_product), {'category': new_category.id})
		self.assertRedirects(response, self._detail_url(self.single_product))

		self.single_product.refresh_from_db()
		self.assertEqual(self.single_product.category, new_category)

	def test_assign_brand_updates_single_variant_product_brand(self):
		new_brand = Brand.objects.create(name='Brand Y', org=self.org)

		response = self.client.post(self._assign_brand_url(self.single_product), {'brand': new_brand.id})
		self.assertRedirects(response, self._detail_url(self.single_product))

		self.single_product.refresh_from_db()
		self.assertEqual(self.single_product.brand, new_brand)

	def test_assign_brand_does_not_update_multi_variant_product_brand(self):
		new_brand = Brand.objects.create(name='Brand Z', org=self.org)

		response = self.client.post(self._assign_brand_url(self.multi_product), {'brand': new_brand.id})
		self.assertRedirects(response, self._detail_url(self.multi_product))

		self.multi_product.refresh_from_db()
		self.assertIsNone(self.multi_product.brand)

	def test_product_list_shows_multi_variant_brands_from_variants(self):
		brand_two = Brand.objects.create(name='Brand Two', org=self.org)
		Variant.objects.create(
			name='Variant 1',
			unit='PIECES',
			product=self.multi_product,
			brand=self.brand,
			total_incoming_quantity=10,
			total_used_quantity=2,
			universal_available_quantity=8,
		)
		Variant.objects.create(
			name='Variant 2',
			unit='PIECES',
			product=self.multi_product,
			brand=brand_two,
			total_incoming_quantity=8,
			total_used_quantity=1,
			universal_available_quantity=7,
		)

		response = self.client.get(self._product_list_url())

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Brand X')
		self.assertContains(response, 'Brand Two')

	def test_product_edit_updates_fields_and_variant_units(self):
		variant = Variant.objects.create(
			name='Variant Unit Sync',
			unit='PIECES',
			product=self.multi_product,
			total_incoming_quantity=12,
			total_used_quantity=2,
			universal_available_quantity=10,
		)

		response = self.client.post(
			self._product_edit_url(self.multi_product),
			{
				'name': 'Multi Product Updated',
				'description': 'Updated description',
				'category': self.category.id,
				'unit': 'BAGS',
			},
		)

		self.assertRedirects(response, self._detail_url(self.multi_product))
		self.multi_product.refresh_from_db()
		variant.refresh_from_db()
		self.assertEqual(self.multi_product.name, 'Multi Product Updated')
		self.assertEqual(self.multi_product.unit, 'BAGS')
		self.assertEqual(variant.unit, 'BAGS')

	def test_delete_product_without_history_succeeds(self):
		response = self.client.post(self._product_delete_url(self.single_product))

		self.assertRedirects(response, self._product_list_url())
		self.assertFalse(Product.objects.filter(id=self.single_product.id).exists())

	def test_delete_product_with_history_succeeds_for_central_admin(self):
		batch = StockMovementBatch.objects.create(
			org=self.org,
			warehouse=self.warehouse,
			recorded_by=self.user,
			reference_code='DEL-BLOCK-001',
			notes='Delete blocked history',
		)
		StockMovementLine.objects.create(
			batch=batch,
			org=self.org,
			warehouse=self.warehouse,
			product=self.single_product,
			variant=None,
			target_type='PRODUCT',
			movement_type='INCOMING',
			quantity=1,
			notes='Has history',
			old_total_incoming_quantity=20,
			old_total_used_quantity=5,
			old_available_quantity=15,
			new_total_incoming_quantity=21,
			new_total_used_quantity=5,
			new_available_quantity=16,
			recorded_by=self.user,
		)

		response = self.client.post(self._product_delete_url(self.single_product))
		self.assertRedirects(response, self._product_list_url())
		self.assertFalse(Product.objects.filter(id=self.single_product.id).exists())
		self.assertTrue(Product.all_objects.filter(id=self.single_product.id, is_deleted=True).exists())

	def test_convert_single_to_multi_clears_brand_and_keeps_totals(self):
		response = self.client.post(
			self._product_convert_url(self.single_product),
			{'target_type': 'MULTI_VARIANT'},
		)

		self.assertRedirects(response, self._detail_url(self.single_product))
		self.single_product.refresh_from_db()
		self.assertEqual(self.single_product.type, 'MULTI_VARIANT')
		self.assertIsNone(self.single_product.brand)
		self.assertEqual(self.single_product.total_incoming_quantity, 20)
		self.assertEqual(self.single_product.total_used_quantity, 5)
		self.assertEqual(self.single_product.universal_available_quantity, 15)

	def test_convert_multi_to_single_uses_selected_variant_and_deletes_all_variants(self):
		selected_variant = Variant.objects.create(
			name='Primary Variant',
			unit='PIECES',
			product=self.multi_product,
			brand=self.brand,
			total_incoming_quantity=60,
			total_used_quantity=10,
			universal_available_quantity=50,
		)
		Variant.objects.create(
			name='Secondary Variant',
			unit='PIECES',
			product=self.multi_product,
			total_incoming_quantity=20,
			total_used_quantity=2,
			universal_available_quantity=18,
		)

		response = self.client.post(
			self._product_convert_url(self.multi_product),
			{
				'target_type': 'SINGLE_VARIANT',
				'source_variant': selected_variant.id,
			},
		)

		self.assertRedirects(response, self._detail_url(self.multi_product))
		self.multi_product.refresh_from_db()
		self.assertEqual(self.multi_product.type, 'SINGLE_VARIANT')
		self.assertEqual(self.multi_product.brand, self.brand)
		self.assertEqual(self.multi_product.total_incoming_quantity, 60)
		self.assertEqual(self.multi_product.total_used_quantity, 10)
		self.assertEqual(self.multi_product.universal_available_quantity, 50)
		self.assertFalse(self.multi_product.variants.exists())

	def test_convert_multi_to_single_requires_source_variant(self):
		Variant.objects.create(
			name='Variant Required',
			unit='PIECES',
			product=self.multi_product,
			total_incoming_quantity=12,
			total_used_quantity=2,
			universal_available_quantity=10,
		)

		response = self.client.post(
			self._product_convert_url(self.multi_product),
			{'target_type': 'SINGLE_VARIANT'},
		)

		self.assertRedirects(response, self._detail_url(self.multi_product))
		self.multi_product.refresh_from_db()
		self.assertEqual(self.multi_product.type, 'MULTI_VARIANT')
		self.assertEqual(self.multi_product.variants.count(), 1)

	def test_central_admin_approve_deletion_request_permanently_deletes_product(self):
		request_item = ProductDeletionRequest.objects.create(
			product=self.single_product,
			product_name=self.single_product.name,
			product_code=self.single_product.product_code,
			org=self.org,
			warehouse=self.warehouse,
			requested_by=self.user,
			request_reason='Product should be removed permanently',
		)

		response = self.client.post(
			self._deletion_request_approve_url(request_item),
			{'review_reason': 'Approved for cleanup'},
		)

		self.assertRedirects(response, self._deletion_request_list_url())
		request_item.refresh_from_db()
		self.assertEqual(request_item.status, 'approved')
		self.assertEqual(request_item.reviewed_by, self.user)
		self.assertFalse(Product.objects.filter(id=self.single_product.id).exists())

	def test_central_admin_reject_deletion_request_requires_reason(self):
		request_item = ProductDeletionRequest.objects.create(
			product=self.single_product,
			product_name=self.single_product.name,
			product_code=self.single_product.product_code,
			org=self.org,
			warehouse=self.warehouse,
			requested_by=self.user,
			request_reason='Please delete this product',
		)

		response = self.client.post(self._deletion_request_reject_url(request_item), {'review_reason': ''})

		self.assertRedirects(response, self._deletion_request_detail_url(request_item))
		request_item.refresh_from_db()
		self.assertEqual(request_item.status, 'pending')
		self.assertTrue(Product.objects.filter(id=self.single_product.id).exists())

	def test_central_admin_reject_deletion_request_keeps_product(self):
		request_item = ProductDeletionRequest.objects.create(
			product=self.single_product,
			product_name=self.single_product.name,
			product_code=self.single_product.product_code,
			org=self.org,
			warehouse=self.warehouse,
			requested_by=self.user,
			request_reason='Delete request for old stock item',
		)

		response = self.client.post(
			self._deletion_request_reject_url(request_item),
			{'review_reason': 'Product is still required in operations'},
		)

		self.assertRedirects(response, self._deletion_request_detail_url(request_item))
		request_item.refresh_from_db()
		self.assertEqual(request_item.status, 'rejected')
		self.assertEqual(request_item.reviewed_by, self.user)
		self.assertTrue(Product.objects.filter(id=self.single_product.id).exists())

	def test_central_admin_can_open_deleted_product_detail_and_restore(self):
		self.client.post(self._product_delete_url(self.single_product))

		deleted_product = Product.all_objects.get(id=self.single_product.id)
		self.assertTrue(deleted_product.is_deleted)

		response_detail = self.client.get(self._detail_url(deleted_product))
		self.assertEqual(response_detail.status_code, 200)
		self.assertContains(response_detail, 'This product is deleted.')

		response_restore = self.client.post(self._product_restore_url(deleted_product))
		self.assertRedirects(response_restore, self._detail_url(deleted_product))

		restored_product = Product.objects.get(id=self.single_product.id)
		self.assertFalse(restored_product.is_deleted)

	def test_warehouse_detail_links_to_deleted_products_and_lists_deleted_item(self):
		self.client.post(self._product_delete_url(self.single_product))

		response_warehouse = self.client.get(
			reverse('inventory:central_admin:warehouse_detail', kwargs={'slug': self.warehouse.slug})
		)
		self.assertEqual(response_warehouse.status_code, 200)
		self.assertContains(response_warehouse, 'Deleted Products')

		response_deleted_list = self.client.get(self._deleted_product_list_url())
		self.assertEqual(response_deleted_list.status_code, 200)
		self.assertContains(response_deleted_list, self.single_product.name)


class StockMovementFlowTests(TestCase):
	def setUp(self):
		self.org = Organization.objects.create(name='Movement Org')

		self.supervisor = User.objects.create_user(
			email='supervisor@example.com',
			password='password123',
			phone_number='+15555550125',
			user_type='supervisor',
			organization=self.org,
		)

		self.central_admin = User.objects.create_user(
			email='central@example.com',
			password='password123',
			phone_number='+15555550126',
			user_type='central_admin',
			organization=self.org,
		)

		self.warehouse = Warehouse.objects.create(name='Movement Warehouse', location='HQ', org=self.org)
		self.supervisor.warehouses.add(self.warehouse)

		self.single_product = Product.objects.create(
			name='Single Movement Product',
			description='Single product',
			type='SINGLE_VARIANT',
			unit='PIECES',
			org=self.org,
			warehouse=self.warehouse,
			total_incoming_quantity=10,
			total_used_quantity=2,
			universal_available_quantity=8,
		)

		self.multi_product = Product.objects.create(
			name='Multi Movement Product',
			description='Multi product',
			type='MULTI_VARIANT',
			unit='PIECES',
			org=self.org,
			warehouse=self.warehouse,
		)
		self.variant = Variant.objects.create(
			name='Variant One',
			unit='PIECES',
			product=self.multi_product,
			total_incoming_quantity=20,
			total_used_quantity=5,
			universal_available_quantity=15,
		)
		self.multi_product.total_incoming_quantity = 20
		self.multi_product.total_used_quantity = 5
		self.multi_product.universal_available_quantity = 15
		self.multi_product.save(update_fields=['total_incoming_quantity', 'total_used_quantity', 'universal_available_quantity'])

	def _create_url(self, product):
		return reverse(
			'inventory:supervisor:stock_movement_create',
			kwargs={'slug': self.warehouse.slug, 'product_slug': product.slug},
		)

	def _history_url_supervisor(self):
		return reverse('inventory:supervisor:stock_movement_history', kwargs={'slug': self.warehouse.slug})

	def _product_detail_url(self, product):
		return reverse(
			'inventory:supervisor:product_detail',
			kwargs={'slug': self.warehouse.slug, 'product_slug': product.slug},
		)

	def _history_url_central_admin(self):
		return reverse('inventory:central_admin:stock_movement_history', kwargs={'slug': self.warehouse.slug})

	def _correct_url_supervisor(self, movement):
		return reverse(
			'inventory:supervisor:stock_movement_correct',
			kwargs={'slug': self.warehouse.slug, 'movement_id': movement.id},
		)

	def _correct_url_central_admin(self, movement):
		return reverse(
			'inventory:central_admin:stock_movement_correct',
			kwargs={'slug': self.warehouse.slug, 'movement_id': movement.id},
		)

	def _base_payload(self):
		return {
			'reference_code': 'TXN-001',
			'movement_type': 'INCOMING',
			'quantity': '1',
			'notes': 'Movement note',
		}

	def test_supervisor_can_record_product_wise_for_single_and_multi_variant(self):
		self.client.force_login(self.supervisor)
		single_payload = self._base_payload()
		single_payload.update({'reference_code': 'TXN-001', 'movement_type': 'INCOMING', 'quantity': '5', 'notes': 'Single product replenish', 'variant': ''})
		response_single = self.client.post(self._create_url(self.single_product), single_payload)
		self.assertRedirects(response_single, self._product_detail_url(self.single_product))

		multi_payload = self._base_payload()
		multi_payload.update({'reference_code': 'TXN-002', 'movement_type': 'OUTGOING', 'quantity': '3', 'notes': 'Variant issued', 'variant': str(self.variant.id)})
		response_multi = self.client.post(self._create_url(self.multi_product), multi_payload)
		self.assertRedirects(response_multi, self._product_detail_url(self.multi_product))

		self.single_product.refresh_from_db()
		self.variant.refresh_from_db()
		self.multi_product.refresh_from_db()

		self.assertEqual(self.single_product.total_incoming_quantity, 15)
		self.assertEqual(self.single_product.total_used_quantity, 2)
		self.assertEqual(self.single_product.universal_available_quantity, 13)

		self.assertEqual(self.variant.total_incoming_quantity, 20)
		self.assertEqual(self.variant.total_used_quantity, 8)
		self.assertEqual(self.variant.universal_available_quantity, 12)
		self.assertEqual(self.multi_product.total_incoming_quantity, 20)
		self.assertEqual(self.multi_product.total_used_quantity, 8)
		self.assertEqual(self.multi_product.universal_available_quantity, 12)

		self.assertEqual(StockMovementBatch.objects.count(), 2)
		self.assertEqual(StockMovementLine.objects.count(), 2)

	def test_outgoing_more_than_available_rolls_back_batch(self):
		self.client.force_login(self.supervisor)
		payload = self._base_payload()
		payload.update(
			{
				'movement_type': 'OUTGOING',
				'quantity': '50',
				'notes': 'Invalid outgoing',
				'variant': '',
			}
		)

		response = self.client.post(self._create_url(self.single_product), payload)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'exceeds available quantity')

		self.single_product.refresh_from_db()
		self.assertEqual(self.single_product.universal_available_quantity, 8)
		self.assertFalse(StockMovementBatch.objects.exists())
		self.assertFalse(StockMovementLine.objects.exists())

	def test_multi_variant_requires_variant_selection(self):
		self.client.force_login(self.supervisor)
		payload = self._base_payload()
		payload.update(
			{
				'movement_type': 'INCOMING',
				'quantity': '2',
				'notes': 'Missing variant',
				'variant': '',
			}
		)

		response = self.client.post(self._create_url(self.multi_product), payload)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'require selecting a variant')
		self.assertFalse(StockMovementBatch.objects.exists())

	def test_central_admin_can_view_stock_movement_history(self):
		batch = StockMovementBatch.objects.create(
			org=self.org,
			warehouse=self.warehouse,
			recorded_by=self.supervisor,
			reference_code='TXN-READ',
			notes='Audit batch',
		)
		StockMovementLine.objects.create(
			batch=batch,
			org=self.org,
			warehouse=self.warehouse,
			product=self.single_product,
			variant=None,
			target_type='PRODUCT',
			movement_type='INCOMING',
			quantity=1,
			notes='Audit line',
			old_total_incoming_quantity=10,
			old_total_used_quantity=2,
			old_available_quantity=8,
			new_total_incoming_quantity=11,
			new_total_used_quantity=2,
			new_available_quantity=9,
			recorded_by=self.supervisor,
		)

		self.client.force_login(self.central_admin)
		response = self.client.get(self._history_url_central_admin())
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'TXN-READ')

	def test_supervisor_can_correct_within_48_hours(self):
		self.client.force_login(self.supervisor)
		payload = self._base_payload()
		payload.update({'reference_code': 'TXN-CORR-1', 'movement_type': 'INCOMING', 'quantity': '5', 'variant': ''})
		self.client.post(self._create_url(self.single_product), payload)

		movement = StockMovementLine.objects.get(batch__reference_code='TXN-CORR-1')
		response = self.client.post(
			self._correct_url_supervisor(movement),
			{
				'reference_code': 'TXN-CORR-1A',
				'corrected_quantity': '3',
				'correction_reason': 'Correct incoming quantity',
			},
		)

		self.assertRedirects(response, self._history_url_supervisor())
		self.single_product.refresh_from_db()
		self.assertEqual(self.single_product.total_incoming_quantity, 13)
		self.assertEqual(self.single_product.total_used_quantity, 2)
		self.assertEqual(self.single_product.universal_available_quantity, 11)

		correction = StockMovementLine.objects.get(corrects_movement=movement)
		self.assertEqual(correction.correction_type, 'CORRECTION')
		self.assertEqual(correction.quantity, 3)
		self.assertEqual(correction.movement_type, 'INCOMING')

	def test_supervisor_cannot_correct_after_48_hours(self):
		self.client.force_login(self.supervisor)
		payload = self._base_payload()
		payload.update({'reference_code': 'TXN-CORR-2', 'movement_type': 'INCOMING', 'quantity': '4', 'variant': ''})
		self.client.post(self._create_url(self.single_product), payload)

		movement = StockMovementLine.objects.get(batch__reference_code='TXN-CORR-2')
		StockMovementLine.objects.filter(id=movement.id).update(created_at=timezone.now() - timedelta(hours=49))
		movement.refresh_from_db()

		response = self.client.post(
			self._correct_url_supervisor(movement),
			{
				'reference_code': 'TXN-CORR-2A',
				'corrected_quantity': '2',
				'correction_reason': 'Late correction',
			},
		)

		self.assertRedirects(response, self._history_url_supervisor())
		self.assertFalse(StockMovementLine.objects.filter(corrects_movement=movement).exists())

	def test_central_admin_can_correct_after_48_hours(self):
		self.client.force_login(self.supervisor)
		payload = self._base_payload()
		payload.update({'reference_code': 'TXN-CORR-3', 'movement_type': 'INCOMING', 'quantity': '6', 'variant': ''})
		self.client.post(self._create_url(self.single_product), payload)

		movement = StockMovementLine.objects.get(batch__reference_code='TXN-CORR-3')
		StockMovementLine.objects.filter(id=movement.id).update(created_at=timezone.now() - timedelta(hours=49))

		self.client.force_login(self.central_admin)
		response = self.client.post(
			self._correct_url_central_admin(movement),
			{
				'reference_code': 'TXN-CORR-3A',
				'corrected_quantity': '2',
				'correction_reason': 'Admin correction after 48 hours',
			},
		)

		self.assertRedirects(response, self._history_url_central_admin())
		self.single_product.refresh_from_db()
		self.assertEqual(self.single_product.total_incoming_quantity, 12)
		self.assertTrue(StockMovementLine.objects.filter(corrects_movement=movement, correction_type='CORRECTION').exists())

	def test_outgoing_correction_updates_used_quantity(self):
		self.client.force_login(self.supervisor)
		payload = self._base_payload()
		payload.update({'reference_code': 'TXN-CORR-4', 'movement_type': 'OUTGOING', 'quantity': '3', 'variant': ''})
		self.client.post(self._create_url(self.single_product), payload)

		movement = StockMovementLine.objects.get(batch__reference_code='TXN-CORR-4')
		response = self.client.post(
			self._correct_url_supervisor(movement),
			{
				'reference_code': 'TXN-CORR-4A',
				'corrected_quantity': '1',
				'correction_reason': 'Used quantity corrected',
			},
		)

		self.assertRedirects(response, self._history_url_supervisor())
		self.single_product.refresh_from_db()
		self.assertEqual(self.single_product.total_incoming_quantity, 10)
		self.assertEqual(self.single_product.total_used_quantity, 3)
		self.assertEqual(self.single_product.universal_available_quantity, 7)


class SupervisorInventoryDashboardTests(TestCase):
	def setUp(self):
		self.org = Organization.objects.create(name='Supervisor Org')
		self.other_org = Organization.objects.create(name='Other Org')

		self.supervisor_user = User.objects.create_user(
			email='supervisor@example.com',
			password='password123',
			phone_number='+15555550125',
			user_type='supervisor',
			organization=self.org,
		)

		self.central_admin_user = User.objects.create_user(
			email='admin2@example.com',
			password='password123',
			phone_number='+15555550126',
			user_type='central_admin',
			organization=self.org,
		)

		self.assigned_warehouse = Warehouse.objects.create(name='Assigned Warehouse', location='HQ A', org=self.org)
		self.unassigned_warehouse = Warehouse.objects.create(name='Unassigned Warehouse', location='HQ B', org=self.org)
		self.cross_org_warehouse = Warehouse.objects.create(name='Cross Org Warehouse', location='HQ C', org=self.other_org)

		self.supervisor_user.warehouses.add(self.assigned_warehouse)

		self.category = Category.objects.create(name='Sup Category', org=self.org)
		self.brand = Brand.objects.create(name='Sup Brand', org=self.org)
		Product.objects.create(
			name='Assigned Product 1',
			description='A',
			type='SINGLE_VARIANT',
			unit='PIECES',
			org=self.org,
			warehouse=self.assigned_warehouse,
			category=self.category,
			brand=self.brand,
			total_incoming_quantity=10,
			total_used_quantity=2,
			universal_available_quantity=8,
		)
		Product.objects.create(
			name='Assigned Product 2',
			description='B',
			type='SINGLE_VARIANT',
			unit='PIECES',
			org=self.org,
			warehouse=self.assigned_warehouse,
			category=self.category,
			total_incoming_quantity=5,
			total_used_quantity=5,
			universal_available_quantity=0,
		)
		Product.objects.create(
			name='Unassigned Product',
			description='C',
			type='SINGLE_VARIANT',
			unit='PIECES',
			org=self.org,
			warehouse=self.unassigned_warehouse,
			total_incoming_quantity=20,
			total_used_quantity=3,
			universal_available_quantity=17,
		)

	def _dashboard_url(self):
		return reverse('inventory:supervisor:inventory_dashboard')

	def _warehouse_detail_url(self, warehouse):
		return reverse('inventory:supervisor:warehouse_detail', kwargs={'slug': warehouse.slug})

	def _warehouse_products_url(self, warehouse):
		return reverse('inventory:supervisor:warehouse_products', kwargs={'slug': warehouse.slug})

	def _create_room_url(self, warehouse):
		return reverse('inventory:supervisor:create_room', kwargs={'slug': warehouse.slug})

	def _create_bucket_url(self, warehouse, room):
		return reverse('inventory:supervisor:create_bucket', kwargs={'slug': warehouse.slug, 'room_slug': room.slug})

	def test_supervisor_inventory_dashboard_lists_only_assigned_warehouses(self):
		self.client.force_login(self.supervisor_user)
		response = self.client.get(self._dashboard_url())

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, self.assigned_warehouse.name)
		self.assertNotContains(response, self.unassigned_warehouse.name)
		self.assertNotContains(response, self.cross_org_warehouse.name)

	def test_non_supervisor_cannot_access_supervisor_inventory_dashboard(self):
		self.client.force_login(self.central_admin_user)
		response = self.client.get(self._dashboard_url())

		self.assertRedirects(response, reverse('core:login'))

	def test_supervisor_warehouse_detail_shows_stats_and_recent_items(self):
		self.client.force_login(self.supervisor_user)
		response = self.client.get(self._warehouse_detail_url(self.assigned_warehouse))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Recent Items')
		self.assertContains(response, 'Total Products')
		self.assertContains(response, 'Assigned Product 1')
		self.assertContains(response, 'Assigned Product 2')
		self.assertNotContains(response, 'Unassigned Product')

	def test_supervisor_cannot_access_unassigned_warehouse_detail(self):
		self.client.force_login(self.supervisor_user)
		response = self.client.get(self._warehouse_detail_url(self.unassigned_warehouse))

		self.assertEqual(response.status_code, 404)

	def test_supervisor_can_create_room_in_assigned_warehouse(self):
		self.client.force_login(self.supervisor_user)
		response = self.client.post(self._create_room_url(self.assigned_warehouse), {'name': 'New Room'})

		self.assertRedirects(response, self._warehouse_detail_url(self.assigned_warehouse))
		self.assertTrue(Room.objects.filter(warehouse=self.assigned_warehouse, name='New Room').exists())

	def test_supervisor_cannot_create_room_in_unassigned_warehouse(self):
		self.client.force_login(self.supervisor_user)
		response = self.client.post(self._create_room_url(self.unassigned_warehouse), {'name': 'Blocked Room'})

		self.assertEqual(response.status_code, 404)
		self.assertFalse(Room.objects.filter(warehouse=self.unassigned_warehouse, name='Blocked Room').exists())

	def test_supervisor_can_create_bucket_in_room_of_assigned_warehouse(self):
		room = Room.objects.create(name='Supervisor Room', warehouse=self.assigned_warehouse)
		self.client.force_login(self.supervisor_user)
		response = self.client.post(self._create_bucket_url(self.assigned_warehouse, room), {'name': 'Bucket 1'})

		self.assertRedirects(response, self._warehouse_detail_url(self.assigned_warehouse))
		self.assertTrue(Bucket.objects.filter(room=room, name='Bucket 1').exists())

	def test_supervisor_can_view_all_products_page_for_assigned_warehouse(self):
		self.client.force_login(self.supervisor_user)
		response = self.client.get(self._warehouse_products_url(self.assigned_warehouse))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'All Products in')
		self.assertContains(response, 'Assigned Product 1')
		self.assertContains(response, 'Assigned Product 2')
		self.assertNotContains(response, 'Unassigned Product')


class SupervisorInventoryBrandCategoryManagementTests(TestCase):
	def setUp(self):
		self.org = Organization.objects.create(name='Supervisor Manage Org')
		self.other_org = Organization.objects.create(name='Supervisor Manage Other Org')

		self.supervisor_user = User.objects.create_user(
			email='supervisor-manage@example.com',
			password='password123',
			phone_number='+15555550128',
			user_type='supervisor',
			organization=self.org,
		)

		self.central_admin_user = User.objects.create_user(
			email='central-admin-manage@example.com',
			password='password123',
			phone_number='+15555550129',
			user_type='central_admin',
			organization=self.org,
		)

		self.own_category = Category.objects.create(name='Own Category', org=self.org)
		self.other_category = Category.objects.create(name='Other Category', org=self.other_org)
		self.own_brand = Brand.objects.create(name='Own Brand', org=self.org)
		self.other_brand = Brand.objects.create(name='Other Brand', org=self.other_org)

	def _dashboard_url(self):
		return reverse('inventory:supervisor:inventory_dashboard')

	def _category_list_url(self):
		return reverse('inventory:supervisor:category_list')

	def _create_category_url(self):
		return reverse('inventory:supervisor:create_category')

	def _edit_category_url(self, category):
		return reverse('inventory:supervisor:edit_category', kwargs={'slug': category.slug})

	def _delete_category_url(self, category):
		return reverse('inventory:supervisor:delete_category', kwargs={'slug': category.slug})

	def _brand_list_url(self):
		return reverse('inventory:supervisor:brand_list')

	def _create_brand_url(self):
		return reverse('inventory:supervisor:create_brand')

	def _edit_brand_url(self, brand):
		return reverse('inventory:supervisor:edit_brand', kwargs={'slug': brand.slug})

	def _delete_brand_url(self, brand):
		return reverse('inventory:supervisor:delete_brand', kwargs={'slug': brand.slug})

	def test_supervisor_list_views_show_only_own_org_records(self):
		self.client.force_login(self.supervisor_user)

		category_response = self.client.get(self._category_list_url())
		brand_response = self.client.get(self._brand_list_url())

		self.assertEqual(category_response.status_code, 200)
		self.assertContains(category_response, self.own_category.name)
		self.assertNotContains(category_response, self.other_category.name)

		self.assertEqual(brand_response.status_code, 200)
		self.assertContains(brand_response, self.own_brand.name)
		self.assertNotContains(brand_response, self.other_brand.name)

	def test_supervisor_can_create_category_and_brand_for_own_org(self):
		self.client.force_login(self.supervisor_user)

		category_response = self.client.post(
			self._create_category_url(),
			{'name': 'Created Category', 'description': 'Created by supervisor'},
		)
		brand_response = self.client.post(
			self._create_brand_url(),
			{'name': 'Created Brand', 'description': 'Created by supervisor'},
		)

		self.assertRedirects(category_response, self._category_list_url())
		self.assertRedirects(brand_response, self._brand_list_url())

		created_category = Category.objects.get(name='Created Category')
		created_brand = Brand.objects.get(name='Created Brand')
		self.assertEqual(created_category.org, self.org)
		self.assertEqual(created_brand.org, self.org)

	def test_supervisor_can_edit_own_category_and_brand(self):
		self.client.force_login(self.supervisor_user)

		category_response = self.client.post(
			self._edit_category_url(self.own_category),
			{'name': 'Own Category Updated', 'description': 'Updated category'},
		)
		brand_response = self.client.post(
			self._edit_brand_url(self.own_brand),
			{'name': 'Own Brand Updated', 'description': 'Updated brand'},
		)

		self.assertRedirects(category_response, self._category_list_url())
		self.assertRedirects(brand_response, self._brand_list_url())

		self.own_category.refresh_from_db()
		self.own_brand.refresh_from_db()
		self.assertEqual(self.own_category.name, 'Own Category Updated')
		self.assertEqual(self.own_brand.name, 'Own Brand Updated')

	def test_supervisor_cannot_edit_cross_org_category_or_brand(self):
		self.client.force_login(self.supervisor_user)

		category_response = self.client.post(
			self._edit_category_url(self.other_category),
			{'name': 'Blocked Category Update', 'description': 'Denied'},
		)
		brand_response = self.client.post(
			self._edit_brand_url(self.other_brand),
			{'name': 'Blocked Brand Update', 'description': 'Denied'},
		)

		self.assertEqual(category_response.status_code, 404)
		self.assertEqual(brand_response.status_code, 404)

	def test_supervisor_can_delete_own_category_and_brand(self):
		self.client.force_login(self.supervisor_user)

		category_response = self.client.post(self._delete_category_url(self.own_category))
		brand_response = self.client.post(self._delete_brand_url(self.own_brand))

		self.assertRedirects(category_response, self._category_list_url())
		self.assertRedirects(brand_response, self._brand_list_url())
		self.assertFalse(Category.objects.filter(id=self.own_category.id).exists())
		self.assertFalse(Brand.objects.filter(id=self.own_brand.id).exists())

	def test_supervisor_cannot_delete_cross_org_category_or_brand(self):
		self.client.force_login(self.supervisor_user)

		category_response = self.client.post(self._delete_category_url(self.other_category))
		brand_response = self.client.post(self._delete_brand_url(self.other_brand))

		self.assertEqual(category_response.status_code, 404)
		self.assertEqual(brand_response.status_code, 404)
		self.assertTrue(Category.objects.filter(id=self.other_category.id).exists())
		self.assertTrue(Brand.objects.filter(id=self.other_brand.id).exists())

	def test_non_supervisor_cannot_access_supervisor_brand_or_category_management(self):
		self.client.force_login(self.central_admin_user)

		category_response = self.client.get(self._category_list_url())
		brand_response = self.client.get(self._brand_list_url())

		self.assertEqual(category_response.status_code, 302)
		self.assertEqual(brand_response.status_code, 302)
		self.assertTrue(category_response.url.startswith(reverse('core:login')))
		self.assertTrue(brand_response.url.startswith(reverse('core:login')))

	def test_dashboard_shows_category_and_brand_links(self):
		self.client.force_login(self.supervisor_user)
		response = self.client.get(self._dashboard_url())

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, self._category_list_url())
		self.assertContains(response, self._brand_list_url())

class SupervisorProductParityTests(TestCase):
	def setUp(self):
		self.org = Organization.objects.create(name='Supervisor Product Org')
		self.supervisor_user = User.objects.create_user(
			email='supervisor-product@example.com',
			password='password123',
			phone_number='+15555550127',
			user_type='supervisor',
			organization=self.org,
		)

		self.assigned_warehouse = Warehouse.objects.create(name='Assigned Product Warehouse', location='HQ', org=self.org)
		self.unassigned_warehouse = Warehouse.objects.create(name='Unassigned Product Warehouse', location='HQ 2', org=self.org)
		self.supervisor_user.warehouses.add(self.assigned_warehouse)

		self.category = Category.objects.create(name='Supervisor Category', org=self.org)
		self.brand = Brand.objects.create(name='Supervisor Brand', org=self.org)
		self.room_a = Room.objects.create(name='Room A', warehouse=self.assigned_warehouse)
		self.room_b = Room.objects.create(name='Room B', warehouse=self.assigned_warehouse)
		self.bucket_a = Bucket.objects.create(name='Bucket A', room=self.room_a)
		self.bucket_b = Bucket.objects.create(name='Bucket B', room=self.room_b)

		self.multi_product = Product.objects.create(
			name='Supervisor Multi Product',
			description='Multi',
			type='MULTI_VARIANT',
			unit='PIECES',
			org=self.org,
			warehouse=self.assigned_warehouse,
			category=self.category,
		)
		self.single_product = Product.objects.create(
			name='Supervisor Single Product',
			description='Single',
			type='SINGLE_VARIANT',
			unit='PIECES',
			org=self.org,
			warehouse=self.assigned_warehouse,
			category=self.category,
			brand=self.brand,
			total_incoming_quantity=10,
			total_used_quantity=2,
			universal_available_quantity=8,
		)

		self.client.force_login(self.supervisor_user)

	def _step1_url(self, warehouse):
		return reverse('inventory:supervisor:product_create_step1', kwargs={'slug': warehouse.slug})

	def _step2_url(self, warehouse):
		return reverse('inventory:supervisor:product_create_step2', kwargs={'slug': warehouse.slug})

	def _step3_url(self, warehouse):
		return reverse('inventory:supervisor:product_create_step3_single', kwargs={'slug': warehouse.slug})

	def _products_url(self, warehouse):
		return reverse('inventory:supervisor:warehouse_products', kwargs={'slug': warehouse.slug})

	def _detail_url(self, product):
		return reverse('inventory:supervisor:product_detail', kwargs={'slug': product.warehouse.slug, 'product_slug': product.slug})

	def _create_variant_url(self):
		return reverse(
			'inventory:supervisor:product_variant_create',
			kwargs={'slug': self.assigned_warehouse.slug, 'product_slug': self.multi_product.slug},
		)

	def _assign_room_url(self, product):
		return reverse('inventory:supervisor:product_assign_room', kwargs={'slug': product.warehouse.slug, 'product_slug': product.slug})

	def _assign_bucket_url(self, product):
		return reverse('inventory:supervisor:product_assign_bucket', kwargs={'slug': product.warehouse.slug, 'product_slug': product.slug})

	def _assign_brand_url(self, product):
		return reverse('inventory:supervisor:product_assign_brand', kwargs={'slug': product.warehouse.slug, 'product_slug': product.slug})

	def _product_edit_url(self, product):
		return reverse('inventory:supervisor:product_edit', kwargs={'slug': product.warehouse.slug, 'product_slug': product.slug})

	def _product_delete_url(self, product):
		return reverse('inventory:supervisor:product_delete', kwargs={'slug': product.warehouse.slug, 'product_slug': product.slug})

	def _product_convert_url(self, product):
		return reverse('inventory:supervisor:product_convert_type', kwargs={'slug': product.warehouse.slug, 'product_slug': product.slug})

	def test_supervisor_multi_variant_creates_product_after_step2(self):
		response_step1 = self.client.post(
			self._step1_url(self.assigned_warehouse),
			{
				'name': 'Supervisor Paint',
				'description': 'Wall paint',
				'category': self.category.id,
				'unit': 'BOTTLES',
			},
		)
		self.assertRedirects(response_step1, self._step2_url(self.assigned_warehouse))

		response_step2 = self.client.post(self._step2_url(self.assigned_warehouse), {'type': 'MULTI_VARIANT'})
		self.assertRedirects(response_step2, self._products_url(self.assigned_warehouse))

		product = Product.objects.get(name='Supervisor Paint')
		self.assertEqual(product.type, 'MULTI_VARIANT')
		self.assertEqual(product.warehouse, self.assigned_warehouse)
		self.assertEqual(product.org, self.org)

	def test_supervisor_single_variant_creates_product_and_size(self):
		self.client.post(
			self._step1_url(self.assigned_warehouse),
			{
				'name': 'Supervisor Cement',
				'description': 'Cement product',
				'category': self.category.id,
				'unit': 'BAGS',
			},
		)
		self.client.post(self._step2_url(self.assigned_warehouse), {'type': 'SINGLE_VARIANT'})

		response_step3 = self.client.post(
			self._step3_url(self.assigned_warehouse),
			{
				'total_quantity': 25,
				'size_name': '50kg',
				'brand': self.brand.id,
			},
		)
		self.assertRedirects(response_step3, self._products_url(self.assigned_warehouse))

		product = Product.objects.get(name='Supervisor Cement')
		self.assertEqual(product.type, 'SINGLE_VARIANT')
		self.assertEqual(product.total_incoming_quantity, 25)
		self.assertEqual(product.universal_available_quantity, 25)

		size = Size.objects.get(product=product, org=self.org, name='50kg')
		self.assertIsNone(size.variant)

	def test_supervisor_cannot_access_product_create_for_unassigned_warehouse(self):
		response = self.client.get(self._step1_url(self.unassigned_warehouse))
		self.assertEqual(response.status_code, 404)

	def test_supervisor_product_detail_only_for_assigned_warehouse(self):
		response_assigned = self.client.get(self._detail_url(self.single_product))
		self.assertEqual(response_assigned.status_code, 200)

		unassigned_product = Product.objects.create(
			name='Unassigned Product Hidden',
			type='SINGLE_VARIANT',
			unit='PIECES',
			org=self.org,
			warehouse=self.unassigned_warehouse,
		)
		response_unassigned = self.client.get(
			reverse(
				'inventory:supervisor:product_detail',
				kwargs={'slug': self.unassigned_warehouse.slug, 'product_slug': unassigned_product.slug},
			)
		)
		self.assertEqual(response_unassigned.status_code, 404)

	def test_supervisor_create_variant_updates_multi_product_totals(self):
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
		self.assertEqual(variant.universal_available_quantity, 70)
		self.assertEqual(self.multi_product.total_incoming_quantity, 100)
		self.assertEqual(self.multi_product.total_used_quantity, 30)
		self.assertEqual(self.multi_product.universal_available_quantity, 70)

	def test_supervisor_assign_room_and_bucket_updates_product(self):
		response_room = self.client.post(self._assign_room_url(self.single_product), {'room': self.room_a.id})
		self.assertRedirects(response_room, self._detail_url(self.single_product))

		response_bucket = self.client.post(self._assign_bucket_url(self.single_product), {'bucket': self.bucket_a.id})
		self.assertRedirects(response_bucket, self._detail_url(self.single_product))

		self.single_product.refresh_from_db()
		self.assertEqual(self.single_product.bucket, self.bucket_a)
		self.assertEqual(self.single_product.room, self.room_a)

	def test_supervisor_assign_brand_only_updates_single_variant_product(self):
		new_brand = Brand.objects.create(name='Supervisor New Brand', org=self.org)

		single_response = self.client.post(self._assign_brand_url(self.single_product), {'brand': new_brand.id})
		self.assertRedirects(single_response, self._detail_url(self.single_product))
		self.single_product.refresh_from_db()
		self.assertEqual(self.single_product.brand, new_brand)

		multi_response = self.client.post(self._assign_brand_url(self.multi_product), {'brand': new_brand.id})
		self.assertRedirects(multi_response, self._detail_url(self.multi_product))
		self.multi_product.refresh_from_db()
		self.assertIsNone(self.multi_product.brand)

	def test_supervisor_product_list_shows_variant_brands_and_add_product_action(self):
		second_brand = Brand.objects.create(name='Supervisor Second Brand', org=self.org)
		Variant.objects.create(
			name='Variant Brand One',
			unit='PIECES',
			product=self.multi_product,
			brand=self.brand,
			total_incoming_quantity=10,
			total_used_quantity=2,
			universal_available_quantity=8,
		)
		Variant.objects.create(
			name='Variant Brand Two',
			unit='PIECES',
			product=self.multi_product,
			brand=second_brand,
			total_incoming_quantity=8,
			total_used_quantity=1,
			universal_available_quantity=7,
		)

		response = self.client.get(self._products_url(self.assigned_warehouse))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Add Product')
		self.assertContains(response, 'Supervisor Brand')
		self.assertContains(response, 'Supervisor Second Brand')

	def test_supervisor_can_edit_product_details(self):
		response = self.client.post(
			self._product_edit_url(self.single_product),
			{
				'name': 'Supervisor Single Updated',
				'description': 'Updated by supervisor',
				'category': self.category.id,
				'unit': 'BAGS',
			},
		)

		self.assertRedirects(response, self._detail_url(self.single_product))
		self.single_product.refresh_from_db()
		self.assertEqual(self.single_product.name, 'Supervisor Single Updated')
		self.assertEqual(self.single_product.unit, 'BAGS')

	def test_supervisor_delete_blocked_when_stock_history_exists(self):
		batch = StockMovementBatch.objects.create(
			org=self.org,
			warehouse=self.assigned_warehouse,
			recorded_by=self.supervisor_user,
			reference_code='SUP-DEL-BLOCK-001',
			notes='Delete blocked',
		)
		StockMovementLine.objects.create(
			batch=batch,
			org=self.org,
			warehouse=self.assigned_warehouse,
			product=self.single_product,
			variant=None,
			target_type='PRODUCT',
			movement_type='INCOMING',
			quantity=1,
			notes='History exists',
			old_total_incoming_quantity=10,
			old_total_used_quantity=2,
			old_available_quantity=8,
			new_total_incoming_quantity=11,
			new_total_used_quantity=2,
			new_available_quantity=9,
			recorded_by=self.supervisor_user,
		)

		response = self.client.post(
			self._product_delete_url(self.single_product),
			{'deletion_reason': 'History exists but this product should be removed'},
		)
		self.assertRedirects(response, self._detail_url(self.single_product))
		self.assertTrue(Product.objects.filter(id=self.single_product.id).exists())
		self.assertTrue(
			ProductDeletionRequest.objects.filter(
				product=self.single_product,
				status='pending',
				request_reason='History exists but this product should be removed',
			).exists()
		)

	def test_supervisor_delete_with_history_requires_reason(self):
		batch = StockMovementBatch.objects.create(
			org=self.org,
			warehouse=self.assigned_warehouse,
			recorded_by=self.supervisor_user,
			reference_code='SUP-DEL-BLOCK-002',
			notes='Delete reason required',
		)
		StockMovementLine.objects.create(
			batch=batch,
			org=self.org,
			warehouse=self.assigned_warehouse,
			product=self.single_product,
			variant=None,
			target_type='PRODUCT',
			movement_type='INCOMING',
			quantity=1,
			notes='History exists',
			old_total_incoming_quantity=10,
			old_total_used_quantity=2,
			old_available_quantity=8,
			new_total_incoming_quantity=11,
			new_total_used_quantity=2,
			new_available_quantity=9,
			recorded_by=self.supervisor_user,
		)

		response = self.client.post(self._product_delete_url(self.single_product), {'deletion_reason': ''})
		self.assertRedirects(response, self._detail_url(self.single_product))
		self.assertTrue(Product.objects.filter(id=self.single_product.id).exists())
		self.assertFalse(ProductDeletionRequest.objects.filter(product=self.single_product).exists())

	def test_supervisor_direct_delete_without_history_still_succeeds(self):
		response = self.client.post(self._product_delete_url(self.single_product))

		self.assertRedirects(response, self._products_url(self.assigned_warehouse))
		self.assertFalse(Product.objects.filter(id=self.single_product.id).exists())

	def test_supervisor_cannot_create_duplicate_pending_deletion_requests(self):
		batch = StockMovementBatch.objects.create(
			org=self.org,
			warehouse=self.assigned_warehouse,
			recorded_by=self.supervisor_user,
			reference_code='SUP-DEL-BLOCK-003',
			notes='Duplicate request guard',
		)
		StockMovementLine.objects.create(
			batch=batch,
			org=self.org,
			warehouse=self.assigned_warehouse,
			product=self.single_product,
			variant=None,
			target_type='PRODUCT',
			movement_type='INCOMING',
			quantity=1,
			notes='History exists',
			old_total_incoming_quantity=10,
			old_total_used_quantity=2,
			old_available_quantity=8,
			new_total_incoming_quantity=11,
			new_total_used_quantity=2,
			new_available_quantity=9,
			recorded_by=self.supervisor_user,
		)

		ProductDeletionRequest.objects.create(
			product=self.single_product,
			product_name=self.single_product.name,
			product_code=self.single_product.product_code,
			org=self.org,
			warehouse=self.assigned_warehouse,
			requested_by=self.supervisor_user,
			request_reason='Existing request',
		)

		response = self.client.post(
			self._product_delete_url(self.single_product),
			{'deletion_reason': 'Second request should be blocked'},
		)

		self.assertRedirects(response, self._detail_url(self.single_product))
		self.assertEqual(ProductDeletionRequest.objects.filter(product=self.single_product, status='pending').count(), 1)

	def test_supervisor_convert_single_to_multi_clears_brand(self):
		response = self.client.post(
			self._product_convert_url(self.single_product),
			{'target_type': 'MULTI_VARIANT'},
		)

		self.assertRedirects(response, self._detail_url(self.single_product))
		self.single_product.refresh_from_db()
		self.assertEqual(self.single_product.type, 'MULTI_VARIANT')
		self.assertIsNone(self.single_product.brand)

	def test_supervisor_convert_multi_to_single_uses_selected_variant(self):
		selected_variant = Variant.objects.create(
			name='Supervisor Selected Variant',
			unit='PIECES',
			product=self.multi_product,
			brand=self.brand,
			total_incoming_quantity=40,
			total_used_quantity=5,
			universal_available_quantity=35,
		)
		Variant.objects.create(
			name='Supervisor Other Variant',
			unit='PIECES',
			product=self.multi_product,
			total_incoming_quantity=10,
			total_used_quantity=2,
			universal_available_quantity=8,
		)

		response = self.client.post(
			self._product_convert_url(self.multi_product),
			{
				'target_type': 'SINGLE_VARIANT',
				'source_variant': selected_variant.id,
			},
		)

		self.assertRedirects(response, self._detail_url(self.multi_product))
		self.multi_product.refresh_from_db()
		self.assertEqual(self.multi_product.type, 'SINGLE_VARIANT')
		self.assertEqual(self.multi_product.brand, self.brand)
		self.assertEqual(self.multi_product.total_incoming_quantity, 40)
		self.assertEqual(self.multi_product.total_used_quantity, 5)
		self.assertFalse(self.multi_product.variants.exists())

	def test_supervisor_cannot_edit_product_in_unassigned_warehouse(self):
		unassigned_product = Product.objects.create(
			name='Unassigned Product Supervisor Edit',
			type='SINGLE_VARIANT',
			unit='PIECES',
			org=self.org,
			warehouse=self.unassigned_warehouse,
		)

		response = self.client.post(
			self._product_edit_url(unassigned_product),
			{
				'name': 'Should Not Update',
				'description': 'Denied',
				'category': '',
				'unit': 'PIECES',
			},
		)

		self.assertEqual(response.status_code, 404)

