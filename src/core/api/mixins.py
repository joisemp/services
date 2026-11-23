"""
Queryset scoping helpers for org- and space-bound API resources.
"""
from rest_framework.exceptions import PermissionDenied


class OrgScopedMixin:
    """
    Restrict querysets to the authenticated user's organization.

    Set ``org_field`` (default ``org``) to the FK name on the model
    (``organization`` for User, ``org`` for Ticket/Space).
    """

    org_field = 'org'
    lookup_field = 'slug'

    def get_user_organization(self):
        user = self.request.user
        org = getattr(user, 'organization', None)
        if org is None and not user.is_superuser:
            raise PermissionDenied('User is not associated with an organization.')
        return org

    def filter_by_organization(self, queryset):
        org = self.get_user_organization()
        if org is None:
            return queryset  # superuser without org
        return queryset.filter(**{self.org_field: org})


class SpaceScopedMixin(OrgScopedMixin):
    """
    For space admins, further restrict to ``active_space`` when set.
    Central admins see the whole org unless a space query param is given.
    """

    space_field = 'space'

    def filter_by_space(self, queryset):
        user = self.request.user
        if getattr(user, 'is_space_admin', False):
            active = getattr(user, 'active_space', None)
            if active is None:
                raise PermissionDenied('Select an active space before continuing.')
            if not user.can_access_space(active):
                raise PermissionDenied('Active space is no longer available.')
            return queryset.filter(**{self.space_field: active})

        space_slug = self.request.query_params.get('space')
        if space_slug:
            return queryset.filter(**{f'{self.space_field}__slug': space_slug})
        return queryset


class OrgQuerysetMixin(OrgScopedMixin):
    """List/detail views: apply organization filter in get_queryset."""

    def get_queryset(self):
        qs = super().get_queryset()
        return self.filter_by_organization(qs)
