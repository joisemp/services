"""
DRF permission classes mirroring config.mixins.access_mixin role checks.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsCentralAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'is_central_admin', False)
        )


class IsSpaceAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'is_space_admin', False)
        )


class IsSupervisor(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'is_supervisor', False)
        )


class IsMaintainer(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'is_maintainer', False)
        )


class IsReviewer(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'is_reviewer', False)
        )


class IsTransportIncharge(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'is_transport_incharge', False)
        )


class IsIssueStaff(BasePermission):
    """Central admin or transport incharge (shared issue staff screens)."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                getattr(user, 'is_central_admin', False)
                or getattr(user, 'is_transport_incharge', False)
            )
        )


class IsCentralOrSpaceAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                getattr(user, 'is_central_admin', False)
                or getattr(user, 'is_space_admin', False)
            )
        )


class IsIssueCreatorRole(BasePermission):
    """Roles allowed to create issues on the web."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return any(
            getattr(user, prop, False)
            for prop in (
                'is_central_admin',
                'is_space_admin',
                'is_supervisor',
                'is_transport_incharge',
            )
        )


class IsDashboardRole(BasePermission):
    """Roles that have a dashboard view."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return any(
            getattr(user, prop, False)
            for prop in (
                'is_central_admin',
                'is_space_admin',
                'is_transport_incharge',
            )
        )


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class RoleAnyOf(BasePermission):
    """
    Allow if the user matches any role property listed on the view as
    ``allowed_role_properties`` (tuple of strings like ``is_central_admin``).
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        props = getattr(view, 'allowed_role_properties', ())
        return any(getattr(user, prop, False) for prop in props)
