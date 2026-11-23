from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from core.models import User, Organization, Space
from fleet_management.models import Vehicle, Workshop
from .models import Ticket, TicketActivity
from .forms import TicketForm


class VehicleTicketIntegrationTests(TestCase):
    """Test vehicle-related ticket creation and management"""
    
    def setUp(self):
        """Set up test data"""
        # Create organizations
        self.org1 = Organization.objects.create(name="Org One")
        self.org2 = Organization.objects.create(name="Org Two")
        
        # Create spaces
        self.space1 = Space.objects.create(name="Space 1", org=self.org1)
        
        # Create users
        self.central_admin = User.objects.create_user(
            email="admin@org1.com",
            phone_number="+1234567890",
            password="testpass123",
            user_type="central_admin",
            organization=self.org1,
            is_active=True
        )
        self.supervisor = User.objects.create_user(
            email="supervisor@org1.com",
            phone_number="+1234567891",
            password="testpass123",
            user_type="supervisor",
            organization=self.org1,
            is_active=True
        )
        self.central_admin_org2 = User.objects.create_user(
            email="admin@org2.com",
            phone_number="+9999999999",
            password="testpass123",
            user_type="central_admin",
            organization=self.org2,
            is_active=True
        )
        self.transport_incharge = User.objects.create_user(
            email="transport@org1.com",
            phone_number="+1234567892",
            password="testpass123",
            user_type="transport_incharge",
            organization=self.org1,
            is_active=True
        )
        
        # Create vehicles
        self.vehicle1 = Vehicle.objects.create(
            org=self.org1,
            registration_number="ABC123",
            vehicle_type="car",
            status="active"
        )
        self.vehicle2 = Vehicle.objects.create(
            org=self.org2,
            registration_number="XYZ789",
            vehicle_type="van",
            status="active"
        )
        
        # Create workshop
        self.workshop = Workshop.objects.create(
            org=self.org1,
            name="Central Workshop"
        )
        self.workshop.incharges.add(self.supervisor)
        
        self.client = Client()
    
    def test_vehicle_ticket_creation_with_vehicle_fk(self):
        """Test that a ticket can be created with a vehicle FK"""
        ticket= Ticket.objects.create(
            title="Engine Problem",
            description="Engine is making noise",
            reporter=self.central_admin,
            org=self.org1,
            vehicle=self.vehicle1
        )
        
        self.assertIsNotNone(ticket.vehicle)
        self.assertEqual(ticket.vehicle, self.vehicle1)
        self.assertEqual(ticket.org, self.org1)
    
    def test_vehicle_status_updated_to_maintenance_on_ticket_create(self):
        """Test that vehicle status is NOT changed when a ticket is created"""
        # Verify initial status
        self.assertEqual(self.vehicle1.status, "active")

        # Create ticket with vehicle
        ticket= Ticket.objects.create(
            title="Brake Ticket",
            description="Brakes not working",
            reporter=self.central_admin,
            org=self.org1,
            vehicle=self.vehicle1
        )

        # Refresh vehicle from DB and check status remains unchanged
        self.vehicle1.refresh_from_db()
        self.assertEqual(self.vehicle1.status, "active")
    
    def test_vehicle_activity_logged_on_ticket_create(self):
        """Test that a vehicle-related ticket creates a reporting activity (no status change)"""
        ticket= Ticket.objects.create(
            title="Suspension Problem",
            description="Suspension needs repair",
            reporter=self.central_admin,
            org=self.org1,
            vehicle=self.vehicle1
        )

        # Check that activity was created with the 'vehicle_ticket_reported' type
        activity = TicketActivity.objects.filter(
            ticket=ticket,
            activity_type="vehicle_ticket_reported"
        ).first()
        self.assertIsNotNone(activity)
        self.assertIn(self.vehicle1.registration_number, activity.description)
    
    def test_issue_form_filters_vehicles_by_organization(self):
        """Test that TicketForm restricts vehicle choices to user's organization"""
        form = TicketForm(current_user=self.central_admin)
        
        # Get vehicle queryset from form
        vehicle_choices = list(form.fields['vehicle'].queryset)
        
        # Should contain vehicle1 (same org) but not vehicle2 (different org)
        self.assertIn(self.vehicle1, vehicle_choices)
        self.assertNotIn(self.vehicle2, vehicle_choices)
    
    def test_issue_form_vehicle_field_optional(self):
        """Test that vehicle field is optional in TicketForm"""
        form_data = {
            'title': 'General Ticket',
            'description': 'No specific vehicle',
            'priority': 'medium',
            'space': '',
            'vehicle': '',
            'voice': ''
        }
        form = TicketForm(data=form_data, current_user=self.central_admin)
        self.assertTrue(form.is_valid())
    
    def test_issue_without_vehicle(self):
        """Test that issues can still be created without a vehicle"""
        ticket= Ticket.objects.create(
            title="General Maintenance",
            description="Regular checkup",
            reporter=self.central_admin,
            org=self.org1,
            vehicle=None
        )
        
        self.assertIsNone(ticket.vehicle)
        self.assertIsNotNone(ticket.org)
    
    def test_vehicle_ticket_list_view_filters_by_vehicle(self):
        """Test that VehicleTicketListView returns only issues for the given vehicle"""
        # Create multiple issues
        issue1 = Ticket.objects.create(
            title="Ticket 1",
            description="First ticket",
            reporter=self.central_admin,
            org=self.org1,
            vehicle=self.vehicle1
        )
        issue2 = Ticket.objects.create(
            title="Ticket 2",
            description="Second ticket",
            reporter=self.central_admin,
            org=self.org1,
            vehicle=self.vehicle1
        )
        issue3 = Ticket.objects.create(
            title="Ticket 3",
            description="Third ticket",
            reporter=self.central_admin,
            org=self.org1,
            vehicle=None
        )
        
        self.client.login(email="admin@org1.com", password="testpass123")
        response = self.client.get(
            reverse('ticket_management:central_admin:vehicle_ticket_list',
                   kwargs={'vehicle_slug': self.vehicle1.slug})
        )
        
        self.assertEqual(response.status_code, 200)
        context_issues = response.context['tickets']
        self.assertIn(issue1, context_issues)
        self.assertIn(issue2, context_issues)
        self.assertNotIn(issue3, context_issues)
    
    def test_vehicle_ticket_list_view_org_scoping(self):
        """Test that VehicleTicketListView respects multi-tenant org boundaries"""
        self.client.login(email="admin@org2.com", password="testpass123")
        
        # Try to access vehicle from org1 as user from org2
        response = self.client.get(
            reverse('ticket_management:central_admin:vehicle_ticket_list',
                   kwargs={'vehicle_slug': self.vehicle1.slug})
        )
        
        # Should be redirected (not allowed to view other org's vehicles)
        self.assertEqual(response.status_code, 302)
    
    def test_ticket_create_view_prefills_vehicle_from_query_param(self):
        """Test that TicketCreateView prefills vehicle from ?vehicle=<slug> query param"""
        self.client.login(email="admin@org1.com", password="testpass123")
        
        response = self.client.get(
            reverse('ticket_management:central_admin:ticket_create')
            + f'?vehicle={self.vehicle1.slug}'
        )
        
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertEqual(form.initial.get('vehicle'), self.vehicle1.pk)

    def test_ticket_create_view_shows_workshop_only_for_vehicle_tickets(self):
        """Test that the workshop field only appears when the create page is opened from a vehicle"""
        self.client.login(email="admin@org1.com", password="testpass123")

        response_without_vehicle = self.client.get(reverse('ticket_management:central_admin:ticket_create'))
        self.assertEqual(response_without_vehicle.status_code, 200)
        self.assertFalse(response_without_vehicle.context['show_workshop_field'])
        self.assertNotContains(response_without_vehicle, 'Workshop (Optional)')

        response_with_vehicle = self.client.get(
            reverse('ticket_management:central_admin:ticket_create') + f'?vehicle={self.vehicle1.slug}'
        )
        self.assertEqual(response_with_vehicle.status_code, 200)
        self.assertTrue(response_with_vehicle.context['show_workshop_field'])
        self.assertContains(response_with_vehicle, 'Workshop')

    def test_ticket_create_view_auto_attaches_vehicle_from_query_param(self):
        """Test that posting from a vehicle-linked create page attaches the vehicle automatically"""
        self.client.login(email="admin@org1.com", password="testpass123")

        response = self.client.post(
            reverse('ticket_management:central_admin:ticket_create') + f'?vehicle={self.vehicle1.slug}',
            {
                'title': 'Vehicle-linked ticket',
                'description': 'Created from vehicle detail',
                'priority': 'medium',
                'space': '',
                'workshop': self.workshop.pk,
                'voice': '',
            }
        )

        self.assertEqual(response.status_code, 302)
        ticket= Ticket.objects.get(title='Vehicle-linked ticket')
        self.assertEqual(ticket.vehicle, self.vehicle1)

    def test_ticket_create_view_requires_workshop_for_vehicle_tickets(self):
        """Test that workshop is required when reporting a ticket from a vehicle"""
        self.client.login(email="admin@org1.com", password="testpass123")

        response = self.client.post(
            reverse('ticket_management:central_admin:ticket_create') + f'?vehicle={self.vehicle1.slug}',
            {
                'title': 'Vehicle-linked ticket without workshop',
                'description': 'Missing workshop',
                'priority': 'medium',
                'space': '',
                'voice': '',
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'workshop', 'This field is required.')
        self.assertFalse(Ticket.objects.filter(title='Vehicle-linked ticket without workshop').exists())

    def test_transport_incharge_ticket_create_auto_attaches_vehicle_and_requires_workshop(self):
        """Test the transport incharge ticket create flow mirrors the vehicle-linked workshop behavior"""
        self.client.force_login(self.transport_incharge)

        response = self.client.post(
            reverse('ticket_management:transport_incharge:ticket_create') + f'?vehicle={self.vehicle1.slug}',
            {
                'title': 'Transport ticket',
                'description': 'Reported by transport incharge',
                'priority': 'medium',
                'space': '',
                'workshop': self.workshop.pk,
                'voice': '',
            }
        )

        self.assertEqual(response.status_code, 302)
        ticket= Ticket.objects.get(title='Transport ticket')
        self.assertEqual(ticket.vehicle, self.vehicle1)
        self.assertEqual(ticket.workshop, self.workshop)

    def test_transport_incharge_vehicle_detail_links_to_ticket_create(self):
        """Test that transport incharge vehicle detail links to the ticket create flow"""
        self.client.force_login(self.transport_incharge)
        response = self.client.get(
            reverse('fleet_management:transport_incharge:vehicle_detail', kwargs={'slug': self.vehicle1.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('ticket_management:transport_incharge:ticket_create') + f'?vehicle={self.vehicle1.slug}')
    
    def test_ticket_create_view_restricts_vehicle_queryset_by_org(self):
        """Test that TicketCreateView restricts vehicle choices to user's org"""
        self.client.login(email="admin@org1.com", password="testpass123")
        
        response = self.client.get(reverse('ticket_management:central_admin:ticket_create'))
        
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        vehicle_queryset = form.fields['vehicle'].queryset
        
        self.assertIn(self.vehicle1, vehicle_queryset)
        self.assertNotIn(self.vehicle2, vehicle_queryset)
    
    def test_ticket_detail_displays_vehicle(self):
        """Test that ticket detail page displays linked vehicle"""
        ticket= Ticket.objects.create(
            title="Windshield Ticket",
            description="Cracked windshield",
            reporter=self.central_admin,
            org=self.org1,
            vehicle=self.vehicle1
        )
        
        self.client.login(email="admin@org1.com", password="testpass123")
        response = self.client.get(
            reverse('ticket_management:central_admin:ticket_detail',
                   kwargs={'ticket_slug': ticket.slug})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.vehicle1.registration_number)

    def test_workshop_assigned_on_ticket_create(self):
        """Test that creating a ticket with workshop sets the workshop FK and it shows on detail"""
        ticket= Ticket.objects.create(
            title="Workshop Test",
            description="Report to workshop",
            reporter=self.central_admin,
            org=self.org1,
            vehicle=self.vehicle1,
            workshop=self.workshop
        )
        self.client.login(email="admin@org1.com", password="testpass123")
        response = self.client.get(reverse('ticket_management:central_admin:ticket_detail', kwargs={'ticket_slug': ticket.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.workshop.name)

    def test_workshop_transfer_view_changes_workshop(self):
        """Test transferring a ticket from one workshop to another"""
        other_workshop = Workshop.objects.create(org=self.org1, name='Other Workshop')
        ticket= Ticket.objects.create(
            title="Transfer Test",
            description="Transfer between workshops",
            reporter=self.central_admin,
            org=self.org1,
            vehicle=self.vehicle1,
            workshop=self.workshop
        )
        self.client.login(email="admin@org1.com", password="testpass123")
        response = self.client.post(
            reverse('ticket_management:central_admin:ticket_change_workshop', kwargs={'ticket_slug': ticket.slug}),
            {'workshop': other_workshop.pk}
        )
        self.assertEqual(response.status_code, 302)
        ticket.refresh_from_db()
        self.assertEqual(ticket.workshop, other_workshop)
    
    def test_vehicle_ticket_on_delete_vehicle_preserves_issue(self):
        """Test that deleting a vehicle preserves the ticket (FK with SET_NULL)"""
        ticket= Ticket.objects.create(
            title="Tire Pressure",
            description="Low tire pressure",
            reporter=self.central_admin,
            org=self.org1,
            vehicle=self.vehicle1
        )
        
        ticket_id = ticket.id
        self.vehicle1.delete()
        
        # Ticket should still exist with vehicle=None
        ticket= Ticket.objects.get(id=ticket_id)
        self.assertIsNone(ticket.vehicle)
    
    def test_org_scoped_vehicle_queryset_in_form(self):
        """Test that vehicle queryset respects organization scoping in forms"""
        # Org1 user should see org1 vehicles
        form1 = TicketForm(current_user=self.central_admin)
        vehicles_org1 = list(form1.fields['vehicle'].queryset)
        self.assertEqual(len(vehicles_org1), 1)
        self.assertEqual(vehicles_org1[0].org, self.org1)
        
        # Org2 user should see org2 vehicles
        form2 = TicketForm(current_user=self.central_admin_org2)
        vehicles_org2 = list(form2.fields['vehicle'].queryset)
        self.assertEqual(len(vehicles_org2), 1)
        self.assertEqual(vehicles_org2[0].org, self.org2)
