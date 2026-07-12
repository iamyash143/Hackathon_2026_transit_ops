# DATABASE_SCHEMA.md

This document is the authoritative entity-relationship schema for TransitOps. Every model implemented in `PHASE_02_CORE_MODULES` must match this schema exactly. If implementation requires a deviation, this document must be updated in the same PR.

## 1. Entity-Relationship Overview

```
User (accounts) ─1───1── Driver (drivers)
                                  │
                                  │ 1
                                  │
                                  * (FK)
Vehicle (vehicles) ──1────────* Trip (trips) *────────1── Driver (drivers)
     │  1                                        
     │
     │ *  (FK)                
MaintenanceLog (maintenance)

Vehicle ──1────* FuelLog (finance) *────0..1── Trip
Vehicle ──1────* ExpenseLog (finance) *────0..1── Trip
```

- A `User` has exactly one `Driver` profile **only if** their role is Driver. Fleet Managers, Safety Officers, and Financial Analysts do not have a `Driver` row.
- A `Vehicle` can have many `Trip`s, `MaintenanceLog`s, `FuelLog`s, and `ExpenseLog`s over its lifetime.
- A `Trip` belongs to exactly one `Vehicle` and exactly one `Driver`.
- A `FuelLog` and an `ExpenseLog` always belong to a `Vehicle`, and optionally to the specific `Trip` during which the cost was incurred.

## 2. `User` (app: `accounts`)

Custom user model, replacing Django's default `User`. Extends `AbstractUser` with `username` removed.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `BigAutoField` | PK | Django default |
| `email` | `EmailField` | `unique=True`, `USERNAME_FIELD` | Used for login instead of username |
| `first_name` | `CharField(max_length=150)` | — | From `AbstractUser` |
| `last_name` | `CharField(max_length=150)` | — | From `AbstractUser` |
| `is_verified` | `BooleanField` | `default=False` | Set `True` after email verification, if implemented; otherwise set `True` at creation by an admin |
| `is_active` | `BooleanField` | `default=True` | From `AbstractUser` |
| `is_staff` | `BooleanField` | `default=False` | Controls Django Admin access |
| `date_joined` | `DateTimeField` | `auto_now_add=True` | From `AbstractUser` |
| `groups` | `ManyToManyField(Group)` | via `AbstractUser` | Determines role — see `SHARED_CONSTANTS.md` |

`USERNAME_FIELD = "email"`, `REQUIRED_FIELDS = []` (only `email` and `password` required to create a superuser via `createsuperuser`).

## 3. `Vehicle` (app: `vehicles`)

The central fleet asset registry.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `BigAutoField` | PK | |
| `registration_number` | `CharField(max_length=20)` | `unique=True`, `db_index=True` | Mandatory business rule: must be unique |
| `name` | `CharField(max_length=100)` | — | Vehicle Name/Model |
| `vehicle_type` | `CharField(max_length=30, choices=VehicleType.choices)` | — | e.g. Heavy Truck, Cargo Van, Pickup — see `SHARED_CONSTANTS.md` |
| `max_load_capacity_kg` | `DecimalField(max_digits=8, decimal_places=2)` | `> 0` (validated in `clean()`) | Used for cargo weight validation |
| `current_odometer_km` | `PositiveIntegerField` | `default=0` | Updated on trip completion |
| `engine_hours` | `PositiveIntegerField` | `default=0` | Used for predictive maintenance (bonus) |
| `acquisition_cost` | `DecimalField(max_digits=12, decimal_places=2)` | `> 0` | Used in ROI calculation |
| `region` | `CharField(max_length=100)` | blank allowed | Used for dashboard filtering |
| `status` | `FSMField(choices=VehicleStatus.choices)` | `default=VehicleStatus.AVAILABLE` | Governs dispatch eligibility |
| `created_at` | `DateTimeField` | `auto_now_add=True` | From `TimeStampedModel` |
| `updated_at` | `DateTimeField` | `auto_now=True` | From `TimeStampedModel` |

**Status values:** `AVAILABLE`, `ON_TRIP`, `IN_SHOP`, `RETIRED` (see `SHARED_CONSTANTS.md`).

**Meta:** `ordering = ["registration_number"]`

## 4. `Driver` (app: `drivers`)

