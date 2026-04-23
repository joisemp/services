from django.contrib.auth import authenticate, get_user_model
from django.test import TestCase
from django.urls import reverse

from core.forms import PhoneLoginForm
from core.models import Organization


User = get_user_model()


class PhoneLoginToggleTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name='Org One')
        self.other_organization = Organization.objects.create(name='Org Two')

        self.central_admin = User.objects.create_user(
            phone_number='+10000000001',
            email='admin@example.com',
            password='AdminPass123!',
            user_type='central_admin',
            organization=self.organization,
            first_name='Central',
            last_name='Admin',
        )

        self.general_user = User.objects.create_user(
            phone_number='+10000000002',
            user_type='general_user',
            organization=self.organization,
            first_name='General',
            last_name='User',
        )

        self.other_org_general_user = User.objects.create_user(
            phone_number='+10000000003',
            user_type='general_user',
            organization=self.other_organization,
            first_name='Other',
            last_name='Org',
        )

    def test_general_user_phone_login_allowed_by_default(self):
        self.assertTrue(self.general_user.allow_phone_login)

    def test_phone_login_form_rejects_disabled_general_user(self):
        self.general_user.allow_phone_login = False
        self.general_user.save(update_fields=['allow_phone_login'])

        form = PhoneLoginForm(data={'phone_number': self.general_user.phone_number})

        self.assertFalse(form.is_valid())
        self.assertIn('Phone login is not available for this user.', form.errors['phone_number'])

    def test_phone_auth_backend_rejects_disabled_general_user(self):
        self.general_user.allow_phone_login = False
        self.general_user.save(update_fields=['allow_phone_login'])

        authenticated = authenticate(phone_number=self.general_user.phone_number)
        self.assertIsNone(authenticated)

    def test_central_admin_can_toggle_phone_login_for_same_org_general_user(self):
        self.client.force_login(self.central_admin)

        response = self.client.post(
            reverse('core:toggle_phone_login'),
            {'user_id': self.general_user.id},
        )

        self.assertEqual(response.status_code, 200)
        self.general_user.refresh_from_db()
        self.assertFalse(self.general_user.allow_phone_login)
        self.assertEqual(response.json().get('allow_phone_login'), False)

    def test_toggle_phone_login_blocks_cross_org_user(self):
        self.client.force_login(self.central_admin)

        response = self.client.post(
            reverse('core:toggle_phone_login'),
            {'user_id': self.other_org_general_user.id},
        )

        self.assertEqual(response.status_code, 403)
        self.other_org_general_user.refresh_from_db()
        self.assertTrue(self.other_org_general_user.allow_phone_login)

    def test_toggle_phone_login_rejects_non_general_user(self):
        non_general_user = User.objects.create_user(
            phone_number='+10000000004',
            email='maintainer@example.com',
            password='MaintainerPass123!',
            user_type='maintainer',
            organization=self.organization,
            first_name='Role',
            last_name='User',
        )

        self.client.force_login(self.central_admin)
        response = self.client.post(
            reverse('core:toggle_phone_login'),
            {'user_id': non_general_user.id},
        )

        self.assertEqual(response.status_code, 400)
        non_general_user.refresh_from_db()
        self.assertTrue(non_general_user.allow_phone_login)
