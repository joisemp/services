from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth import logout


class BaseRoleAccessMixin(LoginRequiredMixin):
    """Base mixin to restrict access to a specific user role (by property)"""
    role_property: str = None  # should be overridden in subclasses

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not getattr(request.user, self.role_property, False):
            logout(request)
            messages.error(request, "You do not have permission to access this page. Please log in with the correct account.")
            return redirect("core:login")

        return super().dispatch(request, *args, **kwargs)


class CentralAdminOnlyAccessMixin(BaseRoleAccessMixin):
    role_property = "is_central_admin"


class SpaceAdminOnlyAccessMixin(BaseRoleAccessMixin):
    role_property = "is_space_admin"


class MaintainerOnlyAccessMixin(BaseRoleAccessMixin):
    role_property = "is_maintainer"


class SupervisorOnlyAccessMixin(BaseRoleAccessMixin):
    role_property = "is_supervisor"


class ReviewerOnlyAccessMixin(BaseRoleAccessMixin):
    role_property = "is_reviewer"


class GeneralUserOnlyAccessMixin(BaseRoleAccessMixin):
    role_property = "is_general_user"
