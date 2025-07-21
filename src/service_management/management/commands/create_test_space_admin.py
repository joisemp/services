from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import UserProfile, Organisation
from service_management.models import Spaces

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a test space admin for testing access control'
    
    def handle(self, *args, **options):
        self.stdout.write("Creating test space admin...")
        
        # Get or create an organization
        org, created = Organisation.objects.get_or_create(
            name="Test Organization",
            defaults={'address': 'Test Address'}
        )
        
        if created:
            self.stdout.write(f"Created organization: {org.name}")
        else:
            self.stdout.write(f"Using existing organization: {org.name}")
        
        # Create test space admin user
        user, created = User.objects.get_or_create(
            email='spaceadmin@test.com',
            defaults={
                'phone': '+1234567890'
            }
        )
        
        if created:
            user.set_password('testpass123')
            user.save()
            self.stdout.write(f"Created user: {user.email}")
        else:
            self.stdout.write(f"Using existing user: {user.email}")
        
        # Create or update profile
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'org': org,
                'first_name': 'Test',
                'last_name': 'SpaceAdmin',
                'user_type': 'space_admin'
            }
        )
        
        if not created:
            profile.org = org
            profile.user_type = 'space_admin'
            profile.save()
            self.stdout.write(f"Updated profile for: {user.email}")
        else:
            self.stdout.write(f"Created profile for: {user.email}")
        
        # Check current space assignments
        assigned_spaces = Spaces.objects.filter(space_admins=user)
        self.stdout.write(f"Current assigned spaces: {assigned_spaces.count()}")
        
        if assigned_spaces.count() == 0:
            self.stdout.write(
                self.style.WARNING(
                    f"Space admin {user.email} has no assigned spaces - will be restricted by middleware"
                )
            )
        else:
            for space in assigned_spaces:
                self.stdout.write(f"  - {space.name}")
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Test space admin ready: {user.email} (password: testpass123)"
            )
        )
