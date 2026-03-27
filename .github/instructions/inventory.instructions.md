---
description: "Use when adding or modifying inventory features, routes, views, templates, or forms. Enforces role-based routing boundaries and inventory app conventions."
name: "Inventory Guardrails"
applyTo: "src/inventory/**"
---
# Inventory Guardrails

- Keep role-specific features in matching role modules:
  - URLs: `src/inventory/role_urls/{role}.py`
  - Views: `src/inventory/views/{role}.py`
  - Templates: `src/templates/{role}/inventory/`
- Register app-level role includes in `src/inventory/urls.py` and keep role routes within `role_urls/*` files.
- Preserve multi-tenant behavior: non-superuser access is organization-scoped; do not introduce cross-org data leakage.
- Use Django CBVs and optimize related-data list/detail pages with `select_related()` / `prefetch_related()`.
- Use `BootstrapFormMixin` for forms unless custom rendering is explicitly needed.
- Keep style changes page-scoped (`style.scss` + compiled `style.css`) and avoid standalone raw CSS pages.
- Keep changes minimal and pattern-consistent with existing inventory role modules.
