"""
Management command: backfill_uuids
====================================
Assigns random UUIDs to the ``org_uuid`` / ``space_uuid`` fields on
Organisation and Space records that do not already have one.

These are *temporary placeholder* UUIDs — the canonical values will be
overwritten later by the Auth service via ``import_org_space_map``.  The main
purpose of this command is to ensure every record has *some* UUID so that
downstream code that depends on the field being non-null can be developed and
tested before the Auth service is ready.

Usage
-----
    # Backfill both models (default)
    python manage.py backfill_uuids

    # Backfill organisations only
    python manage.py backfill_uuids --model org

    # Backfill spaces only
    python manage.py backfill_uuids --model space

    # Preview without saving
    python manage.py backfill_uuids --dry-run

    # Overwrite UUIDs that are already set (use with care!)
    python manage.py backfill_uuids --overwrite

Reversibility
-------------
To clear all UUIDs:

    python manage.py shell -c "
    from core.models import Organization, Space
    Organization.objects.all().update(org_uuid=None)
    Space.objects.all().update(space_uuid=None)
    "
"""

import uuid

from django.core.management.base import BaseCommand

from core.models import Organization, Space


class Command(BaseCommand):
    help = (
        "Assign random UUIDs to Organisation.org_uuid and Space.space_uuid for "
        "records that do not already have one.  These are placeholder values; "
        "canonical UUIDs are pushed by the Auth service via import_org_space_map."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--model",
            choices=["org", "space", "both"],
            default="both",
            help="Which model(s) to backfill.  Default: both.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Print what would be changed without writing to the database.",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            default=False,
            help="Overwrite UUIDs that are already set (use with care).",
        )

    def handle(self, *args, **options):
        model = options["model"]
        dry_run = options["dry_run"]
        overwrite = options["overwrite"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be saved.\n"))

        if model in ("org", "both"):
            self._backfill_organisations(dry_run=dry_run, overwrite=overwrite)

        if model in ("space", "both"):
            self._backfill_spaces(dry_run=dry_run, overwrite=overwrite)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _backfill_organisations(self, *, dry_run, overwrite):
        self.stdout.write("Backfilling Organisation UUIDs …")

        qs = Organization.objects.all()
        if not overwrite:
            qs = qs.filter(org_uuid__isnull=True)

        updated = 0
        for org in qs:
            new_uuid = uuid.uuid4()
            self.stdout.write(
                f"  Organisation [{org.pk}] {org.name!r} (code={org.code!r}): "
                f"{org.org_uuid} → {new_uuid}"
            )
            if not dry_run:
                Organization.objects.filter(pk=org.pk).update(org_uuid=new_uuid)
            updated += 1

        if updated == 0:
            self.stdout.write(self.style.SUCCESS("  No organisations needed UUID backfilling."))
        else:
            verb = "Would update" if dry_run else "Updated"
            self.stdout.write(self.style.SUCCESS(f"  {verb} {updated} organisation(s)."))

    def _backfill_spaces(self, *, dry_run, overwrite):
        self.stdout.write("Backfilling Space UUIDs …")

        qs = Space.objects.select_related("org").all()
        if not overwrite:
            qs = qs.filter(space_uuid__isnull=True)

        updated = 0
        for space in qs:
            new_uuid = uuid.uuid4()
            self.stdout.write(
                f"  Space [{space.pk}] {space.name!r} (code={space.code!r}, "
                f"org={space.org.name!r}): {space.space_uuid} → {new_uuid}"
            )
            if not dry_run:
                Space.objects.filter(pk=space.pk).update(space_uuid=new_uuid)
            updated += 1

        if updated == 0:
            self.stdout.write(self.style.SUCCESS("  No spaces needed UUID backfilling."))
        else:
            verb = "Would update" if dry_run else "Updated"
            self.stdout.write(self.style.SUCCESS(f"  {verb} {updated} space(s)."))
