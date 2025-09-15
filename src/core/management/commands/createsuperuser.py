from django.contrib.auth.management.commands.createsuperuser import Command as BaseCreateSuperUserCommand
from django.core.management import CommandError
from django.core.management.base import CommandParser
from core.models import Organization, User


class Command(BaseCreateSuperUserCommand):
    """
    Custom createsuperuser command that enforces email authentication for superusers
    Superusers don't require an organization
    """
    
    def add_arguments(self, parser: CommandParser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            '--organization',
            help='Organization name for the superuser (optional)',
        )
    
    def handle(self, *args, **options):
        # Organization is optional for superusers
        org_name = options.get('organization')
        organization = None
        
        if org_name:
            # Create or get the organization if specified
            organization, created = Organization.objects.get_or_create(
                name=org_name,
                defaults={
                    'description': f'Organization for {org_name}'
                }
            )
            
            if created:
                self.stdout.write(f'Created organization: {organization.name}')
            else:
                self.stdout.write(f'Using existing organization: {organization.name}')
        else:
            self.stdout.write('Creating superuser without organization association')
        
        # Store organization for use in execute method
        self.organization = organization
        
        # Call the parent handle method
        return super().handle(*args, **options)
    
    def get_input_data(self, field, message, default=None):
        """
        Override to handle our custom fields and ensure email is used for superuser
        """
        # Force email as username field for superuser
        if field.name == self.UserModel.USERNAME_FIELD:
            if self.UserModel.USERNAME_FIELD != 'email':
                # Change the field to email for superuser creation
                field = self.UserModel._meta.get_field('email')
                message = 'Email: '
        
        return super().get_input_data(field, message, default)
    
    def execute(self, *args, **options):
        """
        Override execute to inject organization into the creation process
        """
        # Temporarily store the original create_superuser method
        original_create_superuser = self.UserModel._default_manager.create_superuser
        
        def create_superuser_with_org(*args, **kwargs):
            # Inject the organization
            kwargs['organization'] = self.organization
            return original_create_superuser(*args, **kwargs)
        
        # Replace the method temporarily
        self.UserModel._default_manager.create_superuser = create_superuser_with_org
        
        try:
            return super().execute(*args, **options)
        finally:
            # Restore the original method
            self.UserModel._default_manager.create_superuser = original_create_superuser