"""
Management command: export_org_space_map
=========================================
Exports Organisation and Space data as a JSON file suitable for importing into
the Auth service or another app (e.g. BusNest) to establish cross-system UUID
mapping.

The export intentionally omits sensitive data and keeps only the fields
needed for SSO linking:

  * Organisation: id, name, slug, code, org_uuid
  * Space: id, name, slug, code, space_uuid, org_code (parent org code)

Usage
-----
    # Export to stdout (default)
    python manage.py export_org_space_map

    # Export to a file
    python manage.py export_org_space_map --output /tmp/org_space_map.json

    # Export only organisations with a code set (skip incomplete records)
    python manage.py export_org_space_map --only-coded

Output format (JSON)
--------------------
{
  "exported_at": "2025-01-01T00:00:00.000000",
  "source": "services",
  "organisations": [
    {
      "id": 1,
      "name": "Acme Corp",
      "slug": "acme-corp",
      "code": "ACME",
      "org_uuid": "…"          // null if not yet assigned
    },
    …
  ],
  "spaces": [
    {
      "id": 42,
      "name": "Main Campus",
      "slug": "main-campus",
      "code": "ACME-MAIN",
      "space_uuid": "…",       // null if not yet assigned
      "org_code": "ACME"       // links back to parent organisation
    },
    …
  ]
}
"""

import json
import sys
from datetime import datetime, timezone

from django.core.management.base import BaseCommand

from core.models import Organization, Space


class Command(BaseCommand):
    help = (
        "Export Organisation and Space data as JSON for cross-system UUID mapping "
        "(e.g. for import into the Auth service or BusNest)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default=None,
            metavar="FILE",
            help="Path to write JSON output.  Defaults to stdout.",
        )
        parser.add_argument(
            "--only-coded",
            action="store_true",
            default=False,
            help="Only export records that already have a code set.",
        )

    def handle(self, *args, **options):
        output_path = options["output"]
        only_coded = options["only_coded"]

        org_qs = Organization.objects.all().order_by("pk")
        space_qs = Space.objects.select_related("org").all().order_by("pk")

        if only_coded:
            org_qs = org_qs.exclude(code__isnull=True).exclude(code="")
            space_qs = space_qs.exclude(code__isnull=True).exclude(code="")

        organisations = [
            {
                "id": org.pk,
                "name": org.name,
                "slug": org.slug,
                "code": org.code,
                "org_uuid": str(org.org_uuid) if org.org_uuid else None,
            }
            for org in org_qs
        ]

        spaces = [
            {
                "id": space.pk,
                "name": space.name,
                "slug": space.slug,
                "code": space.code,
                "space_uuid": str(space.space_uuid) if space.space_uuid else None,
                "org_code": space.org.code,
            }
            for space in space_qs
        ]

        payload = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "source": "services",
            "organisations": organisations,
            "spaces": spaces,
        }

        json_output = json.dumps(payload, indent=2)

        if output_path:
            with open(output_path, "w", encoding="utf-8") as fh:
                fh.write(json_output)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Exported {len(organisations)} organisation(s) and "
                    f"{len(spaces)} space(s) to {output_path}"
                )
            )
        else:
            self.stdout.write(json_output)
