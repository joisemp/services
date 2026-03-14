"""
Tests for SSO/shared-identity groundwork in the core app.

Covers:
  - New model fields (code, org_uuid, space_uuid, auth_sub, active_space_uuid)
  - Uniqueness enforcement at the DB/model level
  - Admin form validation for code and uuid uniqueness
  - backfill_codes management command
  - backfill_uuids management command
  - export_org_space_map management command
  - import_org_space_map management command (including a full export→import cycle)
"""

import json
import uuid
from io import StringIO

from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase

from core.models import Organization, Space, User
from core.admin import OrganizationAdminForm, SpaceAdminForm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_org(name="Test Org", code=None, org_uuid=None):
    return Organization.objects.create(
        name=name,
        code=code,
        org_uuid=org_uuid,
    )


def make_space(org, name="Test Space", code=None, space_uuid=None):
    return Space.objects.create(
        name=name,
        org=org,
        code=code,
        space_uuid=space_uuid,
    )


# ---------------------------------------------------------------------------
# Model field tests
# ---------------------------------------------------------------------------

class OrganizationFieldTests(TestCase):
    def test_code_nullable_by_default(self):
        org = make_org(name="No Code Org")
        self.assertIsNone(org.code)

    def test_org_uuid_nullable_by_default(self):
        org = make_org(name="No UUID Org")
        self.assertIsNone(org.org_uuid)

    def test_code_can_be_set(self):
        org = make_org(name="Coded Org", code="MY-ORG")
        self.assertEqual(org.code, "MY-ORG")

    def test_org_uuid_can_be_set(self):
        uid = uuid.uuid4()
        org = make_org(name="UUID Org", org_uuid=uid)
        self.assertEqual(org.org_uuid, uid)

    def test_code_unique_constraint(self):
        make_org(name="Org A", code="UNIQUE-CODE")
        with self.assertRaises(IntegrityError):
            make_org(name="Org B", code="UNIQUE-CODE")

    def test_org_uuid_unique_constraint(self):
        uid = uuid.uuid4()
        make_org(name="Org A", org_uuid=uid)
        with self.assertRaises(IntegrityError):
            make_org(name="Org B", org_uuid=uid)

    def test_multiple_orgs_can_have_null_code(self):
        make_org(name="Org Null 1", code=None)
        make_org(name="Org Null 2", code=None)
        self.assertEqual(Organization.objects.filter(code__isnull=True).count(), 2)

    def test_multiple_orgs_can_have_null_uuid(self):
        make_org(name="Org Null UUID 1")
        make_org(name="Org Null UUID 2")
        self.assertEqual(Organization.objects.filter(org_uuid__isnull=True).count(), 2)


class SpaceFieldTests(TestCase):
    def setUp(self):
        self.org = make_org(name="Parent Org", code="PARENT")

    def test_code_nullable_by_default(self):
        space = make_space(self.org)
        self.assertIsNone(space.code)

    def test_space_uuid_nullable_by_default(self):
        space = make_space(self.org)
        self.assertIsNone(space.space_uuid)

    def test_code_can_be_set(self):
        space = make_space(self.org, code="MY-SPACE")
        self.assertEqual(space.code, "MY-SPACE")

    def test_space_uuid_can_be_set(self):
        uid = uuid.uuid4()
        space = make_space(self.org, space_uuid=uid)
        self.assertEqual(space.space_uuid, uid)

    def test_code_globally_unique(self):
        """Space.code is unique across all orgs, not just within one org."""
        org2 = make_org(name="Other Org", code="OTHER")
        make_space(self.org, name="Space A", code="GLOBAL-CODE")
        with self.assertRaises(IntegrityError):
            make_space(org2, name="Space B", code="GLOBAL-CODE")

    def test_space_uuid_unique(self):
        uid = uuid.uuid4()
        make_space(self.org, name="Space A", space_uuid=uid)
        with self.assertRaises(IntegrityError):
            make_space(self.org, name="Space B", space_uuid=uid)

    def test_multiple_spaces_can_have_null_code(self):
        make_space(self.org, name="Space 1", code=None)
        make_space(self.org, name="Space 2", code=None)
        self.assertEqual(Space.objects.filter(code__isnull=True).count(), 2)


