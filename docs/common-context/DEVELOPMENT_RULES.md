# DEVELOPMENT_RULES.md

These rules apply to every line of code written for TransitOps, by humans or by AI assistants. They exist to keep a multi-developer, time-boxed hackathon codebase consistent, mergeable, and free of the kind of subtle bugs that come from ad hoc conventions.

## 1. Guiding Principles

1. **Simple architecture over clever architecture.** This is an 8-hour build. Do not introduce abstractions (custom middleware stacks, service-locator patterns, generic repository layers) that a college-level Django developer would not recognize immediately.
2. **Business rules live in the model layer, not the view layer.** Any rule listed in `PROJECT_OVERVIEW.md` Section 7 must be enforced by a `django-fsm-2` `@transition` guard or a model-level `clean()`/validator — never only by a form or a template conditional. Views orchestrate; models enforce.
3. **Fat models, thin views, dumb templates.** Views should mostly: authenticate/authorize, parse input, call a model method or FSM transition, and return a response (full page or HTMX partial). Templates should not contain business logic beyond simple display conditionals.
4. **No placeholders, ever.** Do not commit `TODO: implement this`, `pass  # fixme`, empty `except:` blocks, or stub functions that return hardcoded data. If a feature is not ready, it does not get merged.
5. **Every model field must have a stated business reason.** If you can't point to a line in `PROJECT_OVERVIEW.md` or `DATABASE_SCHEMA.md` that justifies a field, don't add it without raising it with the team first.

## 2. Django Project Conventions

### 2.1 App Boundaries
The project is split into small, single-responsibility Django apps (see `PROJECT_STRUCTURE.md` for the full list). Rules:
- One app = one bounded concern (e.g. `vehicles`, `drivers`, `trips`, `maintenance`, `finance`, `dashboard`, `notifications`, `accounts`, `core`).
- Cross-app imports are allowed for models (`from vehicles.models import Vehicle`) but **never** import a view or template-rendering function from another app. Cross-app orchestration belongs in the app that owns the primary entity being changed.
- Shared, non-domain-specific utilities (base model classes, permission mixins, constants) live in `core`, not scattered across feature apps.

### 2.2 Custom User Model
- The custom `User` model **must** be defined and set as `AUTH_USER_MODEL` in `settings.py` **before the first migration is ever run.** This is not something the team can fix later without a database reset.
- `User` extends `AbstractUser`, removes the `username` field, and uses `email` as `USERNAME_FIELD`.
- `User` includes an `is_verified` boolean field.
- Role assignment happens via Django's built-in `Group` model, not a custom `role` CharField on `User`. This lets us use Django's native permission system without extra plumbing.