One-to-one extension of `User`, representing a driving employee.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `BigAutoField` | PK | |
| `user` | `OneToOneField(User, on_delete=PROTECT)` | `unique=True` | Links to login credentials |
| `full_name` | `CharField(max_length=150)` | — | Denormalized for display convenience |
| `license_number` | `CharField(max_length=30)` | `unique=True`, `db_index=True` | |
| `license_category` | `CharField(max_length=20, choices=LicenseCategory.choices)` | — | e.g. Light, Heavy, Commercial |
| `license_expiry_date` | `DateField` | — | Used for compliance checks and expiry reminders |
| `contact_number` | `CharField(max_length=20)` | — | |
| `safety_score` | `PositiveSmallIntegerField` | `validators=[MinValueValidator(0), MaxValueValidator(100)]`, `default=100` | Managed by Safety Officer |
| `status` | `FSMField(choices=DriverStatus.choices)` | `default=DriverStatus.AVAILABLE` | Governs dispatch eligibility |
| `created_at` | `DateTimeField` | `auto_now_add=True` | |
| `updated_at` | `DateTimeField` | `auto_now=True` | |

**Status values:** `AVAILABLE`, `ON_TRIP`, `OFF_DUTY`, `SUSPENDED`.

**Meta:** `ordering = ["full_name"]`

**Compliance rule:** a `Driver` is eligible for dispatch only if `status == AVAILABLE` **and** `license_expiry_date >= today`. This is enforced in the `Trip.dispatch()` transition guard, not only via the `status` field, because license expiry is date-driven and not itself a state transition.

## 5. `Trip` (app: `trips`)

The junction entity mapping a Driver, a Vehicle, and a route.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `BigAutoField` | PK | Internal PK |
| `trip_id` | `UUIDField(default=uuid.uuid4, editable=False)` | `unique=True`, `db_index=True` | Public-facing trip identifier |
| `vehicle` | `ForeignKey(Vehicle, on_delete=PROTECT, related_name="trips")` | — | |
| `driver` | `ForeignKey(Driver, on_delete=PROTECT, related_name="trips")` | — | |
| `source` | `CharField(max_length=255)` | — | Address text |
| `source_lat` | `DecimalField(max_digits=9, decimal_places=6)` | nullable | Populated by Leaflet/Nominatim geocoding |
| `source_lng` | `DecimalField(max_digits=9, decimal_places=6)` | nullable | |
| `destination` | `CharField(max_length=255)` | — | Address text |
| `destination_lat` | `DecimalField(max_digits=9, decimal_places=6)` | nullable | |
| `destination_lng` | `DecimalField(max_digits=9, decimal_places=6)` | nullable | |
| `cargo_weight_kg` | `DecimalField(max_digits=8, decimal_places=2)` | `> 0` | Validated against `vehicle.max_load_capacity_kg` |
| `planned_distance_km` | `DecimalField(max_digits=8, decimal_places=2)` | `> 0` | Auto-filled from OSRM route response where available |
| `start_time` | `DateTimeField` | nullable | Set on dispatch |
| `end_time` | `DateTimeField` | nullable | Set on completion |
| `final_odometer_km` | `PositiveIntegerField` | nullable | Entered on completion |
| `fuel_consumed_liters` | `DecimalField(max_digits=7, decimal_places=2)` | nullable | Entered on completion; generates a `FuelLog` |
| `status` | `FSMField(choices=TripStatus.choices)` | `default=TripStatus.DRAFT` | |
| `created_at` | `DateTimeField` | `auto_now_add=True` | |
| `updated_at` | `DateTimeField` | `auto_now=True` | |

**Status values:** `DRAFT`, `DISPATCHED`, `COMPLETED`, `CANCELLED`.

**Legal transitions:** `DRAFT → DISPATCHED`, `DISPATCHED → COMPLETED`, `DISPATCHED → CANCELLED`. No other transitions are legal (e.g. `DRAFT → COMPLETED` is illegal, `COMPLETED → *` is illegal/terminal).

**Meta:** `ordering = ["-created_at"]`

## 6. `MaintenanceLog` (app: `maintenance`)

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `BigAutoField` | PK | |
| `vehicle` | `ForeignKey(Vehicle, on_delete=PROTECT, related_name="maintenance_logs")` | — | |
| `service_date` | `DateField` | — | |
| `description` | `TextField` | — | Description of work performed |
| `total_cost` | `DecimalField(max_digits=10, decimal_places=2)` | `>= 0` | Included in operational cost aggregation |
| `status` | `CharField(max_length=10, choices=MaintenanceStatus.choices)` | `default=MaintenanceStatus.OPEN` | `OPEN` or `CLOSED` |
| `created_at` | `DateTimeField` | `auto_now_add=True` | |
| `updated_at` | `DateTimeField` | `auto_now=True` | |

