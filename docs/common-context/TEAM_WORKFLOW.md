# TEAM_WORKFLOW.md

This document defines how the team works together during the 8-hour TransitOps build: branching strategy, task ownership, the hour-by-hour execution plan, and communication rules.

## 1. Git Branching Strategy

- `main` is always deployable. Nobody commits directly to `main`.
- One feature branch per unit of work, named `type/short-description`:
  - `feature/` — new functionality (e.g. `feature/trip-dispatch-fsm`)
  - `fix/` — bug fixes (e.g. `fix/vehicle-status-badge`)
  - `docs/` — documentation-only changes (e.g. `docs/database-schema-update`)
  - `chore/` — tooling, config, dependency changes (e.g. `chore/tailwind-v4-setup`)
- Branches are created from the latest `main`, kept small, and merged back via Pull Request as soon as the unit of work is complete and passes `MERGE_CHECKLIST.md`.
- Rebase onto `main` before opening a PR if `main` has moved significantly; avoid long-lived branches during an 8-hour hackathon — anything not merged within ~90 minutes of being opened should be re-scoped smaller.
- Commit messages: short imperative summary line, e.g. `Add Trip.dispatch() FSM transition with cargo weight guard`. No vague messages like `fix stuff` or `wip`.

## 2. Task Ownership by App

Given the app boundaries in `PROJECT_STRUCTURE.md`, task ownership is assigned per app to avoid merge conflicts on the same files. A suggested split for a 4-6 person team:

| Owner Track | Apps | Primary Responsibility |
|---|---|---|
| Track A — Foundation & Identity | `accounts`, `core` | Custom User model, RBAC group seeding, base templates, shared mixins |
| Track B — Fleet & Compliance | `vehicles`, `drivers`, `maintenance` | Vehicle registry, driver management, maintenance workflow, their FSMs |
| Track C — Operations | `trips`, `dashboard` | Trip lifecycle FSM, dispatch workflow, geospatial routing, KPI dashboard |
| Track D — Finance & Reporting | `finance`, `reports`, `notifications` | Fuel/expense tracking, analytics formulas, CSV/PDF export, email/SMS |

If the team is smaller than 4 people, collapse tracks in the order D → C → B → A (Track A must always be staffed first and finished earliest, since every other app depends on the custom User model and base templates existing).

## 3. Hour-by-Hour Execution Plan

This plan assumes an 8-hour session and mirrors the phased structure of `docs/`. Each phase's detailed documents live in the correspondingly named `PHASE_0X` folder.

### Phase 1 — Environment Setup and Database Modeling (Hours 1–2)
- Initialize the Django project using the exact structure in `PROJECT_STRUCTURE.md`.
- Configure PostgreSQL connection and settings split (base/development/production).
- Install pinned dependencies: `django`, `django-fsm-2`, `django-import-export`, `django-crispy-forms`, `crispy-tailwind`, `django-anymail`, `twilio`, `weasyprint`, `django-environ`.
- Define the custom `User` model and set `AUTH_USER_MODEL` **before running any migration.**
- Define `Vehicle`, `Driver`, `Trip`, `MaintenanceLog`, `FuelLog`, `ExpenseLog` models per `DATABASE_SCHEMA.md`.
- Scaffold Django Admin registrations for all models.
- Run and commit initial migrations, including the Group/permission seeding data migration.
- **Exit criteria:** `python manage.py migrate` runs clean on a fresh database; all four Groups exist with correct permissions; superuser can log in via the Django Admin.

### Phase 2 — Finite State Machine and Core Logic Integration (Hours 2–4)
- Implement `django-fsm-2` `@transition` methods on `Vehicle`, `Driver`, and `Trip`.
- Implement the mandatory business rule guards (cargo weight, availability, license expiry) inside the transition methods.
- Implement `post_save` signals connecting `MaintenanceLog` state to `Vehicle.status`.
- Write FSM tests proving both the legal and illegal paths for every transition.
- **Exit criteria:** every mandatory business rule in `PROJECT_OVERVIEW.md` Section 7 has a passing test; illegal transitions raise `TransitionNotAllowed` or `ValidationError`.

