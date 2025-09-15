# Copilot Instructions for Services Project

## Project Overview
This is a Django-based issue management system with role-based access control. The project features a custom user authentication system supporting both phone (passwordless) and email authentication, and is designed around organizations and spaces for multi-tenant issue tracking.

## Architecture & Key Components

### Custom User Authentication (`core/models.py`)
- **Two-Tier Authentication System**:
  - **General Users**: Phone-only authentication (passwordless) - just enter phone number to login
  - **All Other Roles**: Email + password authentication required (`central_admin`, `space_admin`, `maintainer`, `supervisor`, `reviewer`)
- **Role-based User Types**: `central_admin`, `space_admin`, `maintainer`, `supervisor`, `reviewer`, `general_user`
- **Organization Hierarchy**: Every user must belong to an `Organization`; users can be associated with multiple `Space`s
- **Custom UserManager**: Handles role-specific user creation logic - phone users get `set_unusable_password()`

### Role-Based URL Structure (`issue_management/`)
URLs are organized by user role with parallel structures:
```
/issues/central-admin/    → issue_management.role_urls.central_admin
/issues/maintainer/       → issue_management.role_urls.maintainer
/issues/reviewer/         → issue_management.role_urls.reviewer
```
Each role has its own URL namespace and corresponding view modules in `views/`.

### Issue Management System
- **Models**: `Issue`, `IssueImage`, `IssueComment` with automatic slug generation
- **Status Flow**: `open` → `assigned` → `in_progress` → `resolved`/`escalated` → `closed`/`cancelled`
- **Media Handling**: Voice recordings and multiple image uploads per issue
- **Relationships**: Issues belong to Organizations, optionally to Spaces

## Development Conventions

### Model Patterns
- **Auto-slug Generation**: All models use `config.utils.generate_unique_slug()` with 4-char random codes
- **Consistent Relations**: Use `related_name` for reverse relationships (e.g., `'users'`, `'issues'`)
- **Required Organization**: All entities must be associated with an Organization

### Form & View Patterns
- **Bootstrap Integration**: All forms inherit from `BootstrapFormMixin` for automatic styling
- **CBVs with Prefetch**: Use `select_related()`/`prefetch_related()` in `get_queryset()` for performance
- **Role-Based Templates**: Template paths follow pattern `{role}/issue_management/{action}.html`

### Configuration & Environment
- **Environment-based Settings**: Development uses Docker Postgres; production uses DigitalOcean Spaces
- **Media Storage**: Local in dev, AWS S3-compatible (DigitalOcean) in production
- **Static Files**: WhiteNoise for static file serving

## Development Workflow

### Docker Setup
```bash
docker-compose up  # Runs Django on localhost:7000, Postgres on 5432
```
The container auto-runs migrations and starts the dev server.

### Database Migrations
- Always run in container: `python manage.py makemigrations && python manage.py migrate`
- Custom User model requires careful migration handling

### Key Files to Know
- `config/settings.py`: Environment-based configuration with django-environ
- `config/utils.py`: Unique slug/code generation utilities
- `config/mixins/form_mixin.py`: Bootstrap form styling automation
- `docker-compose.yaml`: Development environment setup

## Common Patterns

### Adding New Role-Based Features
1. Create view in `issue_management/views/{role}.py`
2. Add URL in `issue_management/role_urls/{role}.py`
3. Create template in `templates/{role}/issue_management/`
4. Use `BootstrapFormMixin` for forms

### Custom User Creation
Authentication method is determined by user type:
```python
# General user - phone only (passwordless)
user = User.objects.create_user(
    phone_number="+1234567890",
    user_type='general_user',
    organization=org
)

# All other roles - email + password required
user = User.objects.create_user(
    email="admin@example.com",
    password="secure_password",
    user_type='central_admin',
    organization=org
)
```

### Model Relationships
- Organization → Users, Spaces, Issues (one-to-many)
- Space → Users (many-to-many), Issues (one-to-many)
- Issue → IssueImage, IssueComment (one-to-many)

## Security & Permissions
- Role-based access is handled via URL routing, not Django's permission system
- **Authentication Rules**:
  - `general_user`: Phone number only, no password required
  - All other roles: Email + password authentication mandatory
- All file uploads go to `media/public/` directory structure