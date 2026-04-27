"""
Shared fleet management views accessible by all roles.
This module contains common view logic used across different roles.
"""
from django.views.generic import ListView, DetailView


# TODO: Add common views here
# Example patterns to follow:
# - ListViews with select_related/prefetch_related optimization
# - DetailViews with organization scoping for multi-tenant support
# - Shared permission checks for cross-role access control
