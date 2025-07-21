from django.core.management.base import BaseCommand
from django.urls import reverse, NoReverseMatch


class Command(BaseCommand):
    help = 'Test URL reversing for space admin access control'
    
    def handle(self, *args, **options):
        self.stdout.write("Testing URL patterns...")
        
        urls_to_test = [
            ('service_management:no_spaces_assigned', 'No Spaces Assigned'),
            ('core:logout', 'Logout'),
            ('landing', 'Landing Page'),
        ]
        
        for url_name, description in urls_to_test:
            try:
                url = reverse(url_name)
                self.stdout.write(
                    self.style.SUCCESS(f"✓ {description}: {url}")
                )
            except NoReverseMatch as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ {description}: {e}")
                )
        
        self.stdout.write(
            self.style.SUCCESS("URL testing completed.")
        )
