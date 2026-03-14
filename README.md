# Services

A Django 5.2-based issue management system with role-based access control and multi-tenant organization support.

## Overview

This project provides a comprehensive issue tracking platform featuring:

- **Two-Tier Authentication System**: 
  - **General Users**: Passwordless phone-only authentication (just enter phone number to login)
  - **Admin Roles**: Email + password authentication for central_admin, space_admin, maintainer, supervisor, and reviewer roles
- **Role-Based Access Control**: Six distinct user roles with specialized workflows and URL namespaces
- **Multi-Tenant Architecture**: Organization and space-based issue management with hierarchical access controls
- **Work Task Management**: Detailed task tracking with assignment, progress monitoring, completion notes, and external sharing via secure tokens
- **Media Support**: Issue documentation with voice recordings and multiple image uploads (up to 3 per issue)
- **Issue Status Flow**: `open` → `assigned` → `in_progress` → `resolved`/`escalated` → `closed`/`cancelled`

## Tech Stack

- **Backend**: Django 5.2, PostgreSQL
- **Frontend**: Bootstrap 5, HTMX
- **Storage**: DigitalOcean Spaces (S3-compatible) for production, local storage for development
- **Static Files**: WhiteNoise
- **Environment Management**: django-environ
- **Key Dependencies**: django-storages, psycopg2-binary, pillow

## Project Structure

```
services/
├── src/
│   ├── config/              # Project configuration and utilities
│   │   ├── settings.py      # Environment-based settings
│   │   ├── utils.py         # Slug/code generation utilities
│   │   ├── storages.py      # Custom S3 storage classes
│   │   └── mixins/          # Reusable form mixins (BootstrapFormMixin)
│   ├── core/                # Custom user model and authentication
│   │   ├── models.py        # Custom User, Organization, Space models
│   │   ├── backends.py      # DualAuthBackend (phone + email auth)
│   │   ├── forms.py         # Authentication forms
│   │   └── views.py         # Auth views
│   ├── issue_management/    # Issue tracking system
│   │   ├── models.py        # Issue, WorkTask, IssueImage, etc.
│   │   ├── forms.py         # Issue and task forms
│   │   ├── views/           # Role-specific view modules
│   │   └── role_urls/       # Role-based URL patterns
│   ├── dashboard/           # Dashboard views
│   ├── static/              # CSS, JS, images
│   │   └── styles/          # SCSS and compiled CSS (page-specific folders)
│   ├── templates/           # Django templates (role-based structure)
│   └── media/               # User-uploaded files (development)
├── docker-compose.yaml      # Development environment setup
└── README.md
```



## Architecture Details

### Custom User Authentication

The project uses a dual authentication system via `DualAuthBackend`:

- **General Users (`general_user`)**: Phone-only, passwordless authentication
  ```python
  # Authenticate with phone number only
  user = authenticate(phone_number="+1234567890")
  ```

- **All Other Roles**: Email + password required
  ```python
  # Authenticate with email and password
  user = authenticate(username="admin@example.com", password="secure_password")
  ```

**User Types**:
- `central_admin` - System-wide administration
- `space_admin` - Space-level administration
- `maintainer` - Issue maintenance and resolution
- `supervisor` - Issue oversight and escalation
- `reviewer` - Issue review and approval
- `general_user` - Issue reporting (phone-only auth)

### Role-Based URL Structure

URLs are organized by user role with parallel structures:

```
/issues/central-admin/    → Central admin workflows
/issues/space-admin/      → Space admin workflows
/issues/maintainer/       → Maintainer workflows
/issues/supervisor/       → Supervisor workflows
/issues/reviewer/         → Reviewer workflows
```

Each role has its own URL namespace, view module, and template directory.

### Issue Workflow

1. **Creation**: Users create issues with title, description, location, images, and voice recordings
2. **Assignment**: Issues are assigned to maintainers
3. **Work Tasks**: Maintainers create work tasks with assignees and due dates
4. **Progress Tracking**: Tasks move through status updates
5. **Completion**: Tasks are completed with resolution notes
6. **External Sharing**: Tasks can be shared with external users via secure tokens

### Media File Handling