class UserSSOFieldTests(TestCase):
    """Tests for the new auth_sub and active_space_uuid fields on User."""

    def _make_user(self, phone="+10000000001", **kwargs):
        org = Organization.objects.create(name=f"User Org {phone}")
        return User.objects.create_user(
            phone_number=phone,
            user_type="general_user",
            organization=org,
            **kwargs,
        )

    def test_auth_sub_nullable(self):
        user = self._make_user()
        self.assertIsNone(user.auth_sub)

    def test_active_space_uuid_nullable(self):
        user = self._make_user()
        self.assertIsNone(user.active_space_uuid)

    def test_auth_sub_can_be_set(self):
        uid = uuid.uuid4()
        user = self._make_user()
        user.auth_sub = uid
        user.save(skip_validation=True)
        user.refresh_from_db()
        self.assertEqual(user.auth_sub, uid)

    def test_auth_sub_unique(self):
        uid = uuid.uuid4()
        user1 = self._make_user(phone="+10000000010")
        user1.auth_sub = uid
        user1.save(skip_validation=True)

        user2 = self._make_user(phone="+10000000011")
        user2.auth_sub = uid
        with self.assertRaises(IntegrityError):
            user2.save(skip_validation=True)


# ---------------------------------------------------------------------------
# Admin form validation tests
# ---------------------------------------------------------------------------

