---
description: "Use when writing or updating Django tests, test fixtures, or role/auth test coverage in this repository. Covers organization scoping, dual-auth behavior, and stable test patterns."
name: "Django Test Conventions"
applyTo: "src/**/tests.py"
---
# Django Test Conventions

- Prefer Django `TestCase` style already used in this repo; keep tests deterministic and isolated.
- For non-superuser user creation, always include organization and phone to satisfy `UserManager.create_user()` invariants.
- Cover both authentication paths where relevant:
  - `general_user`: phone/passwordless flow
  - other roles: email/password flow (PIN path only where feature supports it)
- For issue-related tests, preserve organization scoping and assert users cannot access cross-org data.
- When testing views that render related objects, mirror production query shape (`select_related` / `prefetch_related`) when asserting counts or query-sensitive behavior.
- Keep role-specific behavior in role-specific tests; shared authenticated behavior belongs in tests aligned with common views.
- Prefer existing app test modules (`src/core/tests.py`, `src/issue_management/tests.py`, `src/issue_management/tests_firebase_notifications.py`) as pattern references.
- Link to detailed docs instead of duplicating guidance:
  - `README.md`
  - `docs/PERFORMANCE_REPORT_QUICKSTART.md`
  - `docs/FIREBASE_NOTIFICATIONS_IMPROVEMENTS.md`
