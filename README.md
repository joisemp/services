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

### CSS/SCSS

- **Always create SCSS files** for page-specific styles (not raw CSS)
- **Page-specific folders**: Each page gets its own folder (e.g., `issue_list/`, `issue_detail/`)
- **Compilation**: SCSS files must be manually compiled to CSS in the same folder
- **Import base styles**:
  - `@use '../_base'` for basic navbar/header styles
  - `@use '../../_sidebar_base'` for full sidebar layout
- **Color variables**: Use variables from `static/styles/_colors.scss`

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

