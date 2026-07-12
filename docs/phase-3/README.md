# PHASE 03 — Business Logic

## Purpose

This phase documents the **additional business logic** layered on top of the existing CRUD functionality.
All database models, serializers, views, and CRUD endpoints are assumed to already exist.
Do NOT redesign or re-document the database schema here — refer to `docs/00_COMMON_CONTEXT/` for that.

---

## Scope

| File | What It Covers |
|---|---|
| `RBAC.md` | Permission enforcement per role — what each role can and cannot do |
| `STATUS_AUTOMATION.md` | Automatic status transitions for Vehicles, Drivers, and Trips via FSM |
| `COST_CALCULATIONS.md` | Fuel efficiency, operational cost aggregation, and ROI computation |
| `NOTIFICATIONS.md` | Email/SMS alerts for expiring licenses and maintenance warnings |

---

## What This Phase Is NOT

- It does not cover model field definitions (see Common Context).
- It does not cover URL routing or template design (see Phase 02 and Phase 04).
- It does not cover CSV/PDF export (see Phase 05).
- It does not introduce new models or database tables beyond what is already defined.

---

## Developer Notes

- Every file in this phase targets a **single concern**. Keep implementations isolated.
- FSM transitions are the single source of truth for state changes. Never update `status` fields directly in views.
- All cost calculations run at **query time** using Django ORM aggregation — no denormalized cost fields.
- Notifications are triggered via Django signals and executed via management commands or Celery tasks.

---

## Ownership Map

| Feature | Suggested Owner |
|---|---|
| RBAC | Backend Lead |
| Status Automation (FSM) | Backend Lead |
| Cost Calculations | Any Backend Developer |
| Notifications | Any Backend Developer (after RBAC is stable) |

---

## Dependencies Between Files

```
RBAC.md
  └── Required by all other features (permissions checked before any logic executes)

STATUS_AUTOMATION.md
  └── Required by COST_CALCULATIONS.md (costs computed on trip completion signal)
  └── Required by NOTIFICATIONS.md (maintenance flag set by FSM transition)

COST_CALCULATIONS.md
  └── Feeds dashboard KPIs and Reports (Phase 04/05)

NOTIFICATIONS.md
  └── Standalone — depends only on Driver and MaintenanceLog models
```
