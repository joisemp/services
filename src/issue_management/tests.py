from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from core.models import User, Organization, Space
from fleet_management.models import Vehicle, Workshop
from .models import Issue, IssueActivity
from .forms import IssueForm


class VehicleIssueIntegrationTests(TestCase):
    """Test vehicle-related issue creation and management"""
    
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
    
    def test_vehicle_issue_creation_with_vehicle_fk(self):
        """Test that an issue can be created with a vehicle FK"""
        issue = Issue.objects.create(
            title="Engine Problem",
            description="Engine is making noise",
            reporter=self.central_admin,
            org=self.org1,
            vehicle=self.vehicle1
        )
        
        self.assertIsNotNone(issue.vehicle)
        self.assertEqual(issue.vehicle, self.vehicle1)
        self.assertEqual(issue.org, self.org1)
    
    def test_vehicle_status_updated_to_maintenance_on_issue_create(self):
        """Test that vehicle status is NOT changed when an issue is created"""
        # Verify initial status
        self.assertEqual(self.vehicle1.status, "active")

        # Create issue with vehicle
        issue = Issue.objects.create(
            title="Brake Issue",
            description="Brakes not working",
            reporter=self.central_admin,
            org=self.org1,
            vehicle=self.vehicle1
        )

        # Refresh vehicle from DB and check status remains unchanged
        self.vehicle1.refresh_from_db()
        self.assertEqual(self.vehicle1.status, "active")
    
    def test_vehicle_activity_logged_on_issue_create(self):
        """Test that a vehicle-related issue creates a reporting activity (no status change)"""
        issue = Issue.objects.create(
            title="Suspension Problem",
            description="Suspension needs repair",
            reporter=self.central_admin,
            org=self.org1,
            vehicle=self.vehicle1
        )

        # Check that activity was created with the 'vehicle_issue_reported' type
        activity = IssueActivity.objects.filter(
            issue=issue,
            activity_type="vehicle_issue_reported"
        ).first()
        self.assertIsNotNone(activity)
        self.assertIn(self.vehicle1.registration_number, activity.description)
    
    def test_issue_form_filters_vehicles_by_organization(self):
        """Test that IssueForm restricts vehicle choices to user's organization"""
        form = IssueForm(current_user=self.central_admin)
        
        # Get vehicle queryset from form
        vehicle_choices = list(form.fields['vehicle'].queryset)
        
        # Should contain vehicle1 (same org) but not vehicle2 (different org)
        self.assertIn(self.vehicle1, vehicle_choices)
        self.assertNotIn(self.vehicle2, vehicle_choices)
    
    def test_issue_form_vehicle_field_optional(self):
        """Test that vehicle field is optional in IssueForm"""
        form_data = {
            'title': 'General Issue',
            'description': 'No specific vehicle',
            'priority': 'medium',
            'space': '',
            'vehicle': '',
            'voice': ''
        }
        form = IssueForm(data=form_data, current_user=self.central_admin)
        self.assertTrue(form.is_valid())
    
    def test_issue_without_vehicle(self):
        """Test that issues can still be created without a vehicle"""
        issue = Issue.objects.create(
            title="General Maintenance",
            description="Regular checkup",
            reporter=self.central_admin,
            org=self.org1,
            vehicle=None
        )
        
        self.assertIsNone(issue.vehicle)
        self.assertIsNotNone(issue.org)
    
    def test_vehicle_issue_list_view_filters_by_vehicle(self):
        """Test that VehicleIssueListView returns only issues for the given vehicle"""
        # Create multiple issues
        issue1 = Issue.objects.create(
            title="Issue 1",
            description="First issue",
            reporter=self.central_admin,
            org=self.org1,
            vehicle=self.vehicle1
        )
        issue2 = Issue.objects.create(
            title="Issue 2",
            description="Second issue",
            reporter=self.central_admin,
            org=self.org1,
            vehicle=self.vehicle1
        )
        issue3 = Issue.objects.create(
            title="Issue 3",
            description="Third issue",
            reporter=self.central_admin,
            org=self.org1,
            vehicle=None
        )
        
        self.client.login(email="admin@org1.com", password="testpass123")
        response = self.client.get(
            reverse('issue_management:central_admin:vehicle_issue_list',
                   kwargs={'vehicle_slug': self.vehicle1.slug})
        )
        
        self.assertEqual(response.status_code, 200)
        context_issues = response.context['issues']
        self.assertIn(issue1, context_issues)
        self.assertIn(issue2, context_issues)
        self.assertNotIn(issue3, context_issues)
    
    def test_vehicle_issue_list_view_org_scoping(self):
        """Test that VehicleIssueListView respects multi-tenant org boundaries"""
        self.client.login(email="admin@org2.com", password="testpass123")
        
        # Try to access vehicle from org1 as user from org2
        response = self.client.get(
            reverse('issue_management:central_admin:vehicle_issue_list',
                   kwargs={'vehicle_slug': self.vehicle1.slug})
        )
        
        # Should be redirected (not allowed to view other org's vehicles)
        self.assertEqual(response.status_code, 302)
    
    def test_issue_create_view_prefills_vehicle_from_query_param(self):
        """Test that IssueCreateView prefills vehicle from ?vehicle=<slug> query param"""
        self.client.login(email="admin@org1.com", password="testpass123")
        
        response = self.client.get(
            reverse('issue_management:central_admin:issue_create')
            + f'?vehicle={self.vehicle1.slug}'
        )
        
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertEqual(form.initial.get('vehicle'), self.vehicle1.pk)

    def test_issue_create_view_shows_workshop_only_for_vehicle_issues(self):
        """Test that the workshop field only appears when the create page is opened from a vehicle"""
        self.client.login(email="admin@org1.com", password="testpass123")

        response_without_vehicle = self.client.get(reverse('issue_management:central_admin:issue_create'))
        self.assertEqual(response_without_vehicle.status_code, 200)
        self.assertFalse(response_without_vehicle.context['show_workshop_field'])
        self.assertNotContains(response_without_vehicle, 'Workshop (Optional)')

        response_with_vehicle = self.client.get(
            reverse('issue_management:central_admin:issue_create') + f'?vehicle={self.vehicle1.slug}'
        )
        self.assertEqual(response_with_vehicle.status_code, 200)
        self.assertTrue(response_with_vehicle.context['show_workshop_field'])
        self.assertContains(response_with_vehicle, 'Workshop')

    def test_issue_create_view_auto_attaches_vehicle_from_query_param(self):
        """Test that posting from a vehicle-linked create page attaches the vehicle automatically"""
        self.client.login(email="admin@org1.com", password="testpass123")

        response = self.client.post(
            reverse('issue_management:central_admin:issue_create') + f'?vehicle={self.vehicle1.slug}',
            {
                'title': 'Vehicle-linked issue',
                'description': 'Created from vehicle detail',
                'priority': 'medium',
                'space': '',
                'workshop': self.workshop.pk,
                'voice': '',
            }
        )

        self.assertEqual(response.status_code, 302)
        issue = Issue.objects.get(title='Vehicle-linked issue')
        self.assertEqual(issue.vehicle, self.vehicle1)

    def test_issue_create_view_requires_workshop_for_vehicle_issues(self):
        """Test that workshop is required when reporting an issue from a vehicle"""
        self.client.login(email="admin@org1.com", password="testpass123")

        response = self.client.post(
            reverse('issue_management:central_admin:issue_create') + f'?vehicle={self.vehicle1.slug}',
            {
                'title': 'Vehicle-linked issue without workshop',
                'description': 'Missing workshop',
                'priority': 'medium',
                'space': '',
                'voice': '',
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'workshop', 'This field is required.')
        self.assertFalse(Issue.objects.filter(title='Vehicle-linked issue without workshop').exists())
    
    def test_issue_create_view_restricts_vehicle_queryset_by_org(self):
        """Test that IssueCreateView restricts vehicle choices to user's org"""
        self.client.login(email="admin@org1.com", password="testpass123")
        
        response = self.client.get(reverse('issue_management:central_admin:issue_create'))
        
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        vehicle_queryset = form.fields['vehicle'].queryset
        
        self.assertIn(self.vehicle1, vehicle_queryset)
        self.assertNotIn(self.vehicle2, vehicle_queryset)
    
    def test_issue_detail_displays_vehicle(self):
        """Test that issue detail page displays linked vehicle"""
        issue = Issue.objects.create(
            title="Windshield Issue",
            description="Cracked windshield",
            reporter=self.central_admin,
            org=self.org1,
            vehicle=self.vehicle1
        )
        
        self.client.login(email="admin@org1.com", password="testpass123")
        response = self.client.get(
            reverse('issue_management:central_admin:issue_detail',
                   kwargs={'issue_slug': issue.slug})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.vehicle1.registration_number)

    def test_workshop_assigned_on_issue_create(self):
        """Test that creating an issue with workshop sets the workshop FK and it shows on detail"""
        issue = Issue.objects.create(
            title="Workshop Test",
            description="Report to workshop",
            reporter=self.central_admin,
            org=self.org1,
            vehicle=self.vehicle1,
            workshop=self.workshop
        )
        self.client.login(email="admin@org1.com", password="testpass123")
        response = self.client.get(reverse('issue_management:central_admin:issue_detail', kwargs={'issue_slug': issue.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.workshop.name)

    def test_workshop_transfer_view_changes_workshop(self):
        """Test transferring an issue from one workshop to another"""
        other_workshop = Workshop.objects.create(org=self.org1, name='Other Workshop')
        issue = Issue.objects.create(
            title="Transfer Test",
            description="Transfer between workshops",
            reporter=self.central_admin,
            org=self.org1,
            vehicle=self.vehicle1,
            workshop=self.workshop
        )
        self.client.login(email="admin@org1.com", password="testpass123")
        response = self.client.post(
            reverse('issue_management:central_admin:issue_change_workshop', kwargs={'issue_slug': issue.slug}),
            {'workshop': other_workshop.pk}
        )
        self.assertEqual(response.status_code, 302)
        issue.refresh_from_db()
        self.assertEqual(issue.workshop, other_workshop)
    
    def test_vehicle_issue_on_delete_vehicle_preserves_issue(self):
        """Test that deleting a vehicle preserves the issue (FK with SET_NULL)"""
        issue = Issue.objects.create(
            title="Tire Pressure",
            description="Low tire pressure",
            reporter=self.central_admin,
            org=self.org1,
            vehicle=self.vehicle1
        )
        
        issue_id = issue.id
        self.vehicle1.delete()
        
        # Issue should still exist with vehicle=None
        issue = Issue.objects.get(id=issue_id)
        self.assertIsNone(issue.vehicle)
    
    def test_org_scoped_vehicle_queryset_in_form(self):
        """Test that vehicle queryset respects organization scoping in forms"""
        # Org1 user should see org1 vehicles
        form1 = IssueForm(current_user=self.central_admin)
        vehicles_org1 = list(form1.fields['vehicle'].queryset)
        self.assertEqual(len(vehicles_org1), 1)
        self.assertEqual(vehicles_org1[0].org, self.org1)
        
        # Org2 user should see org2 vehicles
        form2 = IssueForm(current_user=self.central_admin_org2)
        vehicles_org2 = list(form2.fields['vehicle'].queryset)
        self.assertEqual(len(vehicles_org2), 1)
        self.assertEqual(vehicles_org2[0].org, self.org2)