class OrganizationAdminFormTests(TestCase):
    def test_valid_form_without_code(self):
        form = OrganizationAdminForm(data={"name": "New Org", "slug": ""})
        self.assertTrue(form.is_valid(), form.errors)

    def test_duplicate_code_rejected(self):
        make_org(name="Existing Org", code="DUP-CODE")
        form = OrganizationAdminForm(
            data={"name": "New Org", "code": "DUP-CODE", "slug": "new-org"}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("code", form.errors)

    def test_same_code_allowed_on_own_record(self):
        org = make_org(name="My Org", code="MY-CODE")
        form = OrganizationAdminForm(
            instance=org,
            data={"name": "My Org", "code": "MY-CODE", "slug": org.slug},
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_duplicate_org_uuid_rejected(self):
        uid = uuid.uuid4()
        make_org(name="Existing Org", org_uuid=uid)
        form = OrganizationAdminForm(
            data={"name": "New Org", "org_uuid": str(uid), "slug": "new-org"}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("org_uuid", form.errors)

    def test_same_uuid_allowed_on_own_record(self):
        uid = uuid.uuid4()
        org = make_org(name="My Org", org_uuid=uid)
        form = OrganizationAdminForm(
            instance=org,
            data={"name": "My Org", "org_uuid": str(uid), "slug": org.slug},
        )
        self.assertTrue(form.is_valid(), form.errors)


class SpaceAdminFormTests(TestCase):
    def setUp(self):
        self.org = make_org(name="Parent", code="PAR")

    def test_valid_form_without_code(self):
        form = SpaceAdminForm(
            data={"name": "New Space", "org": self.org.pk, "slug": ""}
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_duplicate_code_rejected(self):
        make_space(self.org, name="Existing Space", code="DUP-SPACE")
        form = SpaceAdminForm(
            data={
                "name": "New Space",
                "org": self.org.pk,
                "code": "DUP-SPACE",
                "slug": "new-space",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("code", form.errors)

    def test_same_code_allowed_on_own_record(self):
        space = make_space(self.org, name="My Space", code="MY-SPACE")
        form = SpaceAdminForm(
            instance=space,
            data={
                "name": "My Space",
                "org": self.org.pk,
                "code": "MY-SPACE",
                "slug": space.slug,
            },
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_duplicate_space_uuid_rejected(self):
        uid = uuid.uuid4()
        make_space(self.org, name="Existing Space", space_uuid=uid)
        form = SpaceAdminForm(
            data={
                "name": "New Space",
                "org": self.org.pk,
                "space_uuid": str(uid),
                "slug": "new-space-2",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("space_uuid", form.errors)


# ---------------------------------------------------------------------------
# backfill_codes command tests
# ---------------------------------------------------------------------------

class BackfillCodesCommandTests(TestCase):
    def _run(self, *args, **kwargs):
        out = StringIO()
        call_command("backfill_codes", *args, stdout=out, **kwargs)
        return out.getvalue()

    def test_backfills_org_codes_from_slug(self):
        org = make_org(name="My Organisation")
        self.assertIsNone(org.code)
        self._run("--model", "org")
        org.refresh_from_db()
        self.assertIsNotNone(org.code)
        self.assertTrue(len(org.code) > 0)

    def test_backfills_space_codes_from_slug(self):
        org = make_org(name="Org For Space", code="OFS")
        space = make_space(org, name="My Space")
        self.assertIsNone(space.code)
        self._run("--model", "space")
        space.refresh_from_db()
        self.assertIsNotNone(space.code)

    def test_dry_run_does_not_save(self):
        org = make_org(name="Dry Run Org")
        self._run("--model", "org", "--dry-run")
        org.refresh_from_db()
        self.assertIsNone(org.code)

    def test_does_not_overwrite_existing_codes(self):
        org = make_org(name="Already Coded", code="EXISTING")
        self._run("--model", "org")
        org.refresh_from_db()
        self.assertEqual(org.code, "EXISTING")

    def test_overwrite_flag_changes_existing_code(self):
        org = make_org(name="Overwrite Me", code="OLD-CODE")
        Organization.objects.filter(pk=org.pk).update(slug="overwrite-me")
        self._run("--model", "org", "--overwrite")
        org.refresh_from_db()
        self.assertNotEqual(org.code, "OLD-CODE")

    def test_generated_codes_are_unique_across_orgs(self):
        # Create multiple orgs without codes; backfill should assign unique codes
        # even if their auto-generated slugs happen to be very similar.
        orgs = [Organization.objects.create(name=f"Similar Name {i}") for i in range(5)]
        self._run("--model", "org")
        codes = []
        for org in orgs:
            org.refresh_from_db()
            codes.append(org.code)
        # All codes must be set and distinct
        self.assertEqual(len(codes), len(set(codes)))

    def test_output_contains_changed_records(self):
        make_org(name="Output Org")
        out = self._run("--model", "org")
        self.assertIn("Output Org", out)

    def test_backfills_both_by_default(self):
        org = make_org(name="Both Org")
        space = make_space(org, name="Both Space")
        self._run()
        org.refresh_from_db()
        space.refresh_from_db()
        self.assertIsNotNone(org.code)
        self.assertIsNotNone(space.code)


# ---------------------------------------------------------------------------
# backfill_uuids command tests
# ---------------------------------------------------------------------------

class BackfillUUIDsCommandTests(TestCase):
    def _run(self, *args, **kwargs):
        out = StringIO()
        call_command("backfill_uuids", *args, stdout=out, **kwargs)
        return out.getvalue()

    def test_assigns_uuid_to_org(self):
        org = make_org(name="UUID Org", code="UUID-ORG")
        self.assertIsNone(org.org_uuid)
        self._run("--model", "org")
        org.refresh_from_db()
        self.assertIsNotNone(org.org_uuid)

    def test_assigns_uuid_to_space(self):
        org = make_org(name="UUID Space Org", code="USO")
        space = make_space(org, name="UUID Space", code="US")
        self.assertIsNone(space.space_uuid)
        self._run("--model", "space")
        space.refresh_from_db()
        self.assertIsNotNone(space.space_uuid)

    def test_dry_run_does_not_save(self):
        org = make_org(name="Dry UUID Org", code="DRY-UUID")
        self._run("--model", "org", "--dry-run")
        org.refresh_from_db()
        self.assertIsNone(org.org_uuid)

    def test_does_not_overwrite_existing_uuid(self):
        uid = uuid.uuid4()
        org = make_org(name="Has UUID", code="HAS-UUID", org_uuid=uid)
        self._run("--model", "org")
        org.refresh_from_db()
        self.assertEqual(org.org_uuid, uid)

    def test_overwrite_replaces_uuid(self):
        uid = uuid.uuid4()
        org = make_org(name="Replace UUID", code="REP-UUID", org_uuid=uid)
        self._run("--model", "org", "--overwrite")
        org.refresh_from_db()
        self.assertNotEqual(org.org_uuid, uid)


# ---------------------------------------------------------------------------
# export_org_space_map command tests
# ---------------------------------------------------------------------------

class ExportOrgSpaceMapCommandTests(TestCase):
    def _run(self, *args, **kwargs):
        out = StringIO()
        call_command("export_org_space_map", *args, stdout=out, **kwargs)
        return out.getvalue()

    def setUp(self):
        self.org = make_org(name="Export Org", code="EXP-ORG", org_uuid=uuid.uuid4())
        self.space = make_space(
            self.org, name="Export Space", code="EXP-SPC", space_uuid=uuid.uuid4()
        )

    def test_outputs_valid_json(self):
        output = self._run()
        data = json.loads(output)
        self.assertIn("organisations", data)
        self.assertIn("spaces", data)

    def test_contains_org_fields(self):
        output = self._run()
        data = json.loads(output)
        orgs = {o["code"]: o for o in data["organisations"]}
        self.assertIn("EXP-ORG", orgs)
        self.assertEqual(orgs["EXP-ORG"]["name"], "Export Org")
        self.assertIsNotNone(orgs["EXP-ORG"]["org_uuid"])

    def test_contains_space_fields(self):
        output = self._run()
        data = json.loads(output)
        spaces = {s["code"]: s for s in data["spaces"]}
        self.assertIn("EXP-SPC", spaces)
        self.assertEqual(spaces["EXP-SPC"]["org_code"], "EXP-ORG")
        self.assertIsNotNone(spaces["EXP-SPC"]["space_uuid"])

    def test_only_coded_flag(self):
        make_org(name="No Code Org")
        output = self._run("--only-coded")
        data = json.loads(output)
        for o in data["organisations"]:
            self.assertIsNotNone(o["code"])

    def test_output_to_file(self):
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            out = StringIO()
            call_command("export_org_space_map", "--output", path, stdout=out)
            self.assertTrue(os.path.exists(path))
            with open(path) as fh:
                data = json.load(fh)
            self.assertIn("organisations", data)
        finally:
            os.unlink(path)

    def test_null_uuid_serialised_as_null(self):
        make_org(name="Null UUID Org", code="NULL-UUID")
        output = self._run()
        data = json.loads(output)
        for o in data["organisations"]:
            if o["code"] == "NULL-UUID":
                self.assertIsNone(o["org_uuid"])


# ---------------------------------------------------------------------------
# import_org_space_map command tests
# ---------------------------------------------------------------------------

class ImportOrgSpaceMapCommandTests(TestCase):
    def _run(self, path, *args, **kwargs):
        out = StringIO()
        call_command("import_org_space_map", path, *args, stdout=out, **kwargs)
        return out.getvalue()

    def _write_json(self, data):
        import tempfile
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump(data, f)
        f.flush()
        return f.name

    def setUp(self):
        self.org = make_org(name="Import Org", code="IMP-ORG")
        self.space = make_space(self.org, name="Import Space", code="IMP-SPC")

    def test_sets_org_uuid_by_code(self):
        uid = uuid.uuid4()
        path = self._write_json(
            {"organisations": [{"code": "IMP-ORG", "org_uuid": str(uid)}]}
        )
        self._run(path)
        self.org.refresh_from_db()
        self.assertEqual(self.org.org_uuid, uid)

    def test_sets_space_uuid_by_code(self):
        uid = uuid.uuid4()
        path = self._write_json(
            {"spaces": [{"code": "IMP-SPC", "space_uuid": str(uid)}]}
        )
        self._run(path)
        self.space.refresh_from_db()
        self.assertEqual(self.space.space_uuid, uid)

    def test_dry_run_does_not_save(self):
        uid = uuid.uuid4()
        path = self._write_json(
            {"organisations": [{"code": "IMP-ORG", "org_uuid": str(uid)}]}
        )
        self._run(path, "--dry-run")
        self.org.refresh_from_db()
        self.assertIsNone(self.org.org_uuid)

    def test_unknown_code_skipped_with_warning(self):
        uid = uuid.uuid4()
        path = self._write_json(
            {"organisations": [{"code": "UNKNOWN-CODE", "org_uuid": str(uid)}]}
        )
        out = self._run(path)
        self.assertIn("not found locally", out)

    def test_unchanged_uuid_not_written(self):
        uid = uuid.uuid4()
        Organization.objects.filter(pk=self.org.pk).update(org_uuid=uid)
        path = self._write_json(
            {"organisations": [{"code": "IMP-ORG", "org_uuid": str(uid)}]}
        )
        self._run(path)
        out = self._run(path)
        self.assertIn("0 organisation(s)", out)

    def test_invalid_json_raises_error(self):
        import tempfile
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        f.write("not json{{{")
        f.flush()
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            self._run(f.name)

    def test_missing_file_raises_error(self):
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            self._run("/nonexistent/path/file.json")

    def test_missing_code_in_record_skipped(self):
        uid = uuid.uuid4()
        path = self._write_json(
            {"organisations": [{"org_uuid": str(uid)}]}
        )
        out = self._run(path)
        self.assertIn("missing", out.lower())

    # ----------------------------------------------------------------
    # Full export → import cycle
    # ----------------------------------------------------------------

    def test_export_import_round_trip(self):
        """Export data, then import it back and verify UUIDs are preserved."""
        import tempfile, os

        org_uid = uuid.uuid4()
        space_uid = uuid.uuid4()
        Organization.objects.filter(pk=self.org.pk).update(org_uuid=org_uid)
        Space.objects.filter(pk=self.space.pk).update(space_uuid=space_uid)

        # 1. Export to a file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as export_file:
            export_path = export_file.name

        try:
            out = StringIO()
            call_command("export_org_space_map", "--output", export_path, stdout=out)

            # 2. Clear UUIDs
            Organization.objects.filter(pk=self.org.pk).update(org_uuid=None)
            Space.objects.filter(pk=self.space.pk).update(space_uuid=None)

            # 3. Import back
            self._run(export_path)

            # 4. Verify
            self.org.refresh_from_db()
            self.space.refresh_from_db()
            self.assertEqual(self.org.org_uuid, org_uid)
            self.assertEqual(self.space.space_uuid, space_uid)
        finally:
            if os.path.exists(export_path):
                os.unlink(export_path)
