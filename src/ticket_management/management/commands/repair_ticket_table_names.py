"""
Idempotent Issue* → Ticket* table renames under the ticket_management app label.

Safe to run before migrate when 0028 may have partially applied or raced:

    python manage.py repair_ticket_table_names
    python manage.py migrate
"""
from django.core.management.base import BaseCommand
from django.db import connection, transaction


# Intermediate (post-relabel, pre-0028) → final (post-0028) table names
TABLE_RENAMES = [
    ('ticket_management_issue_reviewers', 'ticket_management_ticket_reviewers'),
    ('ticket_management_issueimage', 'ticket_management_ticketimage'),
    ('ticket_management_issuecomment', 'ticket_management_ticketcomment'),
    ('ticket_management_issueresolutionimage', 'ticket_management_ticketresolutionimage'),
    ('ticket_management_issuereviewcommentimage', 'ticket_management_ticketreviewcommentimage'),
    ('ticket_management_issuereviewcomment', 'ticket_management_ticketreviewcomment'),
    ('ticket_management_issueactivity', 'ticket_management_ticketactivity'),
    ('ticket_management_issue', 'ticket_management_ticket'),
]


def repair_ticket_tables(*, dry_run=False, stdout=None, style=None):
    """Rename intermediate Issue* tables to Ticket* when needed. Returns rename count."""
    renamed = 0
    with connection.cursor() as cursor:
        tables = set(connection.introspection.table_names())

        def run(sql):
            if dry_run:
                if stdout:
                    stdout.write(f'DRY-RUN: {sql}')
                return
            cursor.execute(sql)

        with transaction.atomic():
            for old, new in TABLE_RENAMES:
                if old in tables and new not in tables:
                    if connection.vendor == 'postgresql':
                        run(f'ALTER TABLE "{old}" RENAME TO "{new}"')
                    elif connection.vendor == 'mysql':
                        run(f'RENAME TABLE `{old}` TO `{new}`')
                    else:
                        run(f'ALTER TABLE {old} RENAME TO {new}')
                    renamed += 1
                    if stdout:
                        msg = f'Renamed table {old} → {new}'
                        stdout.write(style.SUCCESS(msg) if style else msg)
                elif old in tables and new in tables and stdout:
                    msg = f'Skip {old}: {new} already exists'
                    stdout.write(style.WARNING(msg) if style else msg)

    return renamed


class Command(BaseCommand):
    help = (
        'Idempotently rename ticket_management_issue* tables to ticket_management_ticket* '
        'when a partial Issue→Ticket migration left the DB half-renamed.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print actions without applying them.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        renamed = repair_ticket_tables(
            dry_run=dry_run,
            stdout=self.stdout,
            style=self.style,
        )
        if renamed == 0:
            self.stdout.write(self.style.SUCCESS('Ticket table names already OK; nothing to do.'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Repair complete ({renamed} rename(s)).' if not dry_run else 'Dry run complete.'
            ))
