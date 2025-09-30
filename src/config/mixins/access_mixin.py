from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin


class BaseRoleAccessMixin(LoginRequiredMixin):
    """Base mixin to restrict access to a specific user role (by property)"""
    role_property: str = None  # should be overridden in subclasses

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not getattr(request.user, self.role_property, False):
            raise PermissionDenied("You do not have permission to access this page.")

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
