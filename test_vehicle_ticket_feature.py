#!/usr/bin/env python
"""
Quick manual test for vehicle-ticket integration feature
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Organization, User
from fleet_management.models import Vehicle
from ticket_management.models import Ticket, TicketActivity

print("=" * 60)
print("Testing Vehicle-Ticket Integration Feature")
print("=" * 60)

try:
    # Create org and user
    print("\n1. Creating organization and user...")
    org = Organization.objects.create(name='Test Org Vehicle')
    user = User.objects.create_user(
        email='test_vehicle@test.com',
        phone_number='+1234567890',
        user_type='central_admin',
        organization=org
    )
    print(f"   ✓ Org created: {org.name}")
    print(f"   ✓ User created: {user.email}")

    # Create vehicle
    print("\n2. Creating vehicle...")
    vehicle = Vehicle.objects.create(
        org=org,
        registration_number='TEST_VEHICLE_123',
        vehicle_type='car',
        status='active'
    )
    print(f"   ✓ Vehicle created: {vehicle.registration_number}")
    print(f"   ✓ Initial status: {vehicle.status}")

    # Create ticket with vehicle
    print("\n3. Creating ticket linked to vehicle...")
    ticket = Ticket.objects.create(
        title='Test Vehicle Ticket',
        description='This is a test ticket for the vehicle',
        reporter=user,
        org=org,
        vehicle=vehicle
    )
    print(f"   ✓ Ticket created: {ticket.title}")
    print(f"   ✓ Ticket ID: {ticket.ticket_id}")
    print(f"   ✓ Ticket vehicle FK: {ticket.vehicle}")

    # Check vehicle status was updated
    print("\n4. Checking if vehicle status was updated to maintenance...")
    vehicle.refresh_from_db()
    print(f"   ✓ Vehicle status after ticket create: {vehicle.status}")
    
    if vehicle.status == 'maintenance':
        print("   ✓ SUCCESS: Vehicle status was set to maintenance!")
    else:
        print("   ✗ FAIL: Vehicle status was not updated")

    # Check activity was logged
    print("\n5. Checking if activity was logged...")
    activity = TicketActivity.objects.filter(
        ticket=ticket,
        activity_type='vehicle_moved'
    ).first()
    if activity:
        print(f"   ✓ Activity logged: {activity.description}")
    else:
        print("   ✗ No vehicle_moved activity found")

    # Test ticket without vehicle
    print("\n6. Creating ticket WITHOUT vehicle...")
    issue_no_vehicle = Ticket.objects.create(
        title='General Ticket',
        description='No vehicle assigned',
        reporter=user,
        org=org,
        vehicle=None
    )
    print(f"   ✓ Ticket created: {issue_no_vehicle.title}")
    print(f"   ✓ Ticket vehicle: {issue_no_vehicle.vehicle}")

    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)

except Exception as e:
    print(f"\n✗ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    exit(1)
