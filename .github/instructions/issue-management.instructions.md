---
description: "Use when adding or modifying issue management features, routes, views, templates, or forms. Enforces role-vs-common routing boundaries and issue-domain conventions."
name: "Issue Management Guardrails"
applyTo: "src/issue_management/**"
---
# Issue Management Guardrails

- Keep role-specific features in matching role modules:
  - URLs: `src/issue_management/role_urls/{role}.py`
  - Views: `src/issue_management/views/{role}.py`
  - Templates: `src/templates/{role}/issue_management/`
- Put shared features for all authenticated users in `src/issue_management/views/common.py` and route them from `src/issue_management/urls.py` (not role URL modules).
- Preserve multi-tenant behavior: non-superuser access is organization-scoped; do not introduce cross-org data leakage.
- Follow existing issue/task model conventions from `src/issue_management/models.py` and activity tracking in `src/issue_management/signals.py`.
- For list/detail rendering of related data, use `select_related()` / `prefetch_related()` to avoid N+1 queries.
- For forms, use `BootstrapFormMixin` unless a form intentionally needs custom rendering.
- Keep media upload paths under `media/public/` where content must remain publicly readable through configured storage ACL behavior.
- Keep style changes page-scoped (`style.scss` + compiled `style.css`) and avoid standalone raw CSS pages.