**Business rule:** creating a `MaintenanceLog` with `status=OPEN` triggers `vehicle.start_maintenance()` via a `post_save` signal. Setting `status=CLOSED` on an existing record triggers `vehicle.end_maintenance()`.

**Meta:** `ordering = ["-service_date"]`

## 7. `FuelLog` (app: `finance`)

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `BigAutoField` | PK | |
| `vehicle` | `ForeignKey(Vehicle, on_delete=PROTECT, related_name="fuel_logs")` | — | |
| `trip` | `ForeignKey(Trip, on_delete=SET_NULL, related_name="fuel_logs", null=True, blank=True)` | optional | Populated automatically when a trip is completed |
| `liters` | `DecimalField(max_digits=7, decimal_places=2)` | `> 0` | |
| `cost` | `DecimalField(max_digits=10, decimal_places=2)` | `>= 0` | |
| `date` | `DateField` | — | |
| `created_at` | `DateTimeField` | `auto_now_add=True` | |

**Meta:** `ordering = ["-date"]`

## 8. `ExpenseLog` (app: `finance`)

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `BigAutoField` | PK | |
| `vehicle` | `ForeignKey(Vehicle, on_delete=PROTECT, related_name="expense_logs")` | — | |
| `trip` | `ForeignKey(Trip, on_delete=SET_NULL, related_name="expense_logs", null=True, blank=True)` | optional | |
| `expense_type` | `CharField(max_length=30, choices=ExpenseType.choices)` | — | e.g. Toll, Fine, Parking — see `SHARED_CONSTANTS.md` |
| `amount` | `DecimalField(max_digits=10, decimal_places=2)` | `>= 0` | |
| `date` | `DateField` | — | |
| `created_at` | `DateTimeField` | `auto_now_add=True` | |

**Meta:** `ordering = ["-date"]`

## 9. Indexing Strategy

| Model | Indexed Field(s) | Reason |
|---|---|---|
| `Vehicle` | `registration_number` (unique) | Fast lookup, uniqueness enforcement |
| `Vehicle` | `status` | Frequently filtered in dispatch querysets and dashboard KPIs |
| `Driver` | `license_number` (unique) | Fast lookup, uniqueness enforcement |
| `Driver` | `status`, `license_expiry_date` | Frequently filtered in dispatch eligibility queries |
| `Trip` | `trip_id` (unique) | Public identifier lookup |
| `Trip` | `status` | Dashboard active/pending trip counts |
| `Trip` | `vehicle_id`, `driver_id` (FK indexes, automatic) | Join performance |

## 10. Referential Integrity Rules

- `on_delete=PROTECT` is used on every ForeignKey from a transactional model (`Trip`, `MaintenanceLog`, `FuelLog`, `ExpenseLog`) back to `Vehicle` or `Driver`. A `Vehicle` or `Driver` with historical records **cannot** be hard-deleted; retiring/suspending them is the only supported lifecycle exit. This preserves financial and compliance history.
- `on_delete=SET_NULL` is used on the optional `trip` ForeignKey on `FuelLog`/`ExpenseLog` — deleting a `Trip` (which should be rare/never in practice, since trips are cancelled, not deleted) does not delete the associated financial records.

## 11. Aggregate/Computed Values (Not Stored, Calculated On Read)

These values are **never** stored as database columns — they are calculated at query time via Django ORM aggregation (`Sum`, `Avg`, `Count`, `F` expressions) to avoid data drift. Formulas are defined once in `SHARED_CONSTANTS.md`.

- Vehicle Operational Cost = Sum of related `MaintenanceLog.total_cost` (status irrelevant) + Sum of related `FuelLog.cost` + Sum of related `ExpenseLog.amount`.
- Fleet Utilization (%).
- Vehicle ROI.
- Fuel Efficiency (km/liter).
- Fleet-wide and per-vehicle Mean Time to Repair (MTTR) and Mean Time Between Failures (MTBF).

## 12. Role/Group Data (Seeded, Not User-Editable)

Four `django.contrib.auth.models.Group` rows are created via a data migration in `apps/accounts/migrations/`:

- `Fleet Manager`
- `Driver`
- `Safety Officer`
- `Financial Analyst`

Each Group's `permissions` M2M is populated with the exact codenames listed in `SHARED_CONSTANTS.md` Section 3. This migration is the single source of truth for permission assignment — do not assign permissions ad hoc through the Django Admin in a way that isn't reflected back into the migration file.
