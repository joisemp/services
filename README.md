# Services

A Django 5.2-based issue management system with role-based access control and multi-tenant organization support.

## Overview

This project provides a comprehensive issue tracking platform featuring:

- **Custom Authentication System**: Supports both passwordless phone authentication for general users and email/password authentication for administrative roles
- **Role-Based Access Control**: Six distinct user roles (central_admin, space_admin, maintainer, supervisor, reviewer, general_user) with specialized workflows
- **Multi-Tenant Architecture**: Organization and space-based issue management with hierarchical access controls
- **Work Task Management**: Detailed task tracking with assignment, progress monitoring, and external sharing capabilities
- **Media Support**: Issue documentation with voice recordings and multiple image uploads

## Tech Stack

- **Backend**: Django 5.2, PostgreSQL
- **Frontend**: Bootstrap 5, HTMX
- **Storage**: DigitalOcean Spaces (S3-compatible)
- **Deployment**: Docker, WhiteNoise for static files

## Development Status

🚧 **This project is currently under development** 🚧

Features are being actively developed and the API may change.

