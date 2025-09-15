# Copilot Instructions for Services Project

## Project Overview
This is a Django-based issue management system with role-based access control. The project features a custom user authentication system supporting both phone (passwordless) and email authentication, and is designed around organizations and spaces for multi-tenant issue tracking.

## Architecture & Key Components

### Custom User Authentication (`core/models.py`)
- **Two-Tier Authentication System**:
  - **General Users**: Phone-only authentication (passwordless) - just enter phone number to login
  - **All Other Roles**: Email + password authentication required (`central_admin`, `space_admin`, `maintainer`, `supervisor`, `reviewer`)
- **Role-based User Types**: `central_admin`, `space_admin`, `maintainer`, `supervisor`, `reviewer`, `general_user`
- **Organization Hierarchy**: Every non-superuser must belong to an `Organization`; users can be associated with multiple `Space`s
- **Custom UserManager**: Handles role-specific user creation with `auth_method` field determining passwordless vs password authentication

### Role-Based URL Structure (`issue_management/`)
URLs are organized by user role with parallel structures:
```
/issues/central-admin/    → issue_management.role_urls.central_admin
/issues/maintainer/       → issue_management.role_urls.maintainer
/issues/reviewer/         → issue_management.role_urls.reviewer
/issues/space-admin/      → issue_management.role_urls.space_admin
/issues/supervisor/       → issue_management.role_urls.supervisor
```
Each role has its own URL namespace and corresponding view modules in `views/`.

### Issue Management System
- **Models**: `Issue`, `IssueImage`, `IssueComment` with automatic slug generation using `config.utils.generate_unique_slug()`
- **Status Flow**: `open` → `assigned` → `in_progress` → `resolved`/`escalated` → `closed`/`cancelled`
- **Media Handling**: Voice recordings and multiple image uploads per issue (up to 3 via form fields `image1`, `image2`, `image3`)
- **Relationships**: Issues belong to Organizations, optionally to Spaces; reporter is required ForeignKey to User

## Development Conventions

### Model Patterns
- **Auto-slug Generation**: All models use `config.utils.generate_unique_slug()` with 4-char random codes in `save()` method
- **Consistent Relations**: Use descriptive `related_name` for reverse relationships (e.g., `'users'`, `'issues'`, `'reported_issues'`)
- **Required Organization**: All entities (except superusers) must be associated with an Organization

### Form & View Patterns
- **Bootstrap Integration**: All forms inherit from `BootstrapFormMixin` for automatic Bootstrap 5 styling with error handling
- **CBVs with Prefetch**: Use `select_related()`/`prefetch_related()` in `get_queryset()` for performance optimization
- **Role-Based Templates**: Template paths follow pattern `{role}/issue_management/{action}.html`
- **Image Handling**: Forms include separate `image1`, `image2`, `image3` fields; views handle IssueImage creation in `form_valid()`

### Configuration & Environment
- **Environment-based Settings**: Uses `django-environ` with `ENVIRONMENT` variable (`development`/`production`)
- **Development**: Docker Postgres, local media storage, console email backend
- **Production**: DigitalOcean Spaces (S3-compatible), SMTP email, custom `StorageClasses`
- **Static Files**: WhiteNoise for static file serving in all environments

### SCSS/CSS File Organization
- **Page-Specific Structure**: SCSS and generated CSS files stored together by page/feature name
  ```
  static/styles/
    ├── _base.scss, _colors.scss, _sidebar_base.scss     # Global base files
    ├── home/style.scss + style.css                      # Home page styles
    ├── issue_management/
    │   ├── issue_list/style.scss + style.css           # Issue list page
    │   ├── issue_detail/style.scss + style.css         # Issue detail page
    │   └── forms/style.scss + style.css                # Form styles
    └── components/                                      # Reusable components
        ├── voice-recorder.scss + voice-recorder.css
        └── image-upload.css
  ```
- **Base File Imports**: Pages import base styles via `@use` directives:
  - `@use '../base'` for basic navbar/header styles
  - `@use '../../sidebar_base'` for full sidebar layout with responsive design
- **Global Variables**: `_colors.scss` defines theme variables (`$primary`, `$nav-bg`, `$base-white`, etc.)
- **Template Integration**: Pages include specific CSS via `{% static 'styles/path/to/style.css' %}` in `{% block styles %}`

## Development Workflow

### Docker Setup
```bash
docker-compose up  # Runs Django on localhost:7000, Postgres on 5432
```
The container automatically runs migrations and starts dev server via command in `docker-compose.yaml`.

### Database Migrations
- Always run migrations inside container: `python manage.py makemigrations && python manage.py migrate`
- Custom User model requires careful migration handling - organization is optional for superusers only

### Environment Configuration
- Create `src/config/.env` with required variables:
  ```
  SECRET_KEY=your-secret-key
  ENVIRONMENT=development
  ALLOWED_HOSTS=localhost,127.0.0.1
  ```

### Key Files to Know
- `config/settings.py`: Environment-based configuration with django-environ
- `config/utils.py`: Unique slug/code generation utilities (4-char codes)
- `config/mixins/form_mixin.py`: Bootstrap form styling automation with error handling
- `config/storages.py`: Custom S3 storage classes for static/media files
- `docker-compose.yaml`: Development environment setup (container name: `sfs-services-dev-container`)
- `templates/base.html`: Basic template with Bootstrap 5, no sidebar
- `templates/sidebar_base.html`: Full layout template with sidebar, includes Django messages and HTMX
- `static/styles/_colors.scss`: Global color variables and theme definitions
- `static/styles/_sidebar_base.scss`: Complete responsive sidebar layout with navbar

## Common Patterns

### Adding New Role-Based Features
1. Create view in `issue_management/views/{role}.py` (inherit from appropriate Django CBV)
2. Add URL in `issue_management/role_urls/{role}.py` with `app_name = "{role}"`
3. Create template in `templates/{role}/issue_management/{action}.html`
4. Use `BootstrapFormMixin` for forms and include `slug_field = 'slug'` for DetailViews

### Custom User Creation with Auth Method
```python
# General user - phone only (passwordless)
user = User.objects.create_user(
    phone_number="+1234567890",
    user_type='general_user',
    organization=org  # Required for non-superusers
)  # auth_method='phone', password unusable

# All other roles - email + password required  
user = User.objects.create_user(
    email="admin@example.com",
    password="secure_password",
    user_type='central_admin',
    organization=org
)  # auth_method='email'
```

### Model Relationships & Validation
- Organization → Users, Spaces, Issues (one-to-many)
- Space → Users (many-to-many), Issues (one-to-many) 
- Issue → IssueImage, IssueComment (one-to-many)
- User model enforces auth_method constraints in `clean()` method

### Media File Handling
- **Development**: Files stored in `src/media/public/` locally
- **Production**: Files uploaded to DigitalOcean Spaces with `public-read` ACL for `media/public/` paths
- **Image Uploads**: Forms handle multiple images; views create separate `IssueImage` instances in `form_valid()`

## Security & Permissions
- Role-based access handled via URL routing and view inheritance, not Django's permission system
- **Authentication Rules**: Enforced in `UserManager.create_user()` and `User.clean()`
  - `general_user`: Phone number only, no password required (`auth_method='phone'`)
  - All other roles: Email + password authentication mandatory (`auth_method='email'`)
- File uploads go to `media/public/` for public access; private files use default ACL