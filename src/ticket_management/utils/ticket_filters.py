"""
Shared queryset filter helper for the central-admin ticket list.

Used by both the list view and the report view so the two never drift.
"""

from django.db.models import Case, Q, When, IntegerField


# All status values that map directly to Ticket.status
VALID_STATUS_VALUES = [
    'open', 'assigned', 'in_progress', 'resolved',
    'escalated', 'closed', 'cancelled',
]


def apply_ticket_list_filters(queryset, *, status_filter=None, space_filter=None,
                              reporter_filter=None, assignee_filter=None,
                              search_query=None):
    """
    Apply the standard central-admin ticket list filters to *queryset* and
    return the (un-ordered) filtered queryset.

    Parameters
    ----------
    queryset       : Ticket queryset to filter
    status_filter  : value of ?status= param
                     Special values: 'not_resolved', 'critical', 'unassigned'
                     Standard values: any item in VALID_STATUS_VALUES
    space_filter   : value of ?space= param ('no_space' or a space slug)
    reporter_filter: value of ?reporter= param (user slug or numeric id)
    assignee_filter: value of ?assignee= param (user slug or numeric id)
    search_query   : value of ?q= param (matches title, ticket_id, description)
    """

    # --- search ---------------------------------------------------------
    if search_query:
        q = search_query.strip()
        if q:
            queryset = queryset.filter(
                Q(title__icontains=q)
                | Q(ticket_id__icontains=q)
                | Q(description__icontains=q)
            )

    # --- reporter -------------------------------------------------------
    if reporter_filter:
        if reporter_filter.isdigit():
            queryset = queryset.filter(reporter_id=reporter_filter)
        else:
            queryset = queryset.filter(reporter__slug=reporter_filter)

    # --- assignee -------------------------------------------------------
    if assignee_filter:
        if assignee_filter.isdigit():
            queryset = queryset.filter(assigned_to_id=assignee_filter)
        else:
            queryset = queryset.filter(assigned_to__slug=assignee_filter)

    # --- status / priority special values --------------------------------
    if status_filter:
        if status_filter == 'not_resolved':
            queryset = queryset.exclude(status='resolved')
        elif status_filter == 'critical':
            # "Critical" is a priority filter, not a status filter
            queryset = queryset.filter(priority='critical')
        elif status_filter == 'unassigned':
            queryset = queryset.filter(assigned_to__isnull=True)
        elif status_filter in VALID_STATUS_VALUES:
            queryset = queryset.filter(status=status_filter)

    # --- space -----------------------------------------------------------
    if space_filter:
        if space_filter == 'no_space':
            queryset = queryset.filter(space__isnull=True)
        else:
            queryset = queryset.filter(space__slug=space_filter)

    return queryset


def annotate_and_order(queryset):
    """
    Apply the standard status/priority ordering annotation and return the
    ordered queryset.  Call this *after* apply_ticket_list_filters.
    """
    return queryset.annotate(
        status_order=Case(
            When(status='open', then=1),
            When(status='assigned', then=2),
            When(status='in_progress', then=3),
            When(status='resolved', then=4),
            When(status='escalated', then=5),
            When(status='closed', then=6),
            When(status='cancelled', then=7),
            default=8,
            output_field=IntegerField(),
        ),
        priority_order=Case(
            When(priority='critical', then=1),
            When(priority='high', then=2),
            When(priority='medium', then=3),
            When(priority='low', then=4),
            default=5,
            output_field=IntegerField(),
        ),
    ).order_by('status_order', 'priority_order', '-created_at')


def describe_filters(*, status_filter=None, space_filter=None,
                     reporter_filter=None, assignee_filter=None,
                     search_query=None):
    """
    Return a human-readable list of strings describing the active filters,
    e.g. ['Status: Open', 'Space: No Space Assigned'].
    Used in PDF/Excel report headers.
    """
    parts = []

    STATUS_LABELS = {
        'open': 'Open',
        'assigned': 'Assigned',
        'in_progress': 'In Progress',
        'resolved': 'Resolved',
        'escalated': 'Escalated',
        'closed': 'Closed',
        'cancelled': 'Cancelled',
        'not_resolved': 'Not Resolved',
        'critical': 'Critical Priority',
        'unassigned': 'Unassigned',
    }

    if status_filter and status_filter != 'all':
        label = STATUS_LABELS.get(status_filter, status_filter.replace('_', ' ').title())
        parts.append(f"Status: {label}")
    else:
        parts.append("Status: All")

    if space_filter:
        if space_filter == 'no_space':
            parts.append("Space: No Space Assigned")
        else:
            parts.append(f"Space: {space_filter}")

    if reporter_filter:
        parts.append(f"Reporter: {reporter_filter}")

    if assignee_filter:
        parts.append(f"Assignee: {assignee_filter}")

    if search_query and search_query.strip():
        parts.append(f"Search: {search_query.strip()}")

    return parts
