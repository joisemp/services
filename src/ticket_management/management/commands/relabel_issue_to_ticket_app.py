"""
One-time prep for existing databases after renaming the Django app package.

Usually unnecessary: pre_migrate auto-runs the same logic. You can still invoke
it manually before migrate:

    python manage.py relabel_issue_to_ticket_app
    python manage.py migrate

Fresh databases do not need this command.
"""
from django.core.management.base import BaseCommand, CommandError

from ticket_management.relabel_app import DualSchemaError, relabel_issue_to_ticket_app


class Command(BaseCommand):
    help = (
        'Relabel issue_management → ticket_management in django_migrations / '
        'contenttypes and rename DB tables to the new app prefix. '
        'Required once for existing DBs before migrate (also run automatically '
        'via pre_migrate).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print actions without applying them.',
        )

    def handle(self, *args, **options):
        try:
            relabel_issue_to_ticket_app(
                dry_run=options['dry_run'],
                stdout=self.stdout,
                style=self.style,
            )
        except DualSchemaError as exc:
            raise CommandError(str(exc)) from exc