- **Development**: Files stored locally in `src/media/public/`
- **Production**: Files uploaded to DigitalOcean Spaces (S3-compatible)
- **Image Uploads**: Up to 3 images per issue via form fields `image1`, `image2`, `image3`
- **Voice Recordings**: Audio files attached to issues

## Development Conventions

### Models

- Use `config.utils.generate_unique_slug()` for automatic slug generation with 4-char random codes
- All entities (except superusers) must be associated with an Organization
- Use descriptive `related_name` for reverse relationships

### Forms

- Inherit from `BootstrapFormMixin` for automatic Bootstrap 5 styling with error handling
- Handle multiple image uploads in `form_valid()` method

### Views

- Use Django Class-Based Views (CBVs)
- Optimize queries with `select_related()` and `prefetch_related()`
- Follow pattern: `slug_field = 'slug'` and `slug_url_kwarg = '{model}_slug'`

### Templates

- Template paths follow: `{role}/issue_management/{action}.html`
- Base templates: `base.html` (basic) and `sidebar_base.html` (with sidebar)


## SSO / Shared-Identity Groundwork

> **Status:** Phase 1 — additive fields only.  No authentication changes have been made.
> Existing FKs, integer primary keys, and all current workflows are fully preserved.

This section describes the identity fields added to `Organisation` and `Space` to prepare for
future cross-app SSO integration (Services ↔ BusNest ↔ Auth service).

### New fields

| Model | Field | Type | Meaning |
|---|---|---|---|
| `Organization` | `code` | `CharField(50)`, unique, nullable | Human-managed globally-unique identifier (e.g. `SFS-HYD`). Used as the stable match key when linking to the Auth service. |
| `Organization` | `org_uuid` | `UUIDField`, unique, nullable | Canonical UUID assigned by the Auth service after import. Null until Auth is live. |
| `Space` | `code` | `CharField(50)`, unique, nullable | Globally unique, human-managed identifier (e.g. `SFS-HYD-MAIN`). |
| `Space` | `space_uuid` | `UUIDField`, unique, nullable | Canonical UUID assigned by the Auth service after import. Null until Auth is live. |
| `User` | `auth_sub` | `UUIDField`, unique, nullable | SSO subject — the canonical user identifier issued by the Auth service. Null until SSO is enabled. |
| `User` | `active_space_uuid` | `UUIDField`, nullable | UUID of the user's currently active space. Mirrors the existing `active_space` FK. |

All new fields are **nullable** so existing records are unaffected.  Uniqueness is enforced at
the database level for non-null values.

### Field meanings and conventions

- **`code`** values are chosen by the platform administrator (e.g. `SFS-HYD`, `SFS-MUM-01`).  
  They must be globally unique across all organisations *and* globally unique across all spaces.  
  They are the primary match key used during export/import to the Auth service.

- **`org_uuid` / `space_uuid`** are assigned by the Auth service and written back via the
  `import_org_space_map` management command.  Do not edit them manually unless you are performing
  a controlled import.

- **`auth_sub`** will be set when SSO login is implemented.  It will contain the `sub` claim
  from the Auth service's OIDC/OAuth2 token.

- **`active_space_uuid`** mirrors `User.active_space` (FK) and will eventually replace it as the
  primary session-scoping key once SSO is enforced.

### Management commands

#### `backfill_codes`

Auto-populates `code` from the existing `slug` for records that do not already have one.

```bash
# Backfill both organisations and spaces
python manage.py backfill_codes

# Backfill organisations only
python manage.py backfill_codes --model org

# Backfill spaces only
python manage.py backfill_codes --model space

# Preview without saving
python manage.py backfill_codes --dry-run

# Overwrite existing codes
python manage.py backfill_codes --overwrite
```

**Reversibility:** to clear all auto-generated codes:

```python
from core.models import Organization, Space
Organization.objects.all().update(code=None)
Space.objects.all().update(code=None)
```

#### `backfill_uuids`

Assigns random placeholder UUIDs to records without one.  These are overwritten later by
`import_org_space_map` with the canonical Auth-service UUIDs.

```bash
python manage.py backfill_uuids           # both models
python manage.py backfill_uuids --model org
python manage.py backfill_uuids --dry-run
```

#### `export_org_space_map`

