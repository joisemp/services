"""API tests for issue permissions and org isolation."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Organization, Space
from issue_management.models import Issue, PurchaseRequest

User = get_user_model()


def _auth(client, user):
    token = RefreshToken.for_user(user).access_token
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')


@override_settings(
    REST_FRAMEWORK={
        'DEFAULT_AUTHENTICATION_CLASSES': (
            'rest_framework_simplejwt.authentication.JWTAuthentication',
        ),
        'DEFAULT_PERMISSION_CLASSES': (
            'rest_framework.permissions.IsAuthenticated',
        ),
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {},
        'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
        'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
        'PAGE_SIZE': 20,
    }
)
class IssueAPIPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org_a = Organization.objects.create(name='Org A')
        self.org_b = Organization.objects.create(name='Org B')
        self.space_a = Space.objects.create(name='Space A', org=self.org_a)

        self.central_a = User.objects.create_user(
            phone_number='+16660000001',
            email='central-a@example.com',
            password='Pass1234!',
            user_type='central_admin',
            organization=self.org_a,
            first_name='Central',
            last_name='A',
        )
        self.central_b = User.objects.create_user(
            phone_number='+16660000002',
            email='central-b@example.com',
            password='Pass1234!',
            user_type='central_admin',
            organization=self.org_b,
            first_name='Central',
            last_name='B',
        )
        self.supervisor = User.objects.create_user(
            phone_number='+16660000003',
            email='supervisor@example.com',
            password='Pass1234!',
            user_type='supervisor',
            organization=self.org_a,
            first_name='Super',
            last_name='Visor',
        )
        self.maintainer = User.objects.create_user(
            phone_number='+16660000004',
            email='maintainer@example.com',
            password='Pass1234!',
            user_type='maintainer',
            organization=self.org_a,
            first_name='Main',
            last_name='Tainer',
        )
        self.space_admin = User.objects.create_user(
            phone_number='+16660000005',
            email='space@example.com',
            password='Pass1234!',
            user_type='space_admin',
            organization=self.org_a,
            first_name='Space',
            last_name='Admin',
        )
        self.space_admin.spaces.add(self.space_a)
        self.space_admin.set_active_space(self.space_a)

        self.issue_a = Issue.objects.create(
            title='Issue in A',
            description='Desc',
            reporter=self.central_a,
            org=self.org_a,
            space=self.space_a,
            assigned_to=self.supervisor,
            status='assigned',
            priority='medium',
        )
        self.issue_b = Issue.objects.create(
            title='Issue in B',
            description='Desc',
            reporter=self.central_b,
            org=self.org_b,
            status='open',
            priority='low',
        )
        self.purchase = PurchaseRequest.objects.create(
            issue=self.issue_a,
            org=self.org_a,
            space=self.space_a,
            item='Bolts',
            quantity=10,
            requested_by=self.space_admin,
            status='pending',
        )

    def test_other_org_issue_returns_404(self):
        _auth(self.client, self.central_a)
        response = self.client.get(f'/api/issues/{self.issue_b.slug}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_supervisor_can_resolve_assigned_issue(self):
        _auth(self.client, self.supervisor)
        response = self.client.post(
            f'/api/issues/{self.issue_a.slug}/resolve/',
            {'resolution_notes': 'Fixed'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.issue_a.refresh_from_db()
        self.assertEqual(self.issue_a.status, 'resolved')

    def test_maintainer_cannot_assign(self):
        _auth(self.client, self.maintainer)
        response = self.client.post(
            f'/api/issues/{self.issue_a.slug}/assign/',
            {'assigned_to': self.supervisor.slug},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_central_admin_can_approve_purchase(self):
        _auth(self.client, self.central_a)
        response = self.client.post(
            f'/api/purchase-requests/{self.purchase.slug}/approve/',
            {'review_notes': 'OK'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.status, 'approved')
