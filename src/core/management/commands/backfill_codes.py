"""
Management command: backfill_codes
===================================
Populates the ``code`` field on Organisation and/or Space records that do not
already have one.  The generated value is derived from the existing ``slug``
field so that it is human-readable and easy to understand.

Usage
-----
    # Backfill both organisations and spaces (default)
    python manage.py backfill_codes

    # Backfill organisations only
    python manage.py backfill_codes --model org

    # Backfill spaces only
    python manage.py backfill_codes --model space

    # Preview changes without saving (dry-run)
    python manage.py backfill_codes --dry-run

    # Overwrite codes that are already set
    python manage.py backfill_codes --overwrite

Reversibility
-------------
This command is fully non-destructive by default: it only fills *blank* codes.
To revert generated codes set them back to NULL via the Django admin or with:

    python manage.py shell -c "
    from core.models import Organization, Space
    Organization.objects.all().update(code=None)
    Space.objects.all().update(code=None)
    "

Notes
-----
* Generated codes are trimmed to 50 characters to fit the field max_length.
* Uniqueness is guaranteed within a single run by appending a counter when a
  collision is detected.
* The command outputs one line per changed record for easy auditing.
"""

from django.core.management.base import BaseCommand, CommandError

from core.models import Organization, Space


def _make_code(slug, existing_codes, max_length=50):
    """Return a unique code derived from *slug*, not in *existing_codes*."""
    base = slug[:max_length]
    candidate = base
    counter = 2
    while candidate in existing_codes:
        suffix = f"-{counter}"
        candidate = base[: max_length - len(suffix)] + suffix
        counter += 1
    return candidate


class Command(BaseCommand):
    help = (
        "Backfill the 'code' field on Organisation and Space records from their "
        "slugs.  Only records with an empty code are updated unless --overwrite is given."
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
            help="Overwrite codes that are already set.",
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
        self.stdout.write("Backfilling Organisation codes …")

        qs = Organization.objects.all()
        if not overwrite:
            qs = qs.filter(code__isnull=True)

        existing_codes = set(
            Organization.objects.exclude(code__isnull=True)
            .exclude(code="")
            .values_list("code", flat=True)
        )

        updated = 0
        for org in qs:
            new_code = _make_code(org.slug, existing_codes)
            existing_codes.add(new_code)
            self.stdout.write(f"  Organisation [{org.pk}] {org.name!r}: {org.code!r} → {new_code!r}")
            if not dry_run:
                Organization.objects.filter(pk=org.pk).update(code=new_code)
            updated += 1

        if updated == 0:
            self.stdout.write(self.style.SUCCESS("  No organisations needed backfilling."))
        else:
            verb = "Would update" if dry_run else "Updated"
            self.stdout.write(self.style.SUCCESS(f"  {verb} {updated} organisation(s)."))

    def _backfill_spaces(self, *, dry_run, overwrite):
        self.stdout.write("Backfilling Space codes …")

        qs = Space.objects.select_related("org").all()
        if not overwrite:
            qs = qs.filter(code__isnull=True)

        existing_codes = set(
            Space.objects.exclude(code__isnull=True)
            .exclude(code="")
            .values_list("code", flat=True)
        )

        updated = 0
        for space in qs:
            new_code = _make_code(space.slug, existing_codes)
            existing_codes.add(new_code)
            self.stdout.write(
                f"  Space [{space.pk}] {space.name!r} (org: {space.org.name!r}): "
                f"{space.code!r} → {new_code!r}"
            )
            if not dry_run:
                Space.objects.filter(pk=space.pk).update(code=new_code)
            updated += 1

        if updated == 0:
            self.stdout.write(self.style.SUCCESS("  No spaces needed backfilling."))
        else:
            verb = "Would update" if dry_run else "Updated"
            self.stdout.write(self.style.SUCCESS(f"  {verb} {updated} space(s)."))
