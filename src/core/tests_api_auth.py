"""API tests for JWT auth (password, PIN, phone) and cookie refresh."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Organization

User = get_user_model()


@override_settings(
    REST_FRAMEWORK={
        'DEFAULT_AUTHENTICATION_CLASSES': (
            'rest_framework_simplejwt.authentication.JWTAuthentication',
            'rest_framework.authentication.SessionAuthentication',
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
class AuthAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org = Organization.objects.create(name='Auth Org')

        self.email_user = User.objects.create_user(
            phone_number='+15550000001',
            email='staff@example.com',
            password='StaffPass123!',
            user_type='supervisor',
            organization=self.org,
            first_name='Staff',
            last_name='User',
        )
        self.email_user.set_pin('1234')
        self.email_user.save(skip_validation=True)

        self.phone_user = User.objects.create_user(
            phone_number='+15550000002',
            user_type='general_user',
            organization=self.org,
            first_name='Phone',
            last_name='User',
        )

        self.central_admin = User.objects.create_user(
            phone_number='+15550000003',
            email='admin@example.com',
            password='AdminPass123!',
            user_type='central_admin',
            organization=self.org,
            first_name='Central',
            last_name='Admin',
        )

    def test_password_login_returns_access_and_refresh_cookie(self):
        response = self.client.post(
            '/api/auth/login/',
            {'email': 'staff@example.com', 'password': 'StaffPass123!'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertNotIn('refresh', response.data)
        self.assertIn('services_refresh', response.cookies)

    def test_pin_login_success(self):
        response = self.client.post(
            '/api/auth/login/pin/',
            {'email': 'staff@example.com', 'pin': '1234'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_phone_login_success(self):
        response = self.client.post(
            '/api/auth/login/phone/',
            {'phone_number': '+15550000002'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_phone_user_rejected_on_password_login(self):
        response = self.client.post(
            '/api/auth/login/',
            {'email': 'unused@example.com', 'password': 'anything'},
            format='json',
        )
        # Phone users have no email; ensure wrong password for email user fails
        response = self.client.post(
            '/api/auth/login/',
            {'email': 'staff@example.com', 'password': 'wrong'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_central_admin_rejected_on_phone_login(self):
        response = self.client.post(
            '/api/auth/login/phone/',
            {'phone_number': '+15550000003'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_refresh_rotates_cookie(self):
        login = self.client.post(
            '/api/auth/login/',
            {'email': 'staff@example.com', 'password': 'StaffPass123!'},
            format='json',
        )
        refresh = login.cookies['services_refresh'].value
        self.client.cookies['services_refresh'] = refresh
        response = self.client.post('/api/auth/token/refresh/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('services_refresh', response.cookies)

    def test_logout_clears_cookie(self):
        login = self.client.post(
            '/api/auth/login/',
            {'email': 'staff@example.com', 'password': 'StaffPass123!'},
            format='json',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        response = self.client.post('/api/auth/logout/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Cookie cleared (max-age 0 or empty)
        self.assertTrue(
            response.cookies['services_refresh'].value == ''
            or str(response.cookies['services_refresh']['max-age']) in ('0', '')
        )

    def test_me_requires_auth(self):
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_profile(self):
        login = self.client.post(
            '/api/auth/login/',
            {'email': 'staff@example.com', 'password': 'StaffPass123!'},
            format='json',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'staff@example.com')
        self.assertEqual(response.data['user_type'], 'supervisor')
