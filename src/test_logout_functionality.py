"""
Test to verify logout functionality works correctly across all navbars and user types.
Run this test to ensure logout is working properly with the new custom logout view.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from core.models import UserProfile, Organisation
from django.contrib.messages import get_messages

User = get_user_model()


class LogoutFunctionalityTest(TestCase):
    def setUp(self):
        """Set up test data for different user types"""
        self.client = Client()
        
        # Create an organization
        self.org = Organisation.objects.create(
            name="Test Organization",
            address="123 Test Street"
        )
        
        # Create users for different user types
        self.user_types = [
            'central_admin',
            'space_admin', 
            'maintainer',
            'general_user',
            'institution_admin',
            'departement_incharge',
            'room_incharge'
        ]
        
        self.users = {}
        for user_type in self.user_types:
            user = User.objects.create_user(
                email=f"{user_type}@example.com",
                phone=f"123456789{len(self.users)}",
                password="testpass123"
            )
            
            profile = UserProfile.objects.create(
                user=user,
                first_name="Test",
                last_name=user_type.replace('_', ' ').title(),
                user_type=user_type,
                org=self.org
            )
            
            self.users[user_type] = user
    
    def test_logout_url_exists(self):
        """Test that the logout URL is properly configured"""
        logout_url = reverse('core:logout')
        self.assertEqual(logout_url, '/core/logout/')
    
    def test_logout_with_get_request(self):
        """Test that logout works with GET requests (for backward compatibility)"""
        user = self.users['central_admin']
        
        # Login the user
        self.client.login(email=user.email, password="testpass123")
        
        # Verify user is logged in by accessing dashboard
        dashboard_response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(dashboard_response.status_code, 200)
        
        # Test logout with GET
        logout_response = self.client.get(reverse('core:logout'))
        
        # Should redirect to landing page
        self.assertEqual(logout_response.status_code, 302)
        self.assertRedirects(logout_response, reverse('landing'))
        
        # Verify user is logged out by trying to access dashboard again
        dashboard_response_after_logout = self.client.get(reverse('dashboard:dashboard'))
        # Should redirect to login or show 403/redirect
        self.assertIn(dashboard_response_after_logout.status_code, [302, 403])
    
    def test_logout_with_post_request(self):
        """Test that logout works with POST requests (more secure)"""
        user = self.users['space_admin']
        
        # Login the user
        self.client.login(email=user.email, password="testpass123")
        
        # Verify user is logged in
        dashboard_response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(dashboard_response.status_code, 200)
        
        # Test logout with POST
        logout_response = self.client.post(reverse('core:logout'))
        
        # Should redirect to landing page
        self.assertEqual(logout_response.status_code, 302)
        self.assertRedirects(logout_response, reverse('landing'))
        
        # Verify user is logged out
        dashboard_response_after_logout = self.client.get(reverse('dashboard:dashboard'))
        self.assertIn(dashboard_response_after_logout.status_code, [302, 403])
    
    def test_logout_shows_success_message(self):
        """Test that logout shows a success message"""
        user = self.users['maintainer']
        
        # Login the user
        self.client.login(email=user.email, password="testpass123")
        
        # Test logout
        logout_response = self.client.post(reverse('core:logout'), follow=True)
        
        # Check for success message
        messages = list(get_messages(logout_response.wsgi_request))
        self.assertTrue(any('successfully logged out' in str(message) for message in messages))
    
    def test_logout_functionality_for_all_user_types(self):
        """Test that logout works for all user types"""
        for user_type, user in self.users.items():
            with self.subTest(user_type=user_type):
                # Login the user
                self.client.login(email=user.email, password="testpass123")
                
                # Verify user is logged in by accessing dashboard
                dashboard_response = self.client.get(reverse('dashboard:dashboard'))
                self.assertEqual(dashboard_response.status_code, 200)
                
                # Test logout
                logout_response = self.client.post(reverse('core:logout'))
                
                # Should redirect to landing page
                self.assertEqual(logout_response.status_code, 302)
                self.assertRedirects(logout_response, reverse('landing'))
                
                # Verify user is logged out by trying to access dashboard again
                dashboard_response_after_logout = self.client.get(reverse('dashboard:dashboard'))
                # Should redirect to login or show 403/redirect
                self.assertIn(dashboard_response_after_logout.status_code, [302, 403])
    
    def test_unauthenticated_user_logout(self):
        """Test that logout works even for unauthenticated users"""
        # Don't login any user
        logout_response = self.client.get(reverse('core:logout'))
        
        # Should still redirect to landing page
        self.assertEqual(logout_response.status_code, 302)
        self.assertRedirects(logout_response, reverse('landing'))
    
    def test_logout_csrf_protection(self):
        """Test that POST logout properly handles CSRF protection"""
        user = self.users['general_user']
        
        # Login the user
        self.client.login(email=user.email, password="testpass123")
        
        # Test logout with POST including CSRF token
        response = self.client.get(reverse('landing'))  # Get CSRF token
        csrf_token = response.context['csrf_token']
        
        logout_response = self.client.post(reverse('core:logout'), {
            'csrfmiddlewaretoken': csrf_token
        })
        
        # Should work fine
        self.assertEqual(logout_response.status_code, 302)
        self.assertRedirects(logout_response, reverse('landing'))


if __name__ == '__main__':
    # This allows running the test directly
    import django
    import sys
    import os
    
    # Add the src directory to Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    
    # Setup Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    
    # Run the test
    from django.test.utils import get_runner
    from django.conf import settings
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["__main__"])