Exports `Organisation` and `Space` data as JSON for import into the Auth service or BusNest.

```bash
python manage.py export_org_space_map --output /tmp/services_export.json
# or print to stdout
python manage.py export_org_space_map
# export only records that have a code set
python manage.py export_org_space_map --only-coded --output /tmp/services_export.json
```

Output format:

```json
{
  "exported_at": "2025-01-01T12:00:00",
  "source": "services",
  "organisations": [
    { "id": 1, "name": "Acme Corp", "slug": "acme-corp", "code": "ACME", "org_uuid": "…" }
  ],
  "spaces": [
    { "id": 42, "name": "Main Campus", "slug": "main-campus", "code": "ACME-MAIN",
      "space_uuid": "…", "org_code": "ACME" }
  ]
}
```

#### `import_org_space_map`

Reads a JSON file from the Auth service and writes the canonical `org_uuid` / `space_uuid` back
into the local database, matching records by `code`.  Safe to re-run.

```bash
python manage.py import_org_space_map /tmp/auth_export.json
python manage.py import_org_space_map /tmp/auth_export.json --dry-run
python manage.py import_org_space_map /tmp/auth_export.json --verbose
```

### Recommended workflow (one-time setup before Auth goes live)

1. **Set codes** — edit each Organisation and Space in the Django admin and assign a unique
   human-readable code, or run `backfill_codes` to auto-populate from slugs.

2. **Verify uniqueness** — check via the admin list view (codes are shown in the list display).
   The admin form will reject duplicates with a clear error message.

3. **Export** — run `export_org_space_map --only-coded --output services_export.json` and share
   the file with the Auth service team.

4. **Receive canonical UUIDs** — the Auth service team returns a JSON file with `org_uuid` and
   `space_uuid` values assigned.

5. **Import** — run `import_org_space_map auth_export.json --dry-run` to preview, then without
   `--dry-run` to apply.

6. **Verify** — check the admin list view; `org_uuid` and `space_uuid` columns should now be
   populated.

### How to update or fix a code

1. Open the record in the Django admin.
2. Edit the `code` field.  The form will reject the new value if it collides with another record.
3. Save.

If you need to bulk-rename codes, use the shell:

```python
from core.models import Organization
org = Organization.objects.get(slug='old-slug')
org.code = 'NEW-CODE'
org.save()  # Django admin validation does NOT run here; ensure manual uniqueness check
```

Or via `update()` (bypasses model validation — use with care):

```python
Organization.objects.filter(slug='old-slug').update(code='NEW-CODE')
```

### Error handling

| Error | Cause | Fix |
|---|---|---|
| Admin form: *"A space with code X already exists"* | Duplicate code entered | Choose a different code |
| `import_org_space_map`: *"not found locally"* | Code in import file does not match any local record | Check for typos; run `backfill_codes` first |
| `import_org_space_map`: *"Invalid UUID"* | Malformed UUID in the import file | Fix the import file |

### SSO integration notes (future)

The following places in the codebase will need to be updated when SSO login is enabled.
They are marked with `# TODO(SSO):` comments in the source:

- `core/models.py` — `Organization.org_uuid` and `Space.space_uuid` should become non-null once
  all records have been linked to the Auth service.
- `core/models.py` — `User.active_space_uuid` will replace `User.active_space` (FK) as the
  primary session-scoping key.
- `core/models.py` — `User.auth_sub` will become required for all non-superuser logins.
- Login views (`core/views.py`) will need an SSO redirect path and OIDC callback.
- Issue and work-task queries should eventually filter by `space_uuid` instead of the integer
  `space` FK to allow cross-database scoping.

---



## License

This software is proprietary and confidential. All rights reserved by **SFS INSTITUTIONS, BENGALURU**.

**Usage Restrictions:**
- This software may **not** be used, copied, modified, distributed, or sold without prior written consent
- Unauthorized use, reverse-engineering, or distribution is strictly prohibited
- Any violation will result in immediate termination of access and potential legal action

For licensing inquiries and permission requests, please contact: **contact@sfsbusnest.in**

See the [LICENSE](LICENSE) file for complete terms and conditions.

---

© 2025 SFS INSTITUTIONS, BENGALURU - All Rights Reserved.

