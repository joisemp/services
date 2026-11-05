"""Role-aware ticket / work-task / site-visit queryset helpers."""
from django.db.models import Q

from ticket_management.models import Ticket, SiteVisit, WorkTask


def issues_for_user(user):
    """Return issues visible to ``user`` based on their role."""
    if not user.is_authenticated:
        return Ticket.objects.none()

    org = user.organization
    base = Ticket.objects.select_related(
        'org', 'space', 'reporter', 'assigned_to', 'vehicle', 'workshop'
    ).prefetch_related('images', 'reviewers')

    if user.is_superuser and not org:
        return base.all()

    if not org:
        return Ticket.objects.none()

    qs = base.filter(org=org)

    if user.is_central_admin:
        return qs
    if user.is_space_admin:
        if user.active_space:
            return qs.filter(space=user.active_space)
        return qs.filter(space__in=user.spaces.all())
    if user.is_supervisor:
        return qs.filter(assigned_to=user)
    if user.is_maintainer:
        return qs.filter(work_tasks__assigned_to=user).distinct()
    if user.is_reviewer:
        return qs.filter(reviewers=user)
    if user.is_transport_incharge:
        return qs.filter(Q(vehicle__isnull=False) | Q(workshop__isnull=False))
    return Ticket.objects.none()


def work_tasks_for_user(user):
    """Work tasks visible to ``user``."""
    if not user.is_authenticated:
        return WorkTask.objects.none()

    org = user.organization
    base = WorkTask.objects.select_related(
        'ticket', 'ticket__org', 'ticket__space', 'assigned_to'
    )

    if not org and not user.is_superuser:
        return WorkTask.objects.none()

    if org:
        base = base.filter(ticket__org=org)

    if user.is_central_admin or user.is_space_admin:
        if user.is_space_admin and user.active_space:
            return base.filter(ticket__space=user.active_space)
        return base
    if user.is_supervisor:
        # Supervisors manage tasks on their assigned issues and see their own tasks
        return base.filter(Q(assigned_to=user) | Q(ticket__assigned_to=user)).distinct()
    if user.is_maintainer:
        return base.filter(assigned_to=user)
    return WorkTask.objects.none()


def site_visits_for_user(user):
    """Site visits visible to ``user``."""
    if not user.is_authenticated:
        return SiteVisit.objects.none()

    org = user.organization
    base = SiteVisit.objects.select_related(
        'ticket', 'ticket__org', 'ticket__space', 'created_by', 'assigned_to'
    ).prefetch_related('images')

    if not org and not user.is_superuser:
        return SiteVisit.objects.none()

    if org:
        base = base.filter(ticket__org=org)

    if user.is_central_admin:
        return base
    if user.is_space_admin:
        if user.active_space:
            return base.filter(ticket__space=user.active_space)
        return base.filter(ticket__space__in=user.spaces.all())
    if user.is_supervisor or user.is_maintainer:
        return base.filter(Q(assigned_to=user) | Q(created_by=user)).distinct()
    return SiteVisit.objects.none()
