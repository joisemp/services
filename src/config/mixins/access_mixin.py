from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth import logout


from django.shortcuts import redirect
from django.contrib.auth.mixins import AccessMixin


class RedirectLoggedinUsers(AccessMixin):
    """
    Redirect logged-in users to their role-specific dashboard,
    otherwise send them to landing page.
    Also provides get_success_url for post-login redirects.
    """

    role_redirects = {
        "is_central_admin": "dashboard:central_admin_dashboard",
        "is_space_admin": "core:switch_space",  # Netflix-style: always go to space selection first
        "is_supervisor": "issue_management:supervisor:issue_list",
    }

    default_redirect = "home"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return self._redirect_authenticated_user(request.user)

        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        """
        Provide success URL for FormView after successful login
        """
        if hasattr(self, 'request') and self.request.user.is_authenticated:
            # Get redirect URL for the authenticated user
            redirect_url = self._get_redirect_url_for_user(self.request.user)
            if redirect_url is None:
                # No recognized role - logout user
                logout(self.request)
                messages.error(
                    self.request, 
                    "Your account does not have the proper permissions. Please contact an administrator."
                )
                from django.urls import reverse
                return reverse(self.default_redirect)
            
            from django.urls import reverse
            return reverse(redirect_url)
        
        # Fallback to default redirect
        from django.urls import reverse
        return reverse(self.default_redirect)

    def _redirect_authenticated_user(self, user):
        """
        Helper method to redirect authenticated user based on their role
        """
        redirect_url = self._get_redirect_url_for_user(user)
        if redirect_url is None:
            # No recognized role - logout user and redirect
            logout(self.request)
            messages.error(
                self.request, 
                "Your account does not have the proper permissions. Please contact an administrator."
            )
            return redirect(self.default_redirect)
        return redirect(redirect_url)

    def _get_redirect_url_for_user(self, user):
        """
        Get the appropriate redirect URL for a user based on their role
        """
        for role_property, redirect_url in self.role_redirects.items():
            if getattr(user, role_property, False):
                return redirect_url
        # If no specific role match → logout user and redirect to landing page
        return None  # Signal that user should be logged out


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


class SpaceAdminWithActiveSpaceMixin(SpaceAdminOnlyAccessMixin):
    """
    Mixin for space admin views that require an active space context.
    Redirects to space switcher if no active space is set.
    """
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and getattr(request.user, self.role_property, False):
            active_space = request.user.active_space

            # If the user has no active space or no longer has access to it, reset and redirect
            if not active_space or not request.user.can_access_space(active_space):
                if active_space:
                    request.user.active_space = None
                    request.user.save(update_fields=['active_space'], skip_validation=True)

                messages.info(
                    request,
                    "Your previously selected space is no longer available. Please pick another space to continue."
                )
                return redirect("core:switch_space")

        return super().dispatch(request, *args, **kwargs)


class MaintainerOnlyAccessMixin(BaseRoleAccessMixin):
    role_property = "is_maintainer"


class SupervisorOnlyAccessMixin(BaseRoleAccessMixin):
    role_property = "is_supervisor"


class ReviewerOnlyAccessMixin(BaseRoleAccessMixin):
    role_property = "is_reviewer"


class GeneralUserOnlyAccessMixin(BaseRoleAccessMixin):
    role_property = "is_general_user"
