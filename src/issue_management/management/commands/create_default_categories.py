from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Organisation
from issue_management.models import IssueCategory


class Command(BaseCommand):
    help = 'Create default issue categories for all organizations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--org-slug',
            type=str,
            help='Create categories only for specific organization',
        )

    def handle(self, *args, **options):
        default_categories = [
            {
                'name': 'Bug Report',
                'description': 'Software bugs, system malfunctions, or unexpected behavior',
                'color': '#dc3545'  # Red
            },
            {
                'name': 'Feature Request',
                'description': 'Requests for new features or enhancements',
                'color': '#007bff'  # Blue
            },
            {
                'name': 'Maintenance',
                'description': 'Routine maintenance, repairs, or upkeep issues',
                'color': '#ffc107'  # Yellow
            },
            {
                'name': 'Security',
                'description': 'Security-related issues or vulnerabilities',
                'color': '#6f42c1'  # Purple
            },
            {
                'name': 'Infrastructure',
                'description': 'Network, hardware, or infrastructure problems',
                'color': '#28a745'  # Green
            },
            {
                'name': 'User Support',
                'description': 'User assistance, questions, or support requests',
                'color': '#17a2b8'  # Teal
            }
        ]

        if options['org_slug']:
            try:
                orgs = [Organisation.objects.get(slug=options['org_slug'])]
            except Organisation.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Organization with slug "{options["org_slug"]}" not found')
                )
                return
        else:
            orgs = Organisation.objects.all()

        created_count = 0
        for org in orgs:
            self.stdout.write(f'Creating categories for organization: {org.name}')
            
            for category_data in default_categories:
                category, created = IssueCategory.objects.get_or_create(
                    name=category_data['name'],
                    org=org,
                    defaults={
                        'description': category_data['description'],
                        'color': category_data['color'],
                        'is_active': True
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Created category: {category.name}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'  - Category already exists: {category.name}')
                    )

        self.stdout.write(
            self.style.SUCCESS(f'\nCompleted! Created {created_count} new categories.')
        )
