"""
Management command: import_org_space_map
=========================================
Reads a JSON file produced by the Auth service (or ``export_org_space_map``)
and backfills ``org_uuid`` / ``space_uuid`` on local Organisation / Space
records by matching on the ``code`` field.

This is the canonical way to push UUIDs from the Auth service back into the
Services app.  It is safe to re-run: records whose UUID already matches the
import file are left unchanged; only actual differences are written.

Usage
-----
    # Import from a file
    python manage.py import_org_space_map /tmp/auth_export.json

    # Preview changes without saving
    python manage.py import_org_space_map /tmp/auth_export.json --dry-run

    # Show a summary of what would be updated even on re-runs
    python manage.py import_org_space_map /tmp/auth_export.json --verbose

Expected input format
---------------------
The file must be valid JSON and may contain either or both of the following
top-level keys:

{
  "organisations": [
    { "code": "ACME",      "org_uuid": "…uuid…" },
    …
  ],
  "spaces": [
    { "code": "ACME-MAIN", "space_uuid": "…uuid…" },
    …
  ]
}

Unknown keys are silently ignored, so files produced by the Auth service that
carry extra fields (names, addresses, etc.) are accepted without modification.

Error handling
--------------
* A missing or duplicate ``code`` in the local database is reported as a
  warning — the row is skipped and processing continues.
* An invalid UUID value raises an error immediately.
* Use ``--dry-run`` to validate the file before committing.
"""

import json
import uuid as uuid_module

from django.core.management.base import BaseCommand, CommandError

from core.models import Organization, Space


class Command(BaseCommand):
    help = (
        "Import canonical org_uuid / space_uuid values from an Auth-service export "
        "JSON, matching records by their 'code' field."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "input",
            metavar="FILE",
            help="Path to the JSON import file.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Print what would be changed without writing to the database.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            default=False,
            help="Print a line for every record, including unchanged ones.",
        )

    def handle(self, *args, **options):
        input_path = options["input"]
        dry_run = options["dry_run"]
        verbose = options["verbose"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be saved.\n"))

        try:
            with open(input_path, encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            raise CommandError(f"File not found: {input_path}")
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON in {input_path}: {exc}")

        if not isinstance(data, dict):
            raise CommandError("Import file must be a JSON object at the top level.")

        org_records = data.get("organisations", [])
        space_records = data.get("spaces", [])

        orgs_updated = self._import_organisations(
            org_records, dry_run=dry_run, verbose=verbose
        )
        spaces_updated = self._import_spaces(
            space_records, dry_run=dry_run, verbose=verbose
        )

        verb = "Would update" if dry_run else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{verb} {orgs_updated} organisation(s) and {spaces_updated} space(s)."
            )
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_uuid(self, value, field_name):
        """Parse *value* as a UUID or raise CommandError."""
        try:
            return uuid_module.UUID(str(value))
        except (ValueError, AttributeError):
            raise CommandError(
                f"Invalid UUID value for {field_name!r}: {value!r}"
            )

    def _import_organisations(self, records, *, dry_run, verbose):
        if not records:
            return 0

        self.stdout.write(f"Importing {len(records)} organisation record(s) …")

        # Build a lookup: code → Organisation
        code_map = {
            org.code: org
            for org in Organization.objects.exclude(code__isnull=True).exclude(code="")
        }

        updated = 0
        for rec in records:
            code = rec.get("code")
            raw_uuid = rec.get("org_uuid")

            if not code:
                self.stdout.write(
                    self.style.WARNING("  Skipping record with missing 'code'.")
                )
                continue

            if raw_uuid is None:
                if verbose:
                    self.stdout.write(
                        f"  Organisation code={code!r}: no org_uuid in import — skipped."
                    )
                continue

            new_uuid = self._parse_uuid(raw_uuid, "org_uuid")

            if code not in code_map:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Organisation code={code!r} not found locally — skipped."
                    )
                )
                continue

            org = code_map[code]

            if org.org_uuid == new_uuid:
                if verbose:
                    self.stdout.write(
                        f"  Organisation [{org.pk}] {org.name!r} (code={code!r}): "
                        "UUID unchanged."
                    )
                continue

            self.stdout.write(
                f"  Organisation [{org.pk}] {org.name!r} (code={code!r}): "
                f"{org.org_uuid} → {new_uuid}"
            )
            if not dry_run:
                Organization.objects.filter(pk=org.pk).update(org_uuid=new_uuid)
            updated += 1

        return updated

    def _import_spaces(self, records, *, dry_run, verbose):
        if not records:
            return 0

        self.stdout.write(f"Importing {len(records)} space record(s) …")

        # Build a lookup: code → Space
        code_map = {
            space.code: space
            for space in Space.objects.select_related("org")
            .exclude(code__isnull=True)
            .exclude(code="")
        }

        updated = 0
        for rec in records:
            code = rec.get("code")
            raw_uuid = rec.get("space_uuid")

            if not code:
                self.stdout.write(
                    self.style.WARNING("  Skipping space record with missing 'code'.")
                )
                continue

            if raw_uuid is None:
                if verbose:
                    self.stdout.write(
                        f"  Space code={code!r}: no space_uuid in import — skipped."
                    )
                continue

            new_uuid = self._parse_uuid(raw_uuid, "space_uuid")

            if code not in code_map:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Space code={code!r} not found locally — skipped."
                    )
                )
                continue

            space = code_map[code]

            if space.space_uuid == new_uuid:
                if verbose:
                    self.stdout.write(
                        f"  Space [{space.pk}] {space.name!r} (code={code!r}): "
                        "UUID unchanged."
                    )
                continue

            self.stdout.write(
                f"  Space [{space.pk}] {space.name!r} (code={code!r}): "
                f"{space.space_uuid} → {new_uuid}"
            )
            if not dry_run:
                Space.objects.filter(pk=space.pk).update(space_uuid=new_uuid)
            updated += 1

        return updated
