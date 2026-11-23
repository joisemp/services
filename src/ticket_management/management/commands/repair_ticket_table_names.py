"""
Idempotent Issue* → Ticket* table/column renames under ticket_management.

Safe before migrate when 0028 may have partially applied or raced:

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

# After tables are at final names: old column → new column
COLUMN_RENAMES = [
    ('ticket_management_ticket', 'issue_id', 'ticket_id'),
    ('ticket_management_ticketimage', 'issue_id', 'ticket_id'),
    ('ticket_management_ticketcomment', 'issue_id', 'ticket_id'),
    ('ticket_management_ticketresolutionimage', 'issue_id', 'ticket_id'),
    ('ticket_management_ticketreviewcomment', 'issue_id', 'ticket_id'),
    ('ticket_management_ticketactivity', 'issue_id', 'ticket_id'),
    ('ticket_management_worktask', 'issue_id', 'ticket_id'),
    ('ticket_management_sitevisit', 'issue_id', 'ticket_id'),
    ('ticket_management_purchaserequest', 'issue_id', 'ticket_id'),
    ('ticket_management_shoppinglistitem', 'issue_title', 'ticket_title'),
]


def _table_columns(cursor, table_name):
    vendor = connection.vendor
    if vendor == 'postgresql':
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema() AND table_name = %s
            """,
            [table_name],
        )
    else:
        description = connection.introspection.get_table_description(cursor, table_name)
        return {col.name for col in description}
    return {row[0] for row in cursor.fetchall()}


def repair_ticket_tables(*, dry_run=False, stdout=None, style=None):
    """Rename Issue* tables/columns to Ticket* when needed. Returns change count."""
    changed = 0
    with connection.cursor() as cursor:
        tables = set(connection.introspection.table_names())

        def run(sql):
            nonlocal changed
            if dry_run:
                if stdout:
                    stdout.write(f'DRY-RUN: {sql}')
                changed += 1
                return
            cursor.execute(sql)
            changed += 1

        def rename_table(old, new):
            if connection.vendor == 'postgresql':
                run(f'ALTER TABLE "{old}" RENAME TO "{new}"')
            elif connection.vendor == 'mysql':
                run(f'RENAME TABLE `{old}` TO `{new}`')
            else:
                run(f'ALTER TABLE {old} RENAME TO {new}')

        def rename_column(table, old, new):
            if connection.vendor == 'postgresql':
                run(f'ALTER TABLE "{table}" RENAME COLUMN "{old}" TO "{new}"')
            elif connection.vendor == 'mysql':
                # Prefer simple rename when types are unchanged
                run(f'ALTER TABLE `{table}` RENAME COLUMN `{old}` TO `{new}`')
            else:
                run(f'ALTER TABLE {table} RENAME COLUMN {old} TO {new}')

        with transaction.atomic():
            for old, new in TABLE_RENAMES:
                tables = set(connection.introspection.table_names())
                if old in tables and new not in tables:
                    rename_table(old, new)
                    if stdout:
                        msg = f'Renamed table {old} → {new}'
                        stdout.write(style.SUCCESS(msg) if style else msg)
                elif old in tables and new in tables and stdout:
                    msg = f'Skip table {old}: {new} already exists'
                    stdout.write(style.WARNING(msg) if style else msg)

            tables = set(connection.introspection.table_names())
            for table, old_col, new_col in COLUMN_RENAMES:
                if table not in tables:
                    continue
                cols = _table_columns(cursor, table)
                if old_col in cols and new_col not in cols:
                    rename_column(table, old_col, new_col)
                    if stdout:
                        msg = f'Renamed column {table}.{old_col} → {new_col}'
                        stdout.write(style.SUCCESS(msg) if style else msg)
                elif old_col in cols and new_col in cols and stdout:
                    msg = f'Skip column {table}.{old_col}: {new_col} already exists'
                    stdout.write(style.WARNING(msg) if style else msg)

    return changed


class Command(BaseCommand):
    help = (
        'Idempotently rename ticket_management_issue* tables/columns to ticket_* '
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
        changed = repair_ticket_tables(
            dry_run=dry_run,
            stdout=self.stdout,
            style=self.style,
        )
        if changed == 0:
            self.stdout.write(self.style.SUCCESS('Ticket table names already OK; nothing to do.'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Repair complete ({changed} change(s)).' if not dry_run else 'Dry run complete.'
            ))
