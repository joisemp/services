"""
Migration: Add SSO/shared-identity fields to Organization, Space, and User.

All new fields are nullable so this migration is fully backward-compatible and
safe to apply without data loss or constraint violations.

Follow-up steps (after backfill):
  - Add unique constraint to Organization.code and Space.code.
  - Populate org_uuid / space_uuid for all existing rows.
"""

import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013_user_fcm_token"),
    ]

    operations = [
        # --- Organization ---
        migrations.AddField(
            model_name="organization",
            name="code",
            field=models.CharField(
                blank=True,
                null=True,
                max_length=50,
                help_text=(
                    "Globally unique, human-managed short code for this organisation "
                    "(e.g. 'ACME'). Unique constraint will be enforced after initial backfill."
                ),
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="org_uuid",
            field=models.UUIDField(
                blank=True,
                null=True,
                db_index=True,
                help_text="Canonical UUID for this organisation, used for cross-service identity.",
            ),
        ),
        # --- Space ---
        migrations.AddField(
            model_name="space",
            name="code",
            field=models.CharField(
                blank=True,
                null=True,
                max_length=50,
                help_text=(
                    "Globally unique, human-managed short code for this space "
                    "(e.g. 'ACME-HQ'). Unique constraint will be enforced after initial backfill."
                ),
            ),
        ),
        migrations.AddField(
            model_name="space",
            name="space_uuid",
            field=models.UUIDField(
                blank=True,
                null=True,
                db_index=True,
                help_text="Canonical UUID for this space, used for cross-service identity.",
            ),
        ),
        # --- User ---
        migrations.AddField(
            model_name="user",
            name="auth_sub",
            field=models.CharField(
                blank=True,
                null=True,
                max_length=255,
                db_index=True,
                help_text=(
                    "Stable subject identifier from the external Auth/SSO service "
                    "(e.g. Auth0 sub claim)."
                ),
            ),
        ),
    ]
