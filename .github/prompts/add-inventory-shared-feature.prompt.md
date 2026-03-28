---
description: "Scaffold a shared cross-role inventory feature with common views, correct routing, and tenant-safe behavior."
name: "Add Inventory Shared Feature"
argument-hint: "Shared inventory feature request, e.g. common item watch/unwatch toggle"
agent: "agent"
---
Implement one shared inventory feature for all authenticated roles in this repository using the provided request.

Requirements:
- Place shared view logic in `src/inventory/views/common.py`.
- If `src/inventory/views/common.py` does not exist, create it with minimal focused structure.
- Register shared routes in `src/inventory/urls.py` (not in role URL modules).
- Use templates under `src/templates/common/inventory/` (and `partials/` when HTMX swaps are used).
- Use Django CBVs where appropriate and enforce authenticated access.
- Preserve organization-scoped behavior for non-superusers.
- Use `select_related()` / `prefetch_related()` for related data shown in list/detail contexts.
- Use `BootstrapFormMixin` for forms unless custom rendering is explicitly needed.

Execution checklist:
1. Inspect existing inventory URL and role module patterns before editing.
2. Implement the smallest focused change that satisfies the requested feature.
3. Keep role-specific logic out of `views/common.py`; shared-only behavior belongs here.
4. Run relevant Django checks/tests for modified behavior.
5. Summarize changed files and any follow-up validation steps.