### 2.3 Models
- Every model inherits from a shared `TimeStampedModel` abstract base (in `core/models.py`) providing `created_at` and `updated_at`.
- Use `DecimalField` for all monetary and load-capacity values. **Never use `FloatField` for money or weight.** Standard: `max_digits=10, decimal_places=2` for currency; `max_digits=8, decimal_places=2` for weight/capacity in kilograms.
- Use `PositiveIntegerField` for odometer readings and counts that can never be negative.
- Use `UUIDField(default=uuid.uuid4, editable=False, unique=True)` for the Trip's public identifier (`trip_id`), in addition to the default auto-incrementing primary key.
- All status fields use `TextChoices` (or `django-fsm-2`'s `FSMField` with a `choices` argument) — never raw strings compared with magic values in views. Choices are defined once in `SHARED_CONSTANTS.md`-mirrored `choices.py` modules per app, not duplicated per model file.
- Every `ForeignKey` must declare an explicit `on_delete` — default to `PROTECT` for financial and operational records (Vehicle, Driver referenced from Trip/Maintenance/Fuel/Expense) so historical records can never silently vanish. Use `CASCADE` only where the child record is meaningless without the parent (e.g. deleting a Trip's own sub-notes, if any).
- Every `ForeignKey` and unique-lookup field that will be queried frequently (registration number, license number, status fields used in dispatch filtering) must set `db_index=True` or rely on the automatic index from `unique=True`.
- Model `Meta.ordering` must be explicitly set on every model (never rely on implicit database ordering).

### 2.4 Finite State Machines
- Any field representing a lifecycle state (`Vehicle.status`, `Driver.status`, `Trip.status`) is a `django_fsm.FSMField`.
- State-changing operations are implemented as methods decorated with `@transition(field=status, source=..., target=...)`. Business validation (cargo weight check, availability check, license expiry check) happens **inside** the transition method, before the state change is allowed to complete, by raising `django.core.exceptions.ValidationError` or `django_fsm.TransitionNotAllowed` on failure.
- Views and other code must call the transition method (e.g. `trip.dispatch()`) — direct assignment to `.status` is forbidden anywhere outside the model file and migrations.
- Side effects that must happen atomically with a transition (e.g. dispatching a Trip also sets Vehicle and Driver to `On Trip`) are wrapped in `django.db.transaction.atomic()`.

### 2.5 Views
- Prefer Django's Class-Based Views (`ListView`, `DetailView`, `CreateView`, `UpdateView`) for standard CRUD; use function-based views for HTMX partials and custom workflow endpoints (dispatch, complete trip, close maintenance) where explicit control over the response is clearer.
- Every view that is not the login view must be wrapped with `@login_required` (function-based) or `LoginRequiredMixin` (class-based).
- Role-based restrictions use `@permission_required('app_label.permission_codename')` or `PermissionRequiredMixin`, backed by the permissions defined in `SHARED_CONSTANTS.md`. Do not hand-roll `if request.user.groups.filter(name=...)` checks scattered across views — use the permission system so the Django Admin, API, and UI all respect the same rules.
- HTMX partial views return only the HTML fragment needed for the swap target — never a full page — and live in the same app as the entity they render, in a `partials/` template subfolder.

### 2.6 Forms
- All forms are `ModelForm` subclasses, styled via `django-crispy-forms` + `crispy-tailwind`. Do not write raw HTML `<form>` markup for standard CRUD forms.
- Validation specific to a business rule (e.g. cargo weight vs. vehicle capacity) is implemented in the **model's** `clean()` method or the FSM transition guard, and forms call `full_clean()` so the same validation applies whether the object is created via the web UI, the Django Admin, or a management command. Forms may add *additional* UX-only validation (e.g. required-field messaging) but must not be the only place a business rule is enforced.

### 2.7 Templates
- Base layout lives at `templates/base.html`. All pages extend it.
- Shared partials (navbar, sidebar, KPI cards, status badges) live in `templates/partials/`.
- Feature templates live inside their owning app's `templates/<app_name>/` directory (Django app-namespaced template loading).
- Tailwind utility classes only — no custom CSS files unless a Tailwind utility genuinely cannot express the design; any custom CSS goes in `static/css/custom.css` and must be justified in a code comment.
- Dark mode uses Tailwind's `dark:` variant classes throughout; do not build a separate dark-mode template.

### 2.8 Static Files
- Tailwind is compiled via the `@tailwindcss/cli` build step (see `PROJECT_STRUCTURE.md`), not the Play CDN, so production builds are purged and minified.
- Third-party JS (Leaflet, Chart.js, HTMX) is loaded via `django-compressor`-free `<script>` tags pointing at pinned CDN versions or local `static/vendor/` copies — pin exact versions, never `@latest`.

### 2.9 Settings
- Settings are split: `config/settings/base.py`, `config/settings/development.py`, `config/settings/production.py`. Nobody edits `base.py` for a single environment's needs.
- All secrets (`SECRET_KEY`, database credentials, `OPENWEATHERMAP_API_KEY`, `TWILIO_*`, email provider keys) are read from environment variables via `django-environ` or `python-decouple`. **No secret is ever committed to the repository, including in `.env.example` — that file contains variable names only, with placeholder-obviously-fake values.**

### 2.10 Migrations
- Migrations are committed to version control and never edited after being merged to `main`. If a mistake is found, write a new migration to fix it.
- Run `makemigrations` locally and review the generated file before committing — never blindly trust auto-generated migration code, especially for `AlterField` operations on already-migrated columns.
- Data migrations (e.g. seeding the four Groups and their permissions) are written as explicit migration files with `RunPython`, not as a one-off management command run manually by each developer.

## 3. Naming Conventions

| Item | Convention | Example |
|---|---|---|
| Django app names | lowercase, plural, no underscores | `vehicles`, `drivers`, `trips` |
| Model class names | PascalCase, singular | `Vehicle`, `MaintenanceLog` |
| Model field names | snake_case | `license_expiry_date` |
| FSM status choice constants | UPPER_SNAKE_CASE | `AVAILABLE`, `ON_TRIP` |
| URL names | `app_label:action_object`, snake_case | `trips:dispatch_trip` |
| Template files | snake_case | `trip_detail.html` |
| HTMX partial templates | prefixed with underscore | `_trip_row.html` |
| Django Groups (roles) | Title Case, matches `PROJECT_OVERVIEW.md` exactly | `Fleet Manager`, `Safety Officer` |
| Git branches | `type/short-description` | `feature/trip-dispatch-fsm` |
| Environment variables | UPPER_SNAKE_CASE | `OPENWEATHERMAP_API_KEY` |

## 4. Security Rules

- CSRF protection remains enabled everywhere; HTMX requests must include the CSRF token via the `hx-headers` mechanism documented in `PHASE_01_FOUNDATION`.
- Never disable Django's default password validators.
- All role/permission checks happen server-side. Hiding a button in the UI is a UX nicety, not a security control — the underlying view must independently enforce the permission.
- File uploads (vehicle documents, bonus feature) are validated for content type and size server-side, and stored outside of publicly executable paths.
- Do not log sensitive data (passwords, full license numbers, API keys) at any log level.

## 5. Error Handling

- Business rule violations raise `django.core.exceptions.ValidationError` with a clear, user-facing message (e.g. "Cargo weight (600 kg) exceeds vehicle maximum load capacity (500 kg).").
- Views catch expected `ValidationError`/`TransitionNotAllowed` exceptions and re-render the form/partial with the error message attached — they do not let these bubble up into a generic 500 page.
- Unexpected exceptions are allowed to raise normally in development (`DEBUG=True`) and are logged and shown as a generic error page in production (`DEBUG=False`).

## 6. Testing Rules

- Every FSM transition (`dispatch`, `complete`, `cancel`, `start_maintenance`, `end_maintenance`) has at least one test proving the legal path succeeds and one test proving the illegal path is blocked.
- Every mandatory business rule in `PROJECT_OVERVIEW.md` Section 7 has a corresponding test in `PHASE_06_TESTING`.
- Tests use Django's `TestCase` with the test database — never run tests against a shared development database.
- Full testing strategy, coverage expectations, and the test checklist live in `PHASE_06_TESTING/`; this file only states that tests are mandatory, not optional, even under hackathon time pressure.

## 7. Code Style

- Follow PEP 8. Format with `black` (default line length) and sort imports with `isort` before every commit.
- Docstrings are required on every model class (one sentence describing what it represents) and on every FSM transition method (what the transition does and what it validates).
- No commented-out code blocks in merged commits — delete dead code, git history preserves it.

## 8. Dependency Management

- All dependencies are pinned in `requirements.txt` (or `pyproject.toml` if the team adopts Poetry) with exact versions, not ranges, for reproducibility during the hackathon.
- New dependencies require a one-line justification in the PR description ("why this package and not Django built-ins").
