# Service Management App

A comprehensive Django-based service management system designed for organizations to manage all their services efficiently. The system includes issue reporting, service tracking, and maintenance workflows with role-based access control.

## Features

- **Service Management**: Complete service lifecycle management for organizations
- **Issue Reporting**: Users can report service issues with descriptions, images (up to 3), and voice recordings
- **Role-based Access**: Support for different user types (central_admin, maintainer, regular users)
- **Status Management**: One-way issue status progression (inspected → work in progress → resolved/escalated)
- **Assignment System**: Central admins can assign issues to maintainers
- **Organization Support**: Multi-organization support with service categorization
- **Responsive UI**: Modern, clean interface with Bootstrap styling

## Status Workflow

The system enforces a strict one-way status progression:
1. **Not Addressed** → **Inspected** (maintainer sets as inspected)
2. **Inspected** → **Work In Progress** (maintainer starts work)
3. **Work In Progress** → **Resolved** or **Escalated** (maintainer completes or escalates)

Once an issue is resolved or escalated, it cannot be changed.

## User Roles

- **Central Admin**: Can assign issues to maintainers and oversee all organizational services
- **Maintainer**: Can update issue status, manage assigned issues, and maintain services
- **Regular User**: Can report service issues and view service status

## Current Status

🚧 **This project is currently under development** 🚧

The core service management and issue tracking functionality is implemented but the system is still being refined and enhanced. Additional service management features are being developed to provide a complete organizational service management solution.

## Tech Stack

- Django 5.2
- Python 3.12
- SQLite (development)
- Bootstrap 5.3
- PIL (Pillow) for image handling

## Installation

1. Clone the repository
2. Create a virtual environment: `python -m venv env`
3. Activate the environment: `env\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Run migrations: `python manage.py migrate`
6. Create a superuser: `python manage.py createsuperuser`
7. Run the server: `python manage.py runserver`

## License

This project is currently under development and not yet licensed for public use.