### Phase 3 — Frontend Integration and HTMX Prototyping (Hours 4–6)
- Configure Tailwind CSS v4 + Flowbite build pipeline.
- Configure `crispy-tailwind` as the active crispy template pack.
- Build `base.html`, navbar, sidebar, and role-aware navigation.
- Build CRUD views/templates for Vehicle Registry and Driver Management.
- Build the Trip creation flow with HTMX-powered available-vehicle/available-driver filtering.
- Build the RBAC-aware Dashboard shell with HTMX-refreshed KPI cards.
- **Exit criteria:** all four roles can log in and see a dashboard scoped to their role; Vehicle and Driver CRUD works end-to-end through the UI.

### Phase 4 — Geospatial Routing and Advanced Features (Hours 6–7.5)
- Integrate Leaflet.js + Leaflet Routing Machine on the Trip creation page.
- Connect the OSRM API to auto-calculate `planned_distance_km`.
- Integrate Chart.js for dashboard and financial analytics visualizations.
- Integrate the OpenWeatherMap API on the active dispatch screen.
- Implement the predictive maintenance threshold flagging.
- **Exit criteria:** creating a trip via the map interface correctly populates the distance field; dashboard charts render real aggregated data, not placeholder data.

### Phase 5 — Final Polish, Export Validation, and Testing (Hours 7.5–8)
- Validate CSV export for Vehicles, Trips, and Financial records via `django-import-export`.
- Finalize the WeasyPrint PDF trip manifest / financial report view.
- Run the full FSM end-to-end test: create maintenance → vehicle hidden from dispatch → complete trip → both assets return to `Available`.
- Verify Tailwind dark mode toggles correctly across all Flowbite components.
- Run the full `MERGE_CHECKLIST.md` against `main` before the final demo.
- **Exit criteria:** the example workflow in `PROJECT_OVERVIEW.md` Section 8 can be executed live, end-to-end, without an unhandled error.

## 4. Communication Rules

- Post a short update in the team channel whenever you: open a PR, merge a PR, or discover a business rule ambiguity that requires a decision.
- Any change to a model field, status choice, permission, or shared constant is announced immediately — other tracks may be actively writing code that depends on it.
- If you are blocked for more than 10 minutes, say so in the channel rather than working around it silently; a workaround that contradicts `DEVELOPMENT_RULES.md` creates rework for someone else later.
- Ambiguities in the spec are resolved by checking `PROJECT_OVERVIEW.md` and `DATABASE_SCHEMA.md` first. If still unresolved, the track owner makes a call, documents the decision inline in the relevant `00_COMMON_CONTEXT` file, and announces it — do not stall waiting for a meeting during a time-boxed hackathon.

## 5. Standups

Given the 8-hour format, standups are brief and synchronized with phase boundaries rather than run on a fixed clock:
- **Kickoff (start of Hour 1):** confirm track assignments, confirm everyone has the repo cloned and `00_COMMON_CONTEXT` read.
- **Phase checkpoint (end of Hours 2, 4, 6, 7.5):** each track reports exit-criteria status for the phase that just ended. Any track behind schedule gets help reassigned from a track that is ahead.
- **Final sync (Hour 8):** dry run of the demo workflow; freeze `main`.

## 6. Pull Request Process

1. Open the PR against `main` with a description stating what changed and which `PHASE_0X` document it implements.
2. Self-check against `MERGE_CHECKLIST.md` before requesting review.
3. At least one other track owner reviews for: correctness against `DATABASE_SCHEMA.md`/`SHARED_CONSTANTS.md`, adherence to `DEVELOPMENT_RULES.md`, and no placeholder code.
4. Merge via a merge commit or squash (team preference, but be consistent) — do not force-push over `main`.
5. Delete the branch after merge to keep the branch list readable during the hackathon.

## 7. Conflict Resolution Priority

When two developers' work conflicts (e.g. both touched `apps/trips/models.py`):
1. Prefer the change that keeps the FSM transition logic in one place, rather than splitting a single transition's guards across two commits.
2. The developer who merges second is responsible for resolving the conflict and re-running the relevant tests before merging — not the original author.
3. If the conflict reveals a genuine design disagreement (not just overlapping edits), escalate to the track owner immediately rather than silently picking one side.
