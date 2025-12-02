# Copilot Instructions for Services Project

## Project Overview
Django 5.2 issue tracking system with dual authentication, role-based access control, and multi-tenant architecture. Production uses Docker (app on `:7000`, Postgres on `:5432`) with DigitalOcean Spaces for media storage.

**Stack**: Django 5.2 • PostgreSQL • Docker • Bootstrap 5 • HTMX • WhiteNoise • DigitalOcean Spaces (S3-compatible)

**Core Dependencies**: `django-environ`, `django-storages`, `psycopg2-binary`, `pillow`, `whitenoise`, `boto3`

## Architecture

### 1. Dual Authentication System (`core/backends.py`, `core/models.py`)
Two parallel authentication flows in `DualAuthBackend`:
- **Passwordless (Phone)**: `general_user` only → `authenticate(phone_number="+1234567890")`
- **Email + Password**: All other roles → `authenticate(username="email", password="pass")`
- **Email + PIN**: Optional 4-digit PIN for quick auth (all roles except `general_user` and superusers)

**User Model Enforcement**:
- `auth_method` field auto-set based on `user_type` 
- Organization required for all non-superusers
- Phone required for all non-superusers
- Custom `UserManager.create_user()` enforces rules; `User.clean()` validates on save

### 2. Role-Based URL Architecture
Parallel URL structures per role (`issue_management/`):
```
/issues/central-admin/ → role_urls/central_admin.py → views/central_admin.py → templates/central_admin/
/issues/maintainer/    → role_urls/maintainer.py    → views/maintainer.py    → templates/maintainer/
/issues/reviewer/      → role_urls/reviewer.py      → views/reviewer.py      → templates/reviewer/
/issues/space-admin/   → role_urls/space_admin.py   → views/space_admin.py   → templates/space_admin/
/issues/supervisor/    → role_urls/supervisor.py    → views/supervisor.py    → templates/supervisor/
```
Each role gets isolated URL namespace (`app_name = "{role}"`), view module, and template directory.

### 3. Common Cross-Role Views (`issue_management/views/common.py`)
Shared functionality outside role-based URLs:
- **Purpose**: Features accessible to ALL authenticated users (comments, shared resources)
- **URL Registration**: Directly in `issue_management/urls.py` (NOT in role_urls subdirectory)
- **Authentication**: Use `LoginRequiredMixin` for auth
- **HTMX Pattern**: Return partial templates from `templates/common/issue_management/partials/`
- **Example**: `IssueCommentCreateView` at `/issues/<slug>/comments/create/` → returns `comment_list.html` partial

### 4. Issue Management Domain (`issue_management/models.py`)
**Core Models**: `Issue`, `IssueImage`, `IssueComment`, `WorkTask`, `WorkTaskShare`, `SiteVisit`, `IssueActivity`
- **Slug Generation**: All models auto-generate slugs in `save()` using `generate_unique_slug()` with 4-char codes
- **Status Flow**: `open` → `assigned` → `in_progress` → `resolved`/`escalated` → `closed`/`cancelled`
- **Image Handling**: Automatic WebP compression via `compress_image()` utility; unique alphanumeric filenames
- **External Sharing**: `WorkTaskShare` creates secure 32-char tokens with expiration, permission levels, access tracking
- **Activity Tracking**: `IssueActivity` logs all changes (excludes comments) for audit trail

## Development Conventions

### Model Patterns
```python
class MyModel(models.Model):
    title = models.CharField(max_length=200)
    org = models.ForeignKey('core.Organization', related_name='my_models', on_delete=models.CASCADE)
    slug = models.SlugField(unique=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, slugify(self.title))
        super().save(*args, **kwargs)
```
- Use descriptive `related_name` for reverse queries
- Organization required for all entities except superusers

### Form & View Patterns
```python
# Form with Bootstrap styling
class MyForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Issue
        fields = ['title', 'description', 'image1', 'image2', 'image3']

# View with optimization
class MyDetailView(DetailView):
    model = Issue
    slug_field = 'slug'
    slug_url_kwarg = 'issue_slug'
    
    def get_queryset(self):
        return super().get_queryset().select_related('org', 'reporter').prefetch_related('images')
```
- `BootstrapFormMixin` auto-applies form-control classes and inline error display
- Image uploads: Handle `image1`/`image2`/`image3` in `form_valid()`, create separate model instances

