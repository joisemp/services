"""
Relabel issue_management → ticket_management for existing databases.

Run before (or automatically via pre_migrate during) migrate when upgrading a DB
that already applied issue_management migrations. Fresh databases are a no-op.
"""
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

OLD_ISSUE_TABLE = f'{OLD_APP}_issue'
NEW_ISSUE_TABLE = f'{NEW_APP}_issue'
NEW_TICKET_TABLE = f'{NEW_APP}_ticket'


class DualSchemaError(RuntimeError):
    """Raised when both old and new app tables exist (unsafe to auto-relabel)."""


def _rename_table_sql(old: str, new: str) -> str:
    if connection.vendor == 'mysql':
        return f'RENAME TABLE `{old}` TO `{new}`'
    if connection.vendor == 'postgresql':
        return f'ALTER TABLE "{old}" RENAME TO "{new}"'
    return f'ALTER TABLE {old} RENAME TO {new}'


def relabel_issue_to_ticket_app(*, dry_run: bool = False, stdout=None, style=None):
    """
    Relabel migration/contenttype rows and rename issue_management_* tables.

    Returns a short status string: 'already_done', 'noop', 'dry_run', or 'complete'.

    Raises DualSchemaError if both old and new schema tables exist.
    """
    def write(msg, success=False, warning=False):
        if stdout is None:
            return
        if style is not None:
            if success:
                msg = style.SUCCESS(msg)
            elif warning:
                msg = style.WARNING(msg)
        stdout.write(msg)

    with connection.cursor() as cursor:
        tables = set(connection.introspection.table_names())

        has_old_issue = OLD_ISSUE_TABLE in tables
        has_new_issue = NEW_ISSUE_TABLE in tables
        has_new_ticket = NEW_TICKET_TABLE in tables
        has_new_schema = has_new_issue or has_new_ticket
        has_migrations_table = 'django_migrations' in tables
        has_contenttypes_table = 'django_content_type' in tables

        if has_old_issue and has_new_schema:
            raise DualSchemaError(
                'Both issue_management and ticket_management tables exist. '
                'Refusing to relabel to avoid orphaning data. Restore from backup '
                'or manually reconcile the schema before migrating.'
            )

        old_mig_count = 0
        if has_migrations_table:
            cursor.execute(
                'SELECT COUNT(*) FROM django_migrations WHERE app = %s',
                [OLD_APP],
            )
            old_mig_count = cursor.fetchone()[0]

        if not has_old_issue and old_mig_count == 0:
            if has_new_schema:
                write('Already relabeled; nothing to do.', success=True)
                return 'already_done'
            write('No issue_management tables or migration rows; nothing to do.', success=True)
            return 'noop'

        if not has_migrations_table:
            write('django_migrations missing; nothing to do.', success=True)
            return 'noop'

        renamed = []

        def run(sql, params=None):
            params = params or []
            if dry_run:
                write(f'DRY-RUN: {sql} {params}')
                return
            cursor.execute(sql, params)

        with transaction.atomic():
            run(
                'UPDATE django_migrations SET app = %s WHERE app = %s',
                [NEW_APP, OLD_APP],
            )
            if has_contenttypes_table:
                run(
                    'UPDATE django_content_type SET app_label = %s WHERE app_label = %s',
                    [NEW_APP, OLD_APP],
                )

            for old, new in TABLE_RENAMES:
                if old in tables and new not in tables:
                    run(_rename_table_sql(old, new))
                    write(f'Renamed table {old} → {new}')
                    renamed.append((old, new))
                elif old in tables and new in tables:
                    # Should have been caught by dual-schema check for the
                    # primary issue table; treat any remaining collision as fatal.
                    raise DualSchemaError(
                        f'Cannot rename {old} → {new}: both tables already exist. '
                        'Refusing to leave orphaned data.'
                    )

        if dry_run:
            write('Dry run complete.', success=True)
            return 'dry_run'

        write('Relabel complete.', success=True)
        return 'complete'
