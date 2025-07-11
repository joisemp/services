from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal

User = get_user_model()

from .models import (
    VehicleModel, Vehicle, Component, VehicleComponent,
    MaintenanceRecord, Document, ComponentInspection
)


class VehicleModelTestCase(TestCase):
    def setUp(self):
        self.vehicle_model = VehicleModel.objects.create(
            make='Toyota',
            model='Camry',
            year=2020,
            fuel_type='gasoline'
        )

    def test_vehicle_model_creation(self):
        self.assertEqual(self.vehicle_model.make, 'Toyota')
        self.assertEqual(self.vehicle_model.model, 'Camry')
        self.assertEqual(self.vehicle_model.year, 2020)
        self.assertEqual(self.vehicle_model.fuel_type, 'gasoline')

    def test_vehicle_model_string_representation(self):
        expected = "2020 Toyota Camry"
        self.assertEqual(str(self.vehicle_model), expected)


class VehicleTestCase(TestCase):
    def setUp(self):
        self.vehicle_model = VehicleModel.objects.create(
            make='Honda',
            model='Civic',
            year=2019,
            fuel_type='gasoline'
        )
        self.vehicle = Vehicle.objects.create(
            vehicle_model=self.vehicle_model,
            license_plate='ABC123',
            vin='1HGCM82633A123456',
            vehicle_type='car',
            status='active',
            purchase_date=date(2020, 1, 1),
            current_mileage=50000,
            color='White',
            purchase_price=Decimal('25000.00')
        )

    def test_vehicle_creation(self):
        self.assertEqual(self.vehicle.license_plate, 'ABC123')
        self.assertEqual(self.vehicle.vin, '1HGCM82633A123456')
        self.assertEqual(self.vehicle.vehicle_type, 'car')
        self.assertEqual(self.vehicle.status, 'active')
        self.assertEqual(self.vehicle.current_mileage, 50000)

    def test_vehicle_string_representation(self):
        expected = "ABC123 - 2019 Honda Civic"
        self.assertEqual(str(self.vehicle), expected)

    def test_vehicle_absolute_url(self):
        expected_url = reverse('transportation:vehicle_detail', kwargs={'pk': self.vehicle.pk})
        self.assertEqual(self.vehicle.get_absolute_url(), expected_url)


class ComponentTestCase(TestCase):
    def setUp(self):
        self.component = Component.objects.create(
            name='Engine',
            component_type='engine',
            description='Main engine assembly'
        )

    def test_component_creation(self):
        self.assertEqual(self.component.name, 'Engine')
        self.assertEqual(self.component.component_type, 'engine')
        self.assertEqual(self.component.description, 'Main engine assembly')

    def test_component_string_representation(self):
        self.assertEqual(str(self.component), 'Engine')


class MaintenanceRecordTestCase(TestCase):
    def setUp(self):
        self.vehicle_model = VehicleModel.objects.create(
            make='Ford',
            model='F-150',
            year=2021,
            fuel_type='gasoline'
        )
        self.vehicle = Vehicle.objects.create(
            vehicle_model=self.vehicle_model,
            license_plate='XYZ789',
            vin='1FTFW1ET5DKE12345',
            vehicle_type='truck',
            status='active',
            purchase_date=date(2021, 1, 1),
            current_mileage=30000,
            color='Blue',
            purchase_price=Decimal('35000.00')
        )
        self.maintenance_record = MaintenanceRecord.objects.create(
            vehicle=self.vehicle,
            service_type='oil_change',
            service_date=date(2023, 6, 15),
            current_mileage=28000,
            priority='medium',
            status='completed',
            cost=Decimal('75.50'),
            service_provider='Quick Lube',
            description='Regular oil change'
        )

    def test_maintenance_record_creation(self):
        self.assertEqual(self.maintenance_record.vehicle, self.vehicle)
        self.assertEqual(self.maintenance_record.service_type, 'oil_change')
        self.assertEqual(self.maintenance_record.priority, 'medium')
        self.assertEqual(self.maintenance_record.status, 'completed')
        self.assertEqual(self.maintenance_record.cost, Decimal('75.50'))

    def test_maintenance_record_string_representation(self):
        expected = "XYZ789 - oil_change (2023-06-15)"
        self.assertEqual(str(self.maintenance_record), expected)


class TransportationViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')

        # Create test data
        self.vehicle_model = VehicleModel.objects.create(
            make='Toyota',
            model='Camry',
            year=2020,
            fuel_type='gasoline'
        )
        self.vehicle = Vehicle.objects.create(
            vehicle_model=self.vehicle_model,
            license_plate='TEST123',
            vin='1HGCM82633A654321',
            vehicle_type='car',
            status='active',
            purchase_date=date(2020, 1, 1),
            current_mileage=45000,
            color='Silver',
            purchase_price=Decimal('28000.00')
        )

    def test_dashboard_view(self):
        response = self.client.get(reverse('transportation:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Transportation Dashboard')

    def test_vehicle_list_view(self):
        response = self.client.get(reverse('transportation:vehicle_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Vehicle Management')
        self.assertContains(response, 'TEST123')

    def test_vehicle_detail_view(self):
        response = self.client.get(
            reverse('transportation:vehicle_detail', kwargs={'pk': self.vehicle.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TEST123')
        self.assertContains(response, '2020 Toyota Camry')

    def test_vehicle_create_view(self):
        response = self.client.get(reverse('transportation:vehicle_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add New Vehicle')

    def test_vehicle_edit_view(self):
        response = self.client.get(
            reverse('transportation:vehicle_edit', kwargs={'pk': self.vehicle.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Edit Vehicle')

    def test_maintenance_list_view(self):
        response = self.client.get(reverse('transportation:maintenance_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Maintenance Records')

    def test_maintenance_create_view(self):
        response = self.client.get(reverse('transportation:maintenance_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add Maintenance Record')

    def test_component_list_view(self):
        response = self.client.get(reverse('transportation:component_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Component Management')

    def test_reports_view(self):
        response = self.client.get(reverse('transportation:reports'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Transportation Reports')

    def test_vehicle_create_post(self):
        data = {
            'vehicle_model': self.vehicle_model.pk,
            'license_plate': 'NEW123',
            'vin': '1HGCM82633A111111',
            'vehicle_type': 'car',
            'status': 'active',
            'purchase_date': '2023-01-01',
            'current_mileage': 10000,
            'color': 'Red',
            'purchase_price': '30000.00'
        }
        response = self.client.post(reverse('transportation:vehicle_create'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful creation
        self.assertTrue(Vehicle.objects.filter(license_plate='NEW123').exists())

    def test_maintenance_create_post(self):
        data = {
            'vehicle': self.vehicle.pk,
            'service_type': 'oil_change',
            'service_date': '2023-07-01',
            'current_mileage': 46000,
            'priority': 'low',
            'status': 'completed',
            'cost': '65.00',
            'service_provider': 'Test Garage',
            'description': 'Test oil change'
        }
        response = self.client.post(reverse('transportation:maintenance_create'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful creation
        self.assertTrue(MaintenanceRecord.objects.filter(description='Test oil change').exists())


class VehicleComponentTestCase(TestCase):
    def setUp(self):
        self.vehicle_model = VehicleModel.objects.create(
            make='BMW',
            model='X5',
            year=2020,
            fuel_type='gasoline'
        )
        self.vehicle = Vehicle.objects.create(
            vehicle_model=self.vehicle_model,
            license_plate='BMW123',
            vin='5UXCR6C0XL9123456',
            vehicle_type='car',
            status='active',
            purchase_date=date(2020, 1, 1),
            current_mileage=35000,
            color='Black',
            purchase_price=Decimal('60000.00')
        )
        self.component = Component.objects.create(
            name='Brake System',
            component_type='brake',
            description='Complete brake system'
        )
        self.vehicle_component = VehicleComponent.objects.create(
            vehicle=self.vehicle,
            component=self.component,
            installation_date=date(2020, 1, 15),
            status='active'
        )

    def test_vehicle_component_creation(self):
        self.assertEqual(self.vehicle_component.vehicle, self.vehicle)
        self.assertEqual(self.vehicle_component.component, self.component)
        self.assertEqual(self.vehicle_component.status, 'active')

    def test_vehicle_component_string_representation(self):
        expected = "BMW123 - Brake System"
        self.assertEqual(str(self.vehicle_component), expected)


class DocumentTestCase(TestCase):
    def setUp(self):
        self.vehicle_model = VehicleModel.objects.create(
            make='Tesla',
            model='Model 3',
            year=2022,
            fuel_type='electric'
        )
        self.vehicle = Vehicle.objects.create(
            vehicle_model=self.vehicle_model,
            license_plate='TESLA1',
            vin='5YJ3E1EA4JF123456',
            vehicle_type='car',
            status='active',
            purchase_date=date(2022, 1, 1),
            current_mileage=15000,
            color='White',
            purchase_price=Decimal('45000.00')
        )
        self.document = Document.objects.create(
            vehicle=self.vehicle,
            document_type='registration',
            name='Vehicle Registration',
            description='Official vehicle registration document',
            upload_date=date(2023, 1, 1),
            expiry_date=date(2024, 1, 1)
        )

    def test_document_creation(self):
        self.assertEqual(self.document.vehicle, self.vehicle)
        self.assertEqual(self.document.document_type, 'registration')
        self.assertEqual(self.document.name, 'Vehicle Registration')

    def test_document_string_representation(self):
        expected = "TESLA1 - Vehicle Registration"
        self.assertEqual(str(self.document), expected)


class ComponentInspectionTestCase(TestCase):
    def setUp(self):
        self.vehicle_model = VehicleModel.objects.create(
            make='Mercedes',
            model='Sprinter',
            year=2019,
            fuel_type='diesel'
        )
        self.vehicle = Vehicle.objects.create(
            vehicle_model=self.vehicle_model,
            license_plate='MB2019',
            vin='WD3PD5CC3JP123456',
            vehicle_type='bus',
            status='active',
            purchase_date=date(2019, 1, 1),
            current_mileage=75000,
            color='White',
            purchase_price=Decimal('55000.00')
        )
        self.component = Component.objects.create(
            name='Suspension',
            component_type='suspension',
            description='Front and rear suspension'
        )
        self.vehicle_component = VehicleComponent.objects.create(
            vehicle=self.vehicle,
            component=self.component,
            installation_date=date(2019, 1, 15),
            status='active'
        )
        self.inspection = ComponentInspection.objects.create(
            vehicle_component=self.vehicle_component,
            inspection_date=date(2023, 6, 1),
            status='passed',
            notes='Suspension system in good condition',
            next_inspection_date=date(2024, 6, 1)
        )

    def test_inspection_creation(self):
        self.assertEqual(self.inspection.vehicle_component, self.vehicle_component)
        self.assertEqual(self.inspection.status, 'passed')
        self.assertEqual(self.inspection.notes, 'Suspension system in good condition')

    def test_inspection_string_representation(self):
        expected = "MB2019 - Suspension (2023-06-01)"
        self.assertEqual(str(self.inspection), expected)