### Configuration & Environment
- **Environment-based Settings**: Uses `django-environ` with `ENVIRONMENT` variable (`development`/`production`)
- **Development**: Docker Postgres, local media storage, console email backend
- **Production**: DigitalOcean Spaces (S3-compatible), SMTP email, custom `StorageClasses`
- **Static Files**: WhiteNoise for static file serving in all environments
- **Custom Utilities**: `config.utils.py` provides `generate_unique_slug()` and `generate_unique_code()` for 4-char suffixes and longer tokens

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
docker-compose up  # Runs Django on localhost:7000 (mapped from container port 8000), Postgres on 5432
```
The container automatically runs migrations and starts dev server via command in `docker-compose.yaml`. Container names: `sfs-services-dev-container` (app), `sfs-services-dev-postgres-container` (database).

### Running Commands in Container
```bash
# Enter the container for Django commands
docker exec -it sfs-services-dev-container bash

# Or run commands directly
docker exec -it sfs-services-dev-container python manage.py makemigrations
docker exec -it sfs-services-dev-container python manage.py migrate
docker exec -it sfs-services-dev-container python manage.py createsuperuser

# For Windows PowerShell, use:
docker exec -it sfs-services-dev-container python manage.py shell
```

### Database Migrations
- **Always run migrations inside container**: 
  ```bash
  # Linux/Mac (use && to chain commands)
  docker exec -it sfs-services-dev-container python manage.py makemigrations && docker exec -it sfs-services-dev-container python manage.py migrate
  
  # Windows PowerShell (use ; to separate commands - they run sequentially regardless of success)
  docker exec -it sfs-services-dev-container python manage.py makemigrations ; docker exec -it sfs-services-dev-container python manage.py migrate
  ```
- **Migration Considerations**: Custom User model requires careful migration handling - organization is optional for superusers only
- **Important**: Always run `makemigrations` BEFORE `migrate` when model changes are made

### Environment Configuration
- Create `src/config/.env` with required variables (Django looks for this path automatically):
  ```
  SECRET_KEY=your-secret-key-here
  ENVIRONMENT=development
  ALLOWED_HOSTS=localhost,127.0.0.1
  
  # Firebase credentials (required for push notifications)
  FIREBASE_PROJECT_ID=your-project-id
  FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
  FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxxxx@project.iam.gserviceaccount.com
  # ... other Firebase env vars (see .env.example)
  ```
- For production, add: `DATABASE_URL`, email settings (`EMAIL_HOST`, `EMAIL_HOST_USER`, etc.), and DigitalOcean Spaces config
- **Firebase Configuration**: All environments use environment variables for Firebase credentials (no JSON file needed)
  - Run `python convert_firebase_to_env.py` to convert `firebase-service-account.json` to env vars
  - See `docs/FIREBASE_SECRET_MANAGEMENT.md` for complete setup guide
- Environment detection: `ENVIRONMENT=development` enables debug mode, console email, local storage; `production` enables S3 storage, SMTP email

### Working with CSS/SCSS
- **Always create SCSS files for page-specific styles** - do NOT create raw CSS files
- **Each page gets its own folder** within the appropriate module directory (e.g., `issue_list/`, `issue_detail/`)
- **Inside each page folder**, create a `style.scss` file, then compile to `style.css` in the same folder
- **SCSS Compilation**: 
  - Files are NOT automatically compiled - compile manually using a SCSS compiler
  - Example: `sass src/static/styles/home/style.scss src/static/styles/home/style.css`
  - Both `.scss` source and `.css` compiled files are committed to the repository
- **Base Style Imports**: Always import base styles in SCSS files:
  - `@use '../_base'` for basic navbar/header styles only
  - `@use '../../_sidebar_base'` for full sidebar layout with responsive design
- **Variables**: Use color variables from `static/styles/_colors.scss` (e.g., `$primary`, `$nav-bg`, `$base-white`) instead of hardcoded colors
- **Template Loading**: Reference compiled CSS in templates: `{% static 'styles/path/to/style.css' %}` in `{% block styles %}`

### Key Files to Know
- `config/settings.py`: Environment-based configuration with django-environ
- `config/utils.py`: Unique slug/code generation utilities (4-char codes)
- `config/mixins/form_mixin.py`: Bootstrap form styling automation with error handling
- `config/storages.py`: Custom S3 storage classes for static/media files
- `core/backends.py`: DualAuthBackend for phone and email authentication
- `docker-compose.yaml`: Development environment setup (container name: `sfs-services-dev-container`)
- `templates/base.html`: Basic template with Bootstrap 5, no sidebar
- `templates/sidebar_base.html`: Full layout template with sidebar, includes Django messages and HTMX
- `static/styles/_colors.scss`: Global color variables and theme definitions
- `static/styles/_sidebar_base.scss`: Complete responsive sidebar layout with navbar
- `src/requirements.txt`: Python dependencies (Django 5.2, PostgreSQL, DigitalOcean Spaces, WhiteNoise)

### Development Troubleshooting
```bash
# Check container status
docker ps

