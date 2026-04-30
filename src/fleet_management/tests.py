from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from core.models import Organization
from fleet_management.models import Vehicle


User = get_user_model()


class CentralAdminVehicleViewTests(TestCase):
	def setUp(self):
		self.org = Organization.objects.create(name='Org One')
		self.other_org = Organization.objects.create(name='Org Two')

		self.central_admin = User.objects.create_user(
			phone_number='+10000000011',
			email='admin1@example.com',
			password='AdminPass123!',
			user_type='central_admin',
			organization=self.org,
			first_name='Central',
			last_name='Admin',
		)
		self.other_admin = User.objects.create_user(
			phone_number='+10000000012',
			email='admin2@example.com',
			password='AdminPass123!',
			user_type='central_admin',
			organization=self.other_org,
			first_name='Other',
			last_name='Admin',
		)

		self.vehicle = Vehicle.objects.create(
			org=self.org,
			registration_number='ABC 123',
			vehicle_type=Vehicle.TYPE_CAR,
			manufacturer='Toyota',
			model='Corolla',
			year=2022,
			status=Vehicle.STATUS_ACTIVE,
		)
		self.other_vehicle = Vehicle.objects.create(
			org=self.other_org,
			registration_number='XYZ 789',
			vehicle_type=Vehicle.TYPE_VAN,
			manufacturer='Nissan',
			model='Urvan',
			year=2021,
			status=Vehicle.STATUS_IN_MAINTENANCE,
		)

	def test_vehicle_list_is_org_scoped(self):
		self.client.force_login(self.central_admin)

		response = self.client.get(reverse('fleet_management:central_admin:vehicle_list'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, self.vehicle.registration_number)
		self.assertNotContains(response, self.other_vehicle.registration_number)
		self.assertEqual(response.context['vehicle_summary']['total_vehicles'], 1)

	def test_vehicle_detail_blocks_other_org_vehicle(self):
		self.client.force_login(self.central_admin)

		response = self.client.get(
			reverse('fleet_management:central_admin:vehicle_detail', kwargs={'slug': self.other_vehicle.slug})
		)

		self.assertEqual(response.status_code, 404)

	def test_vehicle_create_sets_organization(self):
		self.client.force_login(self.central_admin)

		response = self.client.post(
			reverse('fleet_management:central_admin:vehicle_create'),
			{
				'registration_number': 'new 456',
				'vehicle_type': Vehicle.TYPE_TRUCK,
				'manufacturer': 'Isuzu',
				'model': 'NPR',
				'year': 2020,
				'status': Vehicle.STATUS_ACTIVE,
				'notes': 'Assigned to central admin transport pool',
			},
		)

		self.assertEqual(response.status_code, 302)
		created_vehicle = Vehicle.objects.get(registration_number='NEW 456')
		self.assertEqual(created_vehicle.org, self.org)
		self.assertTrue(created_vehicle.slug)

	def test_vehicle_update_is_org_scoped(self):
		self.client.force_login(self.central_admin)

		response = self.client.post(
			reverse('fleet_management:central_admin:vehicle_update', kwargs={'slug': self.vehicle.slug}),
			{
				'registration_number': self.vehicle.registration_number,
				'vehicle_type': Vehicle.TYPE_CAR,
				'manufacturer': 'Toyota',
				'model': 'Corolla Cross',
				'year': 2023,
				'status': Vehicle.STATUS_ACTIVE,
				'notes': 'Updated model',
			},
		)

		self.assertEqual(response.status_code, 302)
		self.vehicle.refresh_from_db()
		self.assertEqual(self.vehicle.model, 'Corolla Cross')

	def test_vehicle_delete_is_org_scoped(self):
		self.client.force_login(self.central_admin)

		response = self.client.post(
			reverse('fleet_management:central_admin:vehicle_delete', kwargs={'slug': self.vehicle.slug})
		)

		self.assertEqual(response.status_code, 302)
		self.assertFalse(Vehicle.objects.filter(pk=self.vehicle.pk).exists())

	def test_other_org_admin_sees_their_own_vehicle(self):
		self.client.force_login(self.other_admin)

		response = self.client.get(reverse('fleet_management:central_admin:vehicle_list'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, self.other_vehicle.registration_number)
		self.assertNotContains(response, self.vehicle.registration_number)


class TransportInchargeVehicleViewTests(TestCase):
	def setUp(self):
		self.org = Organization.objects.create(name='Org One')

		self.transport_incharge = User.objects.create_user(
			phone_number='+10000000021',
			email='transport@example.com',
			password='TransportPass123!',
			user_type='transport_incharge',
			organization=self.org,
			first_name='Transport',
			last_name='Incharge',
		)

		self.vehicle = Vehicle.objects.create(
			org=self.org,
			registration_number='ABC 123',
			vehicle_type=Vehicle.TYPE_CAR,
			manufacturer='Toyota',
			model='Corolla',
			year=2022,
			status=Vehicle.STATUS_ACTIVE,
		)

	def test_fleet_list_is_available(self):
		self.client.force_login(self.transport_incharge)

		response = self.client.get(reverse('fleet_management:transport_incharge:fleet_list'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Fleets')
		self.assertContains(response, self.vehicle.registration_number)

	def test_fleet_sidebar_tab_is_present(self):
		self.client.force_login(self.transport_incharge)

		response = self.client.get(reverse('fleet_management:transport_incharge:fleet_list'))

		self.assertContains(response, 'Fleets')

	def test_vehicle_create_sets_organization(self):
		self.client.force_login(self.transport_incharge)

		response = self.client.post(
			reverse('fleet_management:transport_incharge:vehicle_create'),
			{
				'registration_number': 'new 555',
				'vehicle_type': Vehicle.TYPE_BUS,
				'manufacturer': 'Mercedes',
				'model': 'Sprinter',
				'year': 2020,
				'status': Vehicle.STATUS_ACTIVE,
				'notes': 'Transport incharge vehicle',
			},
		)

		self.assertEqual(response.status_code, 302)
		created_vehicle = Vehicle.objects.get(registration_number='NEW 555')
		self.assertEqual(created_vehicle.org, self.org)

	def test_vehicle_detail_is_available(self):
		self.client.force_login(self.transport_incharge)

		response = self.client.get(
			reverse('fleet_management:transport_incharge:vehicle_detail', kwargs={'slug': self.vehicle.slug})
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, self.vehicle.registration_number)

	def test_vehicle_update_is_available(self):
		self.client.force_login(self.transport_incharge)

		response = self.client.post(
			reverse('fleet_management:transport_incharge:vehicle_update', kwargs={'slug': self.vehicle.slug}),
			{
				'registration_number': self.vehicle.registration_number,
				'vehicle_type': Vehicle.TYPE_CAR,
				'manufacturer': 'Toyota',
				'model': 'Corolla Cross',
				'year': 2023,
				'status': Vehicle.STATUS_ACTIVE,
				'notes': 'Updated model',
			},
		)

		self.assertEqual(response.status_code, 302)
		self.vehicle.refresh_from_db()
		self.assertEqual(self.vehicle.model, 'Corolla Cross')

	def test_vehicle_delete_is_available(self):
		self.client.force_login(self.transport_incharge)

		response = self.client.post(
			reverse('fleet_management:transport_incharge:vehicle_delete', kwargs={'slug': self.vehicle.slug})
		)

		self.assertEqual(response.status_code, 302)
		self.assertFalse(Vehicle.objects.filter(pk=self.vehicle.pk).exists())
