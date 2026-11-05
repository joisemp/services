---
description: "Scaffold a role-specific feature for ticket_management or inventory with URL, view, template, and query optimization following services project conventions."
name: "Add Role Feature"
argument-hint: "App + role + feature, e.g. inventory maintainer stock alert list"
agent: "agent"
---
Implement one role-specific feature in this repository using the provided request.

Requirements:
- Accept app target as `ticket_management` or `inventory` and keep all changes inside that app.
- Place routing in `src/{app}/role_urls/{role}.py`.
- Place view logic in `src/{app}/views/{role}.py`.
- Place templates in `src/templates/{role}/{app}/`.
- Use Django CBVs and preserve organization-scoped access rules.
- Use `select_related()` / `prefetch_related()` for related data shown in list/detail pages.
- Use `BootstrapFormMixin` for forms unless custom rendering is explicitly needed.
- If the request is for a shared cross-role feature, use the dedicated shared-feature prompt instead of forcing role-specific placement.

Execution checklist:
1. Inspect existing patterns in matching `{app}` role modules before editing.
2. Implement minimal focused changes only for the requested feature.
3. Update templates/styles only where required (`style.scss` + compiled `style.css` if styling is changed).
4. Run the most relevant Django checks/tests for changed behavior.
5. Summarize changed files and any follow-up validation steps.
