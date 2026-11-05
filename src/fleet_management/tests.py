from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from django.utils.timezone import now

from core.models import Organization
from fleet_management.models import Vehicle, Workshop, VehicleExpense, VehicleActivity
from ticket_management.models import Ticket


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


class CentralAdminWorkshopViewTests(TestCase):
	def setUp(self):
		self.org = Organization.objects.create(name='Org One')
		self.other_org = Organization.objects.create(name='Org Two')

		self.central_admin = User.objects.create_user(
			phone_number='+10000000031',
			email='workshop-admin@example.com',
			password='AdminPass123!',
			user_type='central_admin',
			organization=self.org,
			first_name='Central',
			last_name='Admin',
		)
		self.maintainer = User.objects.create_user(
			phone_number='+10000000032',
			email='maintainer@example.com',
			password='MaintainerPass123!',
			user_type='maintainer',
			organization=self.org,
		)
		self.supervisor = User.objects.create_user(
			phone_number='+10000000033',
			email='supervisor@example.com',
			password='SupervisorPass123!',
			user_type='supervisor',
			organization=self.org,
		)
		self.driver = User.objects.create_user(
			phone_number='+10000000034',
			email='driver@example.com',
			password='DriverPass123!',
			user_type='driver',
			organization=self.org,
		)
		self.other_org_maintainer = User.objects.create_user(
			phone_number='+10000000035',
			email='other-maintainer@example.com',
			password='MaintainerPass123!',
			user_type='maintainer',
			organization=self.other_org,
		)

		self.workshop = Workshop.objects.create(
			org=self.org,
			name='Main Workshop',
		)
		self.workshop.incharges.set([self.maintainer])
		self.other_workshop = Workshop.objects.create(
			org=self.other_org,
			name='Other Workshop',
		)

	def test_workshop_list_is_org_scoped(self):
		self.client.force_login(self.central_admin)

		response = self.client.get(reverse('fleet_management:central_admin:workshop_list'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, self.workshop.name)
		self.assertNotContains(response, self.other_workshop.name)

	def test_workshop_create_sets_org_and_allows_valid_incharges(self):
		self.client.force_login(self.central_admin)

		response = self.client.post(
			reverse('fleet_management:central_admin:workshop_create'),
			{
				'name': 'North Workshop',
				'incharges': [self.maintainer.pk, self.supervisor.pk],
				'notes': 'North side workshop',
			},
		)

		self.assertEqual(response.status_code, 302)
		created = Workshop.objects.get(org=self.org, name='North Workshop')
		self.assertEqual(created.name, 'North Workshop')
		self.assertEqual(created.incharges.count(), 2)

	def test_workshop_create_blocks_invalid_incharge_role(self):
		self.client.force_login(self.central_admin)

		response = self.client.post(
			reverse('fleet_management:central_admin:workshop_create'),
			{
				'name': 'Invalid Role Workshop',
				'incharges': [self.driver.pk],
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Select a valid choice')
		self.assertFalse(Workshop.objects.filter(org=self.org, name='Invalid Role Workshop').exists())

	def test_workshop_create_blocks_other_org_incharge(self):
		self.client.force_login(self.central_admin)

		response = self.client.post(
			reverse('fleet_management:central_admin:workshop_create'),
			{
				'name': 'Cross Org Workshop',
				'incharges': [self.other_org_maintainer.pk],
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Select a valid choice')
		self.assertFalse(Workshop.objects.filter(org=self.org, name='Cross Org Workshop').exists())

	def test_workshop_detail_blocks_other_org_workshop(self):
		self.client.force_login(self.central_admin)

		response = self.client.get(
			reverse('fleet_management:central_admin:workshop_detail', kwargs={'slug': self.other_workshop.slug})
		)

		self.assertEqual(response.status_code, 404)

	def test_workshop_update_and_delete(self):
		self.client.force_login(self.central_admin)

		update_response = self.client.post(
			reverse('fleet_management:central_admin:workshop_update', kwargs={'slug': self.workshop.slug}),
			{
				'name': 'Main Workshop Updated',
				'incharges': [self.supervisor.pk],
				'notes': 'Updated',
			},
		)

		self.assertEqual(update_response.status_code, 302)
		self.workshop.refresh_from_db()
		self.assertEqual(self.workshop.name, 'Main Workshop Updated')
		self.assertEqual(self.workshop.incharges.count(), 1)

		delete_response = self.client.post(
			reverse('fleet_management:central_admin:workshop_delete', kwargs={'slug': self.workshop.slug})
		)
		self.assertEqual(delete_response.status_code, 302)
		self.assertFalse(Workshop.objects.filter(pk=self.workshop.pk).exists())


class TransportInchargeWorkshopViewTests(TestCase):
	def setUp(self):
		self.org = Organization.objects.create(name='Org One')
		self.other_org = Organization.objects.create(name='Org Two')

		self.transport_incharge = User.objects.create_user(
			phone_number='+10000000041',
			email='transport-ws@example.com',
			password='TransportPass123!',
			user_type='transport_incharge',
			organization=self.org,
		)
		self.maintainer = User.objects.create_user(
			phone_number='+10000000042',
			email='maintainer-ws@example.com',
			password='MaintainerPass123!',
			user_type='maintainer',
			organization=self.org,
		)

		self.workshop = Workshop.objects.create(
			org=self.org,
			name='Transport Workshop',
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
		self.other_workshop = Workshop.objects.create(
			org=self.other_org,
			name='Other Transport Workshop',
		)

	def test_workshop_sidebar_tab_is_present(self):
		self.client.force_login(self.transport_incharge)

		response = self.client.get(reverse('fleet_management:transport_incharge:workshop_list'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Workshops')

	def test_workshop_list_is_org_scoped(self):
		self.client.force_login(self.transport_incharge)

		response = self.client.get(reverse('fleet_management:transport_incharge:workshop_list'))

		self.assertContains(response, self.workshop.name)
		self.assertNotContains(response, self.other_workshop.name)

	def test_transport_incharge_can_create_update_delete_workshop(self):
		self.client.force_login(self.transport_incharge)

		create_response = self.client.post(
			reverse('fleet_management:transport_incharge:workshop_create'),
			{
				'name': 'Created Workshop',
				'incharges': [self.maintainer.pk],
				'notes': 'Created by transport incharge',
			},
		)
		self.assertEqual(create_response.status_code, 302)
		created = Workshop.objects.get(org=self.org, name='Created Workshop')

		update_response = self.client.post(
			reverse('fleet_management:transport_incharge:workshop_update', kwargs={'slug': created.slug}),
			{
				'name': 'Created Workshop Updated',
				'incharges': [self.maintainer.pk],
				'notes': 'Updated by transport incharge',
			},
		)
		self.assertEqual(update_response.status_code, 302)

		delete_response = self.client.post(
			reverse('fleet_management:transport_incharge:workshop_delete', kwargs={'slug': created.slug})
		)
		self.assertEqual(delete_response.status_code, 302)
		self.assertFalse(Workshop.objects.filter(pk=created.pk).exists())

	def test_workshop_detail_lists_reported_tickets(self):
		self.client.force_login(self.transport_incharge)

		ticket= Ticket.objects.create(
			title='Workshop Ticket',
			description='Reported to workshop',
			reporter=self.transport_incharge,
			org=self.org,
			vehicle=self.vehicle,
			workshop=self.workshop,
		)

		response = self.client.get(
			reverse('fleet_management:transport_incharge:workshop_detail', kwargs={'slug': self.workshop.slug})
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Reported Tickets')
		self.assertContains(response, ticket.title)
		self.assertContains(response, reverse('ticket_management:transport_incharge:ticket_detail', kwargs={'ticket_slug': ticket.slug}))


class TransportInchargeExpenseViewTests(TestCase):
	"""Tests for expense CRUD operations and activity logging."""

	def setUp(self):
		self.org = Organization.objects.create(name='Org One')
		self.other_org = Organization.objects.create(name='Org Two')

		self.transport_incharge = User.objects.create_user(
			phone_number='+10000000051',
			email='transport-expense@example.com',
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

	def test_expense_create_success(self):
		"""Test creating an expense successfully."""
		self.client.force_login(self.transport_incharge)

		response = self.client.post(
			reverse('fleet_management:transport_incharge:expense_create'),
			{
				'vehicle': self.vehicle.pk,
				'amount': '50.00',
				'expense_date': now().date(),
				'category': VehicleExpense.CATEGORY_FUEL,
				'description': 'Fuel for delivery',
			},
		)

		self.assertEqual(response.status_code, 302)
		created_expense = VehicleExpense.objects.get(description='Fuel for delivery')
		self.assertEqual(created_expense.vehicle, self.vehicle)
		self.assertEqual(created_expense.amount, 50)
		self.assertEqual(created_expense.created_by, self.transport_incharge)

	def test_expense_create_logs_activity(self):
		"""Test that creating an expense logs a VehicleActivity."""
		self.client.force_login(self.transport_incharge)

		initial_count = VehicleActivity.objects.count()

		self.client.post(
			reverse('fleet_management:transport_incharge:expense_create'),
			{
				'vehicle': self.vehicle.pk,
				'amount': '75.50',
				'expense_date': now().date(),
				'category': VehicleExpense.CATEGORY_MAINTENANCE,
				'description': 'Oil change',
			},
		)

		# Check that activity was logged
		self.assertEqual(VehicleActivity.objects.count(), initial_count + 1)
		activity = VehicleActivity.objects.latest('timestamp')
		self.assertEqual(activity.action, VehicleActivity.ACTION_EXPENSE_CREATED)
		self.assertEqual(activity.user, self.transport_incharge)
		self.assertEqual(activity.vehicle, self.vehicle)
		self.assertEqual(activity.org, self.org)

	def test_expense_list_is_org_scoped(self):
		"""Test that expense list only shows expenses from the user's org."""
		self.client.force_login(self.transport_incharge)

		other_vehicle = Vehicle.objects.create(
			org=self.other_org,
			registration_number='XYZ 789',
			vehicle_type=Vehicle.TYPE_VAN,
			manufacturer='Nissan',
			model='Urvan',
		)

		# Create expenses in both orgs
		expense1 = VehicleExpense.objects.create(
			vehicle=self.vehicle,
			amount=50,
			expense_date=now().date(),
			category=VehicleExpense.CATEGORY_FUEL,
			description='Org 1 fuel',
			created_by=self.transport_incharge,
		)
		expense2 = VehicleExpense.objects.create(
			vehicle=other_vehicle,
			amount=75,
			expense_date=now().date(),
			category=VehicleExpense.CATEGORY_MAINTENANCE,
			description='Org 2 maintenance',
			created_by=None,
		)

		response = self.client.get(reverse('fleet_management:transport_incharge:expense_list'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, expense1.description)
		self.assertNotContains(response, expense2.description)
