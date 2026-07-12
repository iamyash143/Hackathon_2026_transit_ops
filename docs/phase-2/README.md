# Phase 2 — Core Modules

## Goal

Implement all five core business modules as independent Django apps. Each module is owned by one developer and can be built in parallel once Phase 1 is merged.

## Phase Objective

By the end of Phase 2:
- Vehicle Registry is fully operational with CRUD and status lifecycle
- Driver Management is fully operational with compliance tracking
- Trip Management enforces FSM transitions and all mandatory business rules
- Maintenance module locks vehicles out of dispatch automatically
- Fuel & Expense module tracks operational costs per vehicle
- All modules are wired into Django Admin for immediate data entry
- RBAC permissions are assigned to all four groups across all models

## Dependency Order

Phase 1 must be merged before any module begins. Within Phase 2, the order is:

```
Phase 1 (complete)
    │
    ├── VEHICLE_REGISTRY    ←── no Phase 2 dependencies
    ├── DRIVER_MANAGEMENT   ←── no Phase 2 dependencies
    │
    └── MAINTENANCE         ←── depends on VEHICLE_REGISTRY
    └── FUEL_EXPENSE        ←── depends on VEHICLE_REGISTRY
    └── TRIP_MANAGEMENT     ←── depends on VEHICLE_REGISTRY + DRIVER_MANAGEMENT
```

Vehicle and Driver can be built simultaneously from day one. Maintenance, Fuel/Expense, and Trip can begin as soon as Vehicle and Driver models exist (migrations applied) — not necessarily when their UIs are complete.

## Ownership Matrix

| File | Django App | Owner | Can Start |
|---|---|---|---|
| `VEHICLE_REGISTRY.md` | `fleet` | Dev A | Phase 1 merged |
| `DRIVER_MANAGEMENT.md` | `drivers` | Dev B | Phase 1 merged |
| `MAINTENANCE.md` | `maintenance` | Dev C | `fleet` models migrated |
| `FUEL_EXPENSE.md` | `finance` | Dev D | `fleet` models migrated |
| `TRIP_MANAGEMENT.md` | `trips` | Dev E | `fleet` + `drivers` models migrated |

## Django Apps Created in This Phase

| App | Models |
|---|---|
| `fleet` | `Vehicle` |
| `drivers` | `Driver` |
| `trips` | `Trip` |
| `maintenance` | `MaintenanceLog` |
| `finance` | `FuelLog`, `ExpenseLog` |

## Shared Conventions (All Modules)

- All list views are protected with the appropriate mixin from `accounts.mixins`
- All models use `created_at` / `updated_at` auto timestamps
- All admin classes are registered in each app's `admin.py`
- All URLs are namespaced: `fleet:vehicle_list`, `trips:trip_list`, etc.
- FSM transitions live on the model, not in views
- Status fields use `TextChoices` for type safety

## RBAC Permission Assignment

Each module's `apps.py` `ready()` method assigns group permissions after migrations. See implementation pattern in each feature file. Permissions follow the matrix in the Common Context.

## Definition of Done (Phase 2 Complete)

- [ ] All five apps are registered in `INSTALLED_APPS`
- [ ] `python manage.py migrate` is clean across all apps
- [ ] All mandatory business rules from the spec are enforced at the model/FSM level
- [ ] Django Admin allows full CRUD for all models
- [ ] Superuser can navigate all list/detail/create/edit views without errors
- [ ] Each role sees only the views and actions the spec permits
- [ ] No circular imports between apps
