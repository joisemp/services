---
description: "Scaffold a shared cross-role ticket-management feature in common views with correct routing and tenant-safe behavior."
name: "Add Shared Feature"
argument-hint: "Shared feature request, e.g. common ticket watch/unwatch toggle"
agent: "agent"
---
Implement one shared feature for all authenticated roles in this repository using the provided request.

Requirements:
- Place view logic in `src/ticket_management/views/common.py`.
- Register routes in `src/ticket_management/urls.py` (not in role URL modules).
- Use templates under `src/templates/common/ticket_management/` (and `partials/` when HTMX swaps are used).
- Use Django CBVs where appropriate and enforce authenticated access.
- Preserve organization-scoped behavior for non-superusers.
- Use `select_related()` / `prefetch_related()` for related data shown in list/detail contexts.
- Use `BootstrapFormMixin` for forms unless custom rendering is explicitly needed.

Execution checklist:
1. Inspect existing common view and URL patterns before editing.
2. Implement the smallest focused change that satisfies the requested feature.
3. Keep role-specific logic out of `common.py`; shared-only behavior belongs here.
4. Run relevant Django checks/tests for modified behavior.
5. Summarize changed files and any follow-up validation steps.
