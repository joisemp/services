"""
One-time prep for existing databases after renaming the Django app package.

Run BEFORE migrate when upgrading a DB that already applied issue_management migrations:

    python manage.py relabel_issue_to_ticket_app
    python manage.py migrate

Fresh databases do not need this command.
"""
from django.core.management.base import BaseCommand
from django.db import connection, transaction


OLD_APP = 'issue_management'
NEW_APP = 'ticket_management'

# Old table name -> intermediate name under new app label (model still Issue*)
TABLE_RENAMES = [
    ('issue_management_issue_reviewers', 'ticket_management_issue_reviewers'),
    ('issue_management_issueimage', 'ticket_management_issueimage'),
    ('issue_management_issuecomment', 'ticket_management_issuecomment'),
    ('issue_management_issueresolutionimage', 'ticket_management_issueresolutionimage'),
    ('issue_management_issuereviewcommentimage', 'ticket_management_issuereviewcommentimage'),
    ('issue_management_issuereviewcomment', 'ticket_management_issuereviewcomment'),
    ('issue_management_issueactivity', 'ticket_management_issueactivity'),
    ('issue_management_worktaskresolutionimage', 'ticket_management_worktaskresolutionimage'),
    ('issue_management_worktaskshare', 'ticket_management_worktaskshare'),
    ('issue_management_worktask', 'ticket_management_worktask'),
    ('issue_management_sitevisitimage', 'ticket_management_sitevisitimage'),
    ('issue_management_sitevisit', 'ticket_management_sitevisit'),
    ('issue_management_purchaserequest', 'ticket_management_purchaserequest'),
    ('issue_management_shoppinglistitem', 'ticket_management_shoppinglistitem'),
    ('issue_management_shoppinglist', 'ticket_management_shoppinglist'),
    ('issue_management_issue', 'ticket_management_issue'),
]


class Command(BaseCommand):
    help = (
        'Relabel issue_management → ticket_management in django_migrations / '
        'contenttypes and rename DB tables to the new app prefix. '
        'Required once for existing DBs before migrate.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print actions without applying them.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        with connection.cursor() as cursor:
            tables = set(connection.introspection.table_names())

            if OLD_APP + '_issue' not in tables and 'django_migrations' in tables:
                cursor.execute(
                    'SELECT COUNT(*) FROM django_migrations WHERE app = %s',
                    [OLD_APP],
                )
                old_mig_count = cursor.fetchone()[0]
                if old_mig_count == 0 and NEW_APP + '_issue' in tables or NEW_APP + '_ticket' in tables:
                    self.stdout.write(self.style.SUCCESS('Already relabeled; nothing to do.'))
                    return

            def run(sql, params=None):
                params = params or []
                if dry_run:
                    self.stdout.write(f'DRY-RUN: {sql} {params}')
                    return
                cursor.execute(sql, params)

            with transaction.atomic():
                run(
                    'UPDATE django_migrations SET app = %s WHERE app = %s',
                    [NEW_APP, OLD_APP],
                )
                run(
                    'UPDATE django_content_type SET app_label = %s WHERE app_label = %s',
                    [NEW_APP, OLD_APP],
                )

                for old, new in TABLE_RENAMES:
                    if old in tables and new not in tables:
                        # SQLite / Postgres
                        if connection.vendor == 'mysql':
                            run(f'RENAME TABLE `{old}` TO `{new}`')
                        else:
                            run(f'ALTER TABLE "{old}" RENAME TO "{new}"' if connection.vendor == 'postgresql'
                                else f'ALTER TABLE {old} RENAME TO {new}')
                        self.stdout.write(f'Renamed table {old} → {new}')
                    elif old in tables and new in tables:
                        self.stdout.write(self.style.WARNING(f'Skip {old}: {new} already exists'))

        self.stdout.write(self.style.SUCCESS(
            'Relabel complete.' if not dry_run else 'Dry run complete.'
        ))
