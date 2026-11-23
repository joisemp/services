# Idempotent repair for half-applied Issue → Ticket table renames.
# Safe no-op when ticket_management_ticket* already exists.

from django.db import migrations


def forwards_repair_ticket_tables(apps, schema_editor):
    from ticket_management.management.commands.repair_ticket_table_names import (
        repair_ticket_tables,
    )

    repair_ticket_tables(dry_run=False)


class Migration(migrations.Migration):

    dependencies = [
        ('ticket_management', '0029_polish_ticket_indexes_and_fields'),
    ]

    operations = [
        migrations.RunPython(forwards_repair_ticket_tables, migrations.RunPython.noop),
    ]
