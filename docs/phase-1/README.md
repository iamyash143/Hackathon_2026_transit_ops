# Phase 1 — Foundation

## Goal

Establish a fully working Django project that every developer can clone, run, and build features on top of — immediately and independently. No feature work begins until this phase is complete and merged.

## Phase Objective

By the end of Phase 1:
- Django project boots with PostgreSQL connected
- Custom User model with email-based auth is in place
- RBAC groups (Fleet Manager, Driver, Safety Officer, Financial Analyst) exist and are seeded
- Login / logout / permission-denied pages work
- Base HTML layout, navigation, and Tailwind + Flowbite are configured
- All developers share identical local environment setup

## Files in This Phase

| File | Covers |
|---|---|
| `PROJECT_SETUP.md` | Project init, dependencies, PostgreSQL, settings split, management commands, seed data |
| `AUTHENTICATION.md` | Custom User model, email login, RBAC groups, decorators/mixins, login UI |
| `BASE_UI.md` | Tailwind CSS v4, Flowbite, base templates, navigation, dark mode toggle, HTMX setup |

## Django Apps Created in This Phase

| App | Purpose |
|---|---|
| `accounts` | Custom User model, login/logout, RBAC group helpers |
| `core` | Base template context processors, shared utilities |

## Phase Dependencies

None. This is the root phase. All other phases depend on it.

## Owner

One developer owns this phase end-to-end. Others are blocked until `main` has a green build with migrations applied.

## Definition of Done

- [ ] `python manage.py migrate` runs with zero errors on a clean DB
- [ ] `python manage.py seed_groups` creates all four RBAC groups
- [ ] `python manage.py createsuperuser` works with email as the identifier
- [ ] Visiting `/login/` renders the styled login form
- [ ] A logged-in user sees the sidebar nav; an unauthenticated user is redirected to `/login/`
- [ ] Tailwind dark mode toggle works in the browser
- [ ] HTMX is loaded and `hx-boost` is active on the base template
