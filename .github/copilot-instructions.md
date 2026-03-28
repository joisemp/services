# Project Guidelines

## Code Style
- Use Django class-based views and keep role-specific logic in matching role modules.
- Use `BootstrapFormMixin` for Django forms unless a form intentionally needs custom rendering.
- Use `select_related()` / `prefetch_related()` in list/detail views that render related data.
- Keep model slugs/code generation aligned with `src/config/utils.py` helpers.
- For styles, create page-level `style.scss` and compile to colocated `style.css`; avoid introducing raw CSS-only pages.

## Architecture
- Core authentication and user domain live in `src/core/`.
- Issue workflows live in `src/issue_management/` with role-segmented routing:
  - role URLs: `src/issue_management/role_urls/`
  - role views: `src/issue_management/views/{role}.py`
  - role templates: `src/templates/{role}/issue_management/`
- Inventory workflows live in `src/inventory/` with the same role-segmented routing pattern:
  - role URLs: `src/inventory/role_urls/`
  - role views: `src/inventory/views/{role}.py`
  - role templates: `src/templates/{role}/inventory/`
- Shared issue features for all authenticated roles belong in `src/issue_management/views/common.py` and are routed from `src/issue_management/urls.py` (not `role_urls`).
- The system is multi-tenant: non-superusers are organization-scoped.

## Build and Test
- Preferred dev runtime:
  - `docker-compose up`
- Django commands (inside app container):
  - `docker exec -it sfs-services-dev-container python manage.py makemigrations`
  - `docker exec -it sfs-services-dev-container python manage.py migrate`
  - `docker exec -it sfs-services-dev-container python manage.py createsuperuser`
  - `docker exec -it sfs-services-dev-container python manage.py check`
- Container names:
  - app: `sfs-services-dev-container`
  - db: `sfs-services-dev-postgres-container`
- Tests:
  - `docker exec -it sfs-services-dev-container python manage.py test`

## Conventions
- Authentication rules are strict:
  - `general_user`: phone-only/passwordless flow
  - other roles: email/password flow (optional PIN flow where supported)
- User creation must follow `UserManager.create_user()` invariants in `src/core/models.py`:
  - org and phone required for non-superusers
  - `auth_method` derived from role
- Issue/task entities should preserve slug and activity-tracking patterns used in `src/issue_management/models.py` and `src/issue_management/signals.py`.
- Public media paths should remain under `media/public/` so storage ACL behavior in `src/config/storages.py` remains correct.

## Pitfalls
- Missing `src/config/.env` breaks startup and notifications; ensure required `FIREBASE_*`, `SECRET_KEY`, and `ENVIRONMENT` values exist.
- Run migrations in containerized workflow before validating UI behavior.
- After editing SCSS, compile to CSS before considering style changes complete.

## Key References
- Project overview and setup: `README.md`
- Firebase setup and improvements:
  - `docs/FIREBASE_PUSH_NOTIFICATIONS_SETUP.md`
  - `docs/FIREBASE_NOTIFICATIONS_IMPROVEMENTS.md`
- Image processing and storage behavior: `docs/IMAGE_HANDLING_COMPLETE_GUIDE.md`
- Form submit behavior and anti-double-submit utility: `docs/FORM_SUBMIT_HANDLER_USAGE.md`
- Performance reporting:
  - `docs/PERFORMANCE_REPORT_QUICKSTART.md`
  - `docs/PERFORMANCE_REPORT_FEATURE.md`

## Key Files
- Settings/env/storage: `src/config/settings.py`, `src/config/storages.py`, `src/config/utils.py`
- Auth and user model: `src/core/backends.py`, `src/core/models.py`
- Issue domain and shared views: `src/issue_management/models.py`, `src/issue_management/views/common.py`, `src/issue_management/signals.py`
- Base templates/layout: `src/templates/base.html`, `src/templates/sidebar_base.html`
