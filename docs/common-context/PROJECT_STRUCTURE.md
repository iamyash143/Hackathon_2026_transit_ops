# PROJECT_STRUCTURE.md

This is the exact, authoritative folder structure for the TransitOps Django project. Do not invent alternate structures. If a new app or top-level folder is genuinely needed, update this document in the same PR that introduces it.

## 1. Top-Level Repository Layout

```
transitops/
├── config/                     # Django project package (settings, root urls, wsgi/asgi)
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── apps/                       # All Django apps live here, not at repo root
│   ├── accounts/                # Custom User model, auth, RBAC group setup
│   ├── core/                    # Shared base models, mixins, permission helpers, constants
│   ├── vehicles/                 # Vehicle registry
│   ├── drivers/                  # Driver management
│   ├── trips/                    # Trip lifecycle + dispatch workflow + geospatial routing views
│   ├── maintenance/              # Maintenance logs
│   ├── finance/                  # Fuel logs, expense logs, financial analytics, ROI
│   ├── dashboard/                # KPI dashboard, filters
│   ├── notifications/            # Email (Anymail) + SMS (Twilio) alerts, license expiry checks
│   └── reports/                  # CSV export, PDF export (WeasyPrint)
│
├── templates/                   # Project-level shared templates
│   ├── base.html
│   ├── partials/
│   │   ├── _navbar.html
│   │   ├── _sidebar.html
│   │   ├── _kpi_card.html
│   │   ├── _status_badge.html
│   │   └── _dark_mode_toggle.html
│   └── registration/
│       └── login.html
│
├── static/                      # Project-level static assets
│   ├── src/
│   │   └── input.css             # Tailwind v4 entry file (@import "tailwindcss";)
│   ├── css/
│   │   └── output.css            # Compiled Tailwind output (generated, gitignored)
│   ├── js/
│   │   ├── map.js                # Leaflet + OSRM integration
│   │   ├── charts.js             # Chart.js dashboard rendering
│   │   └── htmx-config.js        # HTMX CSRF header configuration
│   └── vendor/
│       ├── htmx.min.js
│       ├── leaflet/
│       └── chart.js/
│
├── docs/                         # This documentation set
│   ├── 00_COMMON_CONTEXT/
│   ├── PHASE_01_FOUNDATION/
│   ├── PHASE_02_CORE_MODULES/
│   ├── PHASE_03_BUSINESS_LOGIC/
│   ├── PHASE_04_ANALYTICS/
│   ├── PHASE_05_BONUS/
│   └── PHASE_06_TESTING/
│
├── media/                        # User-uploaded files (vehicle documents) — gitignored
│
├── scripts/                      # One-off management/setup scripts
│   └── seed_roles_and_permissions.py
│
├── manage.py
├── requirements.txt
├── package.json                  # Tailwind CLI + npm build scripts
├── tailwind.config.js
├── .env.example
├── .gitignore
└── README.md
```

## 2. Standard Internal Layout of Each App

Every app under `apps/` follows this exact internal structure. Not every app needs every file (e.g. `dashboard` has no `models.py` of its own), but the files that do exist go in these exact locations.

```
apps/<app_name>/
├── __init__.py
├── admin.py                # ModelAdmin registrations, django-admincharts mixins where relevant
├── apps.py
├── models.py                # Model + FSM transitions for this app's primary entity
├── choices.py               # TextChoices classes for this app's status fields
├── forms.py                 # ModelForm classes, crispy-forms FormHelper layouts
├── views.py                 # CBVs for standard CRUD
├── htmx_views.py            # Function-based views returning HTML partials
├── urls.py
├── signals.py                # post_save/pre_save signal handlers owned by this app
├── permissions.py            # Custom permission_required decorators/mixins specific to this app, if any
├── selectors.py              # Read-only query helper functions (complex querysets used by multiple views)
├── services.py                # Non-trivial business logic that doesn't belong on the model itself (e.g. cost aggregation)
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_views.py
│   └── test_transitions.py    # FSM-specific tests
├── migrations/
├── templates/
│   └── <app_name>/
│       ├── <entity>_list.html
│       ├── <entity>_detail.html
│       ├── <entity>_form.html
│       └── partials/
│           └── _<entity>_row.html
└── static/
    └── <app_name>/            # App-specific JS/CSS, if any (rare — prefer project-level static/)
```

## 3. App Responsibility Map

