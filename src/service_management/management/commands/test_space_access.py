from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import UserProfile
from service_management.models import Spaces
from config.helpers import is_space_admin, has_assigned_spaces

User = get_user_model()


class Command(BaseCommand):
    help = 'Test space admin access control functionality'
    
    def handle(self, *args, **options):
        self.stdout.write("Testing Space Admin Access Control...")
        
        # Find space admins
        space_admins = UserProfile.objects.filter(user_type='space_admin')
        
        if not space_admins.exists():
            self.stdout.write(
                self.style.WARNING('No space admins found in the system.')
            )
            return
        
        for profile in space_admins:
            user = profile.user
            self.stdout.write(f"\nTesting user: {user}")
            self.stdout.write(f"  - Is space admin: {is_space_admin(user)}")
            self.stdout.write(f"  - Has assigned spaces: {has_assigned_spaces(user)}")
            
            # Show assigned spaces
            assigned_spaces = Spaces.objects.filter(space_admins=user)
            if assigned_spaces.exists():
                self.stdout.write(f"  - Assigned to {assigned_spaces.count()} space(s):")
                for space in assigned_spaces:
                    self.stdout.write(f"    * {space.name} ({space.org.name})")
            else:
                self.stdout.write(
                    self.style.ERROR('    * No spaces assigned - would be redirected to no-spaces page')
                )
        
        self.stdout.write(
            self.style.SUCCESS('\nSpace admin access control test completed.')
        )
