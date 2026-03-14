"""
Management command: export_identity_data

Exports Organizations and Spaces to JSON or CSV for use when bootstrapping
an external Auth/SSO service.

Usage examples:
    # Export both orgs and spaces as JSON (default)
    python manage.py export_identity_data

    # Export only organisations as CSV to a file
    python manage.py export_identity_data --model org --format csv --output /tmp/orgs.csv

    # Export spaces as JSON to stdout
    python manage.py export_identity_data --model space --format json

Options:
    --model     {org,space,all}   Which models to export (default: all)
    --format    {json,csv}        Output format (default: json)
    --output    PATH              File path to write output to (default: stdout)
"""

import csv
import io
import json
import sys

from django.core.management.base import BaseCommand, CommandError

from core.models import Organization, Space


def _org_row(org):
    return {
        "model": "organization",
        "legacy_id": org.pk,
        "name": org.name,
        "slug": org.slug,
        "code": org.code or "",
        "org_uuid": str(org.org_uuid) if org.org_uuid else "",
    }


def _space_row(space):
    return {
        "model": "space",
        "legacy_id": space.pk,
        "name": space.name,
        "slug": space.slug,
        "code": space.code or "",
        "space_uuid": str(space.space_uuid) if space.space_uuid else "",
        "org_legacy_id": space.org_id,
        "org_name": space.org.name,
        "org_code": space.org.code or "",
    }


_ORG_CSV_FIELDS = ["model", "legacy_id", "name", "slug", "code", "org_uuid"]
_SPACE_CSV_FIELDS = [
    "model", "legacy_id", "name", "slug", "code", "space_uuid",
    "org_legacy_id", "org_name", "org_code",
]


class Command(BaseCommand):
    help = (
        "Export Organizations and/or Spaces to JSON or CSV for Auth/SSO bootstrapping."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--model",
            choices=["org", "space", "all"],
            default="all",
            help="Which model(s) to export (default: all).",
        )
        parser.add_argument(
            "--format",
            choices=["json", "csv"],
            default="json",
            dest="output_format",
            help="Output format: json or csv (default: json).",
        )
        parser.add_argument(
            "--output",
            default=None,
            help="File path to write output to. Omit to write to stdout.",
        )

    def handle(self, *args, **options):
        model = options["model"]
        output_format = options["output_format"]
        output_path = options["output"]

        rows = []

        if model in ("org", "all"):
            for org in Organization.objects.all().order_by("pk"):
                rows.append(_org_row(org))

        if model in ("space", "all"):
            for space in Space.objects.select_related("org").order_by("pk"):
                rows.append(_space_row(space))

        if not rows:
            self.stderr.write(self.style.WARNING("No data found to export."))
            return

        content = self._render(rows, output_format, model)

        if output_path:
            with open(output_path, "w", encoding="utf-8", newline="") as fh:
                fh.write(content)
            self.stderr.write(
                self.style.SUCCESS(
                    f"Exported {len(rows)} record(s) to '{output_path}'."
                )
            )
        else:
            self.stdout.write(content)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _render(self, rows, output_format, model):
        if output_format == "json":
            return json.dumps(rows, indent=2, ensure_ascii=False)

        # CSV — choose column set based on what we're exporting
        if model == "org":
            fieldnames = _ORG_CSV_FIELDS
        elif model == "space":
            fieldnames = _SPACE_CSV_FIELDS
        else:
            # "all": union of both field sets, with org-only fields first
            fieldnames = list(dict.fromkeys(_ORG_CSV_FIELDS + _SPACE_CSV_FIELDS))

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue()