| App | Owns | Key Models |
|---|---|---|
| `accounts` | Authentication, custom User model, Group/Role seeding | `User` |
| `core` | Shared abstract base models, shared mixins, shared constants module, base template context processors | *(no domain model)* |
| `vehicles` | Vehicle registry, vehicle status FSM | `Vehicle` |
| `drivers` | Driver profiles, driver status FSM, license compliance | `Driver` |
| `trips` | Trip creation, dispatch workflow, trip status FSM, Leaflet/OSRM routing views | `Trip` |
| `maintenance` | Maintenance logs, maintenance-triggered vehicle state changes, predictive maintenance thresholds | `MaintenanceLog` |
| `finance` | Fuel logs, expense logs, cost aggregation, ROI/utilization/efficiency calculations | `FuelLog`, `ExpenseLog` |
| `dashboard` | KPI aggregation views, dashboard filters, HTMX-driven dashboard partials | *(no domain model — reads from other apps)* |
| `notifications` | License expiry checks, Anymail email sending, Twilio SMS sending, scheduled management commands | *(no domain model, or a lightweight `NotificationLog`)* |
| `reports` | CSV export (django-import-export), PDF export (WeasyPrint) views | *(no domain model — reads from other apps)* |

## 4. Settings Split

- `config/settings/base.py` — everything common to all environments: `INSTALLED_APPS`, `MIDDLEWARE`, `TEMPLATES`, `AUTH_USER_MODEL`, `AUTH_PASSWORD_VALIDATORS`, `CRISPY_TEMPLATE_PACK`, static/media roots.
- `config/settings/development.py` — imports `from .base import *`, sets `DEBUG = True`, local database credentials, permissive `ALLOWED_HOSTS`, console email backend fallback.
- `config/settings/production.py` — imports `from .base import *`, sets `DEBUG = False`, reads all secrets from environment variables, configures Anymail/Twilio with real credentials, sets `SECURE_*` headers.
- `manage.py` and `wsgi.py`/`asgi.py` default to `config.settings.development` locally; deployment sets `DJANGO_SETTINGS_MODULE=config.settings.production` via environment variable.

## 5. URL Routing Structure

- `config/urls.py` includes each app's `urls.py` under a namespaced prefix:

```python
urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    path("", include("apps.dashboard.urls", namespace="dashboard")),
    path("vehicles/", include("apps.vehicles.urls", namespace="vehicles")),
    path("drivers/", include("apps.drivers.urls", namespace="drivers")),
    path("trips/", include("apps.trips.urls", namespace="trips")),
    path("maintenance/", include("apps.maintenance.urls", namespace="maintenance")),
    path("finance/", include("apps.finance.urls", namespace="finance")),
    path("reports/", include("apps.reports.urls", namespace="reports")),
]
```

- Every app's `urls.py` sets `app_name = "<app_name>"` to match the namespace above.

## 6. Template Resolution Order

Django's `APP_DIRS=True` template loader searches each app's `templates/` folder. Because every app namespaces its templates under `templates/<app_name>/`, there is never a filename collision between apps. `templates/base.html` and `templates/partials/` at the project root are found via the project-level `DIRS` setting in `TEMPLATES`.

## 7. Static Asset Build Process

1. `package.json` defines `npm run build:css`, which runs `@tailwindcss/cli` against `static/src/input.css`, scanning all `templates/**/*.html` and `apps/**/templates/**/*.html` for class usage, and outputs `static/css/output.css`.
2. `npm run watch:css` runs the same process in watch mode during development.
3. `output.css` is committed to `.gitignore` — it is a build artifact, not source. Every developer runs the build step locally; CI/deployment runs it as part of the build pipeline.

## 8. Where New Code Goes — Quick Reference

| I need to... | File to edit/create |
|---|---|
| Add a new field to Vehicle | `apps/vehicles/models.py` + new migration |
| Add a new FSM transition to Trip | `apps/trips/models.py` |
| Add a new dashboard KPI | `apps/dashboard/selectors.py` (query) + `apps/dashboard/views.py` (context) + `templates/dashboard/partials/_kpi_card.html` |
| Add a new HTMX-filtered table | `apps/<app>/htmx_views.py` + `apps/<app>/templates/<app>/partials/_<entity>_row.html` |
| Add a new email/SMS trigger | `apps/notifications/services.py` + a management command in `apps/notifications/management/commands/` |
| Add a new CSV/PDF export | `apps/reports/views.py` |
| Add a new status choice | `apps/<app>/choices.py`, then update `docs/00_COMMON_CONTEXT/SHARED_CONSTANTS.md` in the same PR |
