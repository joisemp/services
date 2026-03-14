"""
Management command: backfill_identity_fields

Generates placeholder codes and/or canonical UUIDs for Organizations and Spaces
that currently have blank values for those fields.

Placeholder codes are generated from the model's slug by upper-casing it and
replacing hyphens with underscores (e.g. slug "acme-corp" → code "ACME_CORP").
A numeric suffix is appended when a collision would occur.

This command is intentionally *idempotent*: rows that already have a code/uuid
are left untouched unless --force is passed.

Usage examples:
    # Dry-run: show what would change without saving
    python manage.py backfill_identity_fields --dry-run

    # Generate missing codes AND uuids for all orgs and spaces
    python manage.py backfill_identity_fields

    # Only generate uuids for spaces
    python manage.py backfill_identity_fields --model space --skip-codes

    # Overwrite existing values (use with care)
    python manage.py backfill_identity_fields --force
"""

import uuid as _uuid_mod

from django.core.management.base import BaseCommand

from core.models import Organization, Space


def _slug_to_code(slug):
    """Convert a slug to an uppercase placeholder code."""
    return slug.upper().replace("-", "_")


def _unique_code(base_code, existing_codes):
    """Return a code that does not appear in existing_codes, appending a counter if needed."""
    code = base_code
    counter = 2
    while code in existing_codes:
        code = f"{base_code}_{counter}"
        counter += 1
    return code


class Command(BaseCommand):
    help = (
        "Generate placeholder codes and/or canonical UUIDs for Organizations "
        "and Spaces that currently have blank values for those fields."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--model",
            choices=["org", "space", "all"],
            default="all",
            help="Which model(s) to backfill (default: all).",
        )
        parser.add_argument(
            "--skip-codes",
            action="store_true",
            default=False,
            help="Skip generating placeholder codes; only fill uuid fields.",
        )
        parser.add_argument(
            "--skip-uuids",
            action="store_true",
            default=False,
            help="Skip generating UUIDs; only fill code fields.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="Overwrite existing non-blank values (use with care).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Show what would change without writing to the database.",
        )

    def handle(self, *args, **options):
        model = options["model"]
        skip_codes = options["skip_codes"]
        skip_uuids = options["skip_uuids"]
        force = options["force"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stderr.write(self.style.WARNING("DRY-RUN mode – no changes will be saved."))

        if model in ("org", "all"):
            self._backfill_orgs(skip_codes, skip_uuids, force, dry_run)

        if model in ("space", "all"):
            self._backfill_spaces(skip_codes, skip_uuids, force, dry_run)

    # ------------------------------------------------------------------
    # Per-model helpers
    # ------------------------------------------------------------------

    def _backfill_orgs(self, skip_codes, skip_uuids, force, dry_run):
        orgs = list(Organization.objects.all().order_by("pk"))
        if not orgs:
            self.stderr.write("No organisations found.")
            return

        # Build the set of codes already in use (including DB rows we won't touch)
        existing_codes = set(
            Organization.objects.exclude(code__isnull=True)
            .exclude(code="")
            .values_list("code", flat=True)
        )

        updated = 0
        for org in orgs:
            dirty = False

            if not skip_codes and (force or not org.code):
                base = _slug_to_code(org.slug) if org.slug else f"ORG_{org.pk}"
                code = _unique_code(base, existing_codes)
                if org.code != code:
                    self._log_change("Organization", org.pk, org.name, "code", org.code, code, dry_run)
                    if not dry_run:
                        org.code = code
                    existing_codes.add(code)
                    dirty = True

            if not skip_uuids and (force or not org.org_uuid):
                new_uuid = _uuid_mod.uuid4()
                self._log_change("Organization", org.pk, org.name, "org_uuid", org.org_uuid, new_uuid, dry_run)
                if not dry_run:
                    org.org_uuid = new_uuid
                dirty = True

            if dirty:
                if not dry_run:
                    fields_to_save = []
                    if not skip_codes:
                        fields_to_save.append("code")
                    if not skip_uuids:
                        fields_to_save.append("org_uuid")
                    org.save(update_fields=fields_to_save)
                updated += 1

        self.stderr.write(
            self.style.SUCCESS(
                f"Organisations: {updated} record(s) {'would be ' if dry_run else ''}updated."
            )
        )

    def _backfill_spaces(self, skip_codes, skip_uuids, force, dry_run):
        spaces = list(Space.objects.select_related("org").order_by("pk"))
        if not spaces:
            self.stderr.write("No spaces found.")
            return

        existing_codes = set(
            Space.objects.exclude(code__isnull=True)
            .exclude(code="")
            .values_list("code", flat=True)
        )

        updated = 0
        for space in spaces:
            dirty = False

            if not skip_codes and (force or not space.code):
                base = _slug_to_code(space.slug) if space.slug else f"SPACE_{space.pk}"
                code = _unique_code(base, existing_codes)
                if space.code != code:
                    self._log_change("Space", space.pk, space.name, "code", space.code, code, dry_run)
                    if not dry_run:
                        space.code = code
                    existing_codes.add(code)
                    dirty = True

            if not skip_uuids and (force or not space.space_uuid):
                new_uuid = _uuid_mod.uuid4()
                self._log_change("Space", space.pk, space.name, "space_uuid", space.space_uuid, new_uuid, dry_run)
                if not dry_run:
                    space.space_uuid = new_uuid
                dirty = True

            if dirty:
                if not dry_run:
                    fields_to_save = []
                    if not skip_codes:
                        fields_to_save.append("code")
                    if not skip_uuids:
                        fields_to_save.append("space_uuid")
                    space.save(update_fields=fields_to_save)
                updated += 1

        self.stderr.write(
            self.style.SUCCESS(
                f"Spaces: {updated} record(s) {'would be ' if dry_run else ''}updated."
            )
        )

    def _log_change(self, model_name, pk, name, field, old_val, new_val, dry_run):
        prefix = "[DRY-RUN] " if dry_run else ""
        self.stdout.write(
            f"{prefix}{model_name} pk={pk} '{name}': {field} "
            f"{old_val!r} → {new_val!r}"
        )