# View container logs
docker logs sfs-services-dev-container
docker logs sfs-services-dev-postgres-container

# Reset database completely
docker-compose down -v  # Removes volumes
docker-compose up

# Access Django shell
docker exec -it sfs-services-dev-container python manage.py shell

# Check Django configuration
docker exec -it sfs-services-dev-container python manage.py check
```

## Common Patterns

### Adding New Role-Based Features
1. Create view in `issue_management/views/{role}.py` (inherit from appropriate Django CBV)
2. Add URL in `issue_management/role_urls/{role}.py` with `app_name = "{role}"`
3. Create template in `templates/{role}/issue_management/{action}.html`
4. Use `BootstrapFormMixin` for forms and include `slug_field = 'slug'` for DetailViews

### Adding Common/Shared Features
For functionality that should be accessible across all roles:
1. Create view in `issue_management/views/common.py` (use `LoginRequiredMixin` for auth)
2. Add URL directly in `issue_management/urls.py` (not in role_urls subdirectory)
3. Create partial templates in `templates/common/issue_management/partials/` for HTMX responses
4. Example pattern - Issue Comments:
   ```python
   # View in common.py
   class IssueCommentCreateView(LoginRequiredMixin, View):
       def post(self, request, issue_slug):
           issue = get_object_or_404(Issue, slug=issue_slug)
           form = IssueCommentForm(request.POST)
           if form.is_valid():
               comment = form.save(commit=False)
               comment.issue = issue
               comment.user = request.user
               comment.save()
               # Return partial template for HTMX swap
               return render(request, 'common/issue_management/partials/comment_list.html', {...})
   
   # URL in urls.py
   path('issues/<slug:issue_slug>/comments/create/', common.IssueCommentCreateView.as_view(), name='comment_create')
   ```

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
- Issue → IssueImage, IssueComment, WorkTask (one-to-many)
- WorkTask → WorkTaskShare (one-to-many) for external sharing
- User model enforces auth_method constraints in `clean()` method

### Work Task Management
- **Task Lifecycle**: Create → Assign → Update → Complete (with resolution notes) → Optional sharing
- **External Sharing**: Generate secure tokens via `WorkTaskShare` with expiration, permission levels, and access tracking
- **Completion Flow**: Use `WorkTaskCompleteView` requiring resolution notes; `WorkTaskToggleCompleteView` for reopening

### Media File Handling
- **Development**: Files stored in `src/media/public/` locally
- **Production**: Files uploaded to DigitalOcean Spaces (S3-compatible) using custom `MediaStorage` class
  - Default ACL is `private` for security
  - Files in `media/public/` paths automatically get `public-read` ACL (see `config/storages.py`)
  - This allows public access to issue images/voices while keeping other files private
- **Image Uploads**: Forms handle multiple images via `image1`, `image2`, `image3` fields; views create separate `IssueImage` instances in `form_valid()`
- **Storage Classes**: `StaticStorage` (public-read for all static files) and `MediaStorage` (conditional ACL based on path)

## Security & Permissions
- Role-based access handled via URL routing and view inheritance, not Django's permission system
- **Authentication Rules**: Enforced in `UserManager.create_user()` and `User.clean()`
  - `general_user`: Phone number only, no password required (`auth_method='phone'`)
  - All other roles: Email + password authentication mandatory (`auth_method='email'`)
- File uploads go to `media/public/` for public access; private files use default ACL