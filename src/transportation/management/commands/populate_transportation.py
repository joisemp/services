from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from transportation.models import (
    VehicleModel, Vehicle, Component, VehicleComponent, 
    MaintenanceRecord, Document, ComponentInspection
)
from decimal import Decimal
import random

class Command(BaseCommand):
    help = 'Populate the transportation app with sample data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before populating',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            ComponentInspection.objects.all().delete()
            Document.objects.all().delete()
            MaintenanceRecord.objects.all().delete()
            VehicleComponent.objects.all().delete()
            Component.objects.all().delete()
            Vehicle.objects.all().delete()
            VehicleModel.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Data cleared successfully'))

        self.stdout.write('Creating sample data...')
        
        # Create Vehicle Models
        self.create_vehicle_models()
        
        # Create Components
        self.create_components()
        
        # Create Vehicles
        self.create_vehicles()
        
        # Create Vehicle Components
        self.create_vehicle_components()
        
        # Create Maintenance Records
        self.create_maintenance_records()
        
        # Create Documents
        self.create_documents()
        
        # Create Component Inspections
        self.create_component_inspections()
        
        self.stdout.write(self.style.SUCCESS('Sample data created successfully'))

    def create_vehicle_models(self):
        models_data = [
            {'make': 'Toyota', 'model': 'Camry', 'year': 2020, 'fuel_type': 'gasoline'},
            {'make': 'Honda', 'model': 'Civic', 'year': 2019, 'fuel_type': 'gasoline'},
            {'make': 'Ford', 'model': 'F-150', 'year': 2021, 'fuel_type': 'gasoline'},
            {'make': 'Tesla', 'model': 'Model 3', 'year': 2022, 'fuel_type': 'electric'},
            {'make': 'BMW', 'model': 'X5', 'year': 2020, 'fuel_type': 'gasoline'},
            {'make': 'Mercedes', 'model': 'Sprinter', 'year': 2019, 'fuel_type': 'diesel'},
            {'make': 'Chevrolet', 'model': 'Bolt', 'year': 2021, 'fuel_type': 'electric'},
            {'make': 'Nissan', 'model': 'Altima', 'year': 2020, 'fuel_type': 'gasoline'},
        ]
        
        for model_data in models_data:
            VehicleModel.objects.get_or_create(**model_data)
        
        self.stdout.write(f'Created {len(models_data)} vehicle models')

    def create_components(self):
        components_data = [
            {'name': 'Engine', 'component_type': 'engine', 'description': 'Main engine assembly'},
            {'name': 'Transmission', 'component_type': 'transmission', 'description': 'Automatic transmission'},
            {'name': 'Brake System', 'component_type': 'brake', 'description': 'Complete brake system'},
            {'name': 'Steering System', 'component_type': 'steering', 'description': 'Power steering system'},
            {'name': 'Suspension', 'component_type': 'suspension', 'description': 'Front and rear suspension'},
            {'name': 'Air Conditioning', 'component_type': 'electrical', 'description': 'HVAC system'},
            {'name': 'Battery', 'component_type': 'electrical', 'description': 'Main vehicle battery'},
            {'name': 'Alternator', 'component_type': 'electrical', 'description': 'Charging system'},
            {'name': 'Radiator', 'component_type': 'cooling', 'description': 'Engine cooling system'},
            {'name': 'Fuel System', 'component_type': 'fuel', 'description': 'Fuel delivery system'},
        ]
        
        for comp_data in components_data:
            Component.objects.get_or_create(**comp_data)
        
        self.stdout.write(f'Created {len(components_data)} components')

    def create_vehicles(self):
        vehicle_models = VehicleModel.objects.all()
        vehicle_types = ['car', 'truck', 'bus', 'motorcycle', 'other']
        statuses = ['active', 'maintenance', 'inactive', 'retired']
        
        for i in range(1, 16):  # Create 15 vehicles
            vehicle = Vehicle.objects.create(
                vehicle_model=random.choice(vehicle_models),
                license_plate=f'ABC{i:03d}',
                vin=f'1HGCM82633A{i:06d}',
                vehicle_type=random.choice(vehicle_types),
                status=random.choice(statuses),
                purchase_date=timezone.now().date() - timedelta(days=random.randint(365, 1825)),
                current_mileage=random.randint(10000, 150000),
                color=random.choice(['White', 'Black', 'Silver', 'Red', 'Blue', 'Gray']),
                purchase_price=Decimal(random.randint(15000, 50000)),
                is_active=True,
                notes=f'Sample vehicle {i} for testing purposes'
            )
        
        self.stdout.write(f'Created {Vehicle.objects.count()} vehicles')

    def create_vehicle_components(self):
        vehicles = Vehicle.objects.all()
        components = Component.objects.all()
        
        for vehicle in vehicles:
            # Add 3-7 random components to each vehicle
            selected_components = random.sample(list(components), random.randint(3, 7))
            
            for component in selected_components:
                VehicleComponent.objects.create(
                    vehicle=vehicle,
                    component=component,
                    installation_date=vehicle.purchase_date + timedelta(days=random.randint(0, 365)),
                    status=random.choice(['active', 'inactive', 'maintenance']),
                    notes=f'Installed on {vehicle.license_plate}'
                )
        
        self.stdout.write(f'Created {VehicleComponent.objects.count()} vehicle components')

    def create_maintenance_records(self):
        vehicles = Vehicle.objects.all()
        service_types = ['oil_change', 'tire_rotation', 'brake_inspection', 'transmission', 'major_service']
        priorities = ['low', 'medium', 'high']
        statuses = ['scheduled', 'in_progress', 'completed', 'cancelled']
        
        for vehicle in vehicles:
            # Create 2-5 maintenance records per vehicle
            for i in range(random.randint(2, 5)):
                service_date = timezone.now().date() - timedelta(days=random.randint(0, 730))
                
                MaintenanceRecord.objects.create(
                    vehicle=vehicle,
                    service_type=random.choice(service_types),
                    service_date=service_date,
                    current_mileage=vehicle.current_mileage - random.randint(0, 50000),
                    priority=random.choice(priorities),
                    status=random.choice(statuses),
                    cost=Decimal(random.randint(50, 1500)),
                    service_provider=random.choice(['Quick Lube', 'Dealership', 'Local Garage', 'Fleet Services']),
                    description=f'Routine maintenance for {vehicle.license_plate}',
                    notes=f'Maintenance performed on {service_date}'
                )
        
        self.stdout.write(f'Created {MaintenanceRecord.objects.count()} maintenance records')

    def create_documents(self):
        vehicles = Vehicle.objects.all()
        document_types = ['registration', 'insurance', 'inspection', 'manual', 'receipt', 'other']
        
        for vehicle in vehicles:
            # Create 1-3 documents per vehicle
            for i in range(random.randint(1, 3)):
                Document.objects.create(
                    vehicle=vehicle,
                    document_type=random.choice(document_types),
                    name=f'{vehicle.license_plate} - Document {i+1}',
                    description=f'Sample document for {vehicle.license_plate}',
                    upload_date=timezone.now().date() - timedelta(days=random.randint(0, 365)),
                    expiry_date=timezone.now().date() + timedelta(days=random.randint(30, 730)),
                    is_active=True
                )
        
        self.stdout.write(f'Created {Document.objects.count()} documents')

    def create_component_inspections(self):
        vehicle_components = VehicleComponent.objects.all()
        statuses = ['passed', 'failed', 'pending']
        
        for vc in vehicle_components:
            # Create 1-3 inspections per component
            for i in range(random.randint(1, 3)):
                ComponentInspection.objects.create(
                    vehicle_component=vc,
                    inspection_date=timezone.now().date() - timedelta(days=random.randint(0, 365)),
                    status=random.choice(statuses),
                    notes=f'Inspection of {vc.component.name} on {vc.vehicle.license_plate}',
                    next_inspection_date=timezone.now().date() + timedelta(days=random.randint(30, 365))
                )
        
        self.stdout.write(f'Created {ComponentInspection.objects.count()} component inspections')
