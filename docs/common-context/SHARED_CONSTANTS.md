# SHARED_CONSTANTS.md

This document is the single source of truth for every enumerated value, threshold, formula, and permission codename used across TransitOps. Code must reference these values via a `choices.py` or `constants.py` module — never hardcode a status string or threshold number directly in a view, template, or signal handler.

## 1. Status Choices

### 1.1 Vehicle Status (`apps/vehicles/choices.py` — `VehicleStatus`)

| Constant | DB Value | Display Label | Dispatch Eligible? |
|---|---|---|---|
| `AVAILABLE` | `available` | Available | Yes |
| `ON_TRIP` | `on_trip` | On Trip | No |
| `IN_SHOP` | `in_shop` | In Shop | No |
| `RETIRED` | `retired` | Retired | No |

```python
from django.db import models

class VehicleStatus(models.TextChoices):
    AVAILABLE = "available", "Available"
    ON_TRIP = "on_trip", "On Trip"
    IN_SHOP = "in_shop", "In Shop"
    RETIRED = "retired", "Retired"
```

### 1.2 Driver Status (`apps/drivers/choices.py` — `DriverStatus`)

| Constant | DB Value | Display Label | Dispatch Eligible? |
|---|---|---|---|
| `AVAILABLE` | `available` | Available | Yes (if license valid) |
| `ON_TRIP` | `on_trip` | On Trip | No |
| `OFF_DUTY` | `off_duty` | Off Duty | No |
| `SUSPENDED` | `suspended` | Suspended | No |

```python
from django.db import models

class DriverStatus(models.TextChoices):
    AVAILABLE = "available", "Available"
    ON_TRIP = "on_trip", "On Trip"
    OFF_DUTY = "off_duty", "Off Duty"
    SUSPENDED = "suspended", "Suspended"
```

### 1.3 Trip Status (`apps/trips/choices.py` — `TripStatus`)

| Constant | DB Value | Display Label |
|---|---|---|
| `DRAFT` | `draft` | Draft |
| `DISPATCHED` | `dispatched` | Dispatched |
| `COMPLETED` | `completed` | Completed |
| `CANCELLED` | `cancelled` | Cancelled |

```python
from django.db import models

class TripStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    DISPATCHED = "dispatched", "Dispatched"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
```

**Legal transition graph:**

```
DRAFT ──dispatch──> DISPATCHED ──complete──> COMPLETED
                         │
                         └──cancel──> CANCELLED
```

### 1.4 Maintenance Status (`apps/maintenance/choices.py` — `MaintenanceStatus`)

| Constant | DB Value | Display Label |
|---|---|---|
| `OPEN` | `open` | Open |
| `CLOSED` | `closed` | Closed |

```python
from django.db import models

class MaintenanceStatus(models.TextChoices):
    OPEN = "open", "Open"
    CLOSED = "closed", "Closed"
```

### 1.5 Vehicle Type (`apps/vehicles/choices.py` — `VehicleType`)

| Constant | DB Value | Display Label |
|---|---|---|
| `HEAVY_TRUCK` | `heavy_truck` | Heavy Truck |
| `CARGO_VAN` | `cargo_van` | Cargo Van |
| `PICKUP` | `pickup` | Pickup |
| `MOTORCYCLE` | `motorcycle` | Motorcycle |
| `TRAILER` | `trailer` | Trailer |

### 1.6 License Category (`apps/drivers/choices.py` — `LicenseCategory`)

| Constant | DB Value | Display Label |
|---|---|---|
| `LIGHT` | `light` | Light Vehicle |
| `HEAVY` | `heavy` | Heavy Vehicle |
| `COMMERCIAL` | `commercial` | Commercial |
| `MOTORCYCLE` | `motorcycle` | Motorcycle |

### 1.7 Expense Type (`apps/finance/choices.py` — `ExpenseType`)

| Constant | DB Value | Display Label |
|---|---|---|
| `TOLL` | `toll` | Toll |
| `FINE` | `fine` | Fine |
| `PARKING` | `parking` | Parking |
| `OTHER` | `other` | Other |

## 2. Roles (Django Groups)

Role names **must** match these strings exactly (case-sensitive) everywhere: Group seeding migration, permission checks, documentation, and UI labels.

| Role | Group Name |
|---|---|
| Fleet Manager | `Fleet Manager` |
| Driver | `Driver` |
| Safety Officer | `Safety Officer` |
| Financial Analyst | `Financial Analyst` |

## 3. Permission Matrix

Permissions use Django's default auto-generated codenames (`add_<model>`, `change_<model>`, `delete_<model>`, `view_<model>`) at the app level (`app_label.codename`).

| Role | Vehicle | Driver | Trip | MaintenanceLog | FuelLog | ExpenseLog |
|---|---|---|---|---|---|---|
| **Fleet Manager** | add, change, delete, view | view | view | add, change, delete, view | view | view |
| **Driver** | view | view (own profile only, enforced in view logic) | view (own trips), change (status/odometer on own trips) | view | add | add |
| **Safety Officer** | view | add, change, delete, view | view | view | — | — |
| **Financial Analyst** | view | view | view | view | add, change, delete, view | add, change, delete, view |

**Important:** Django's permission system is model-level, not row-level. "Own trips only" and "own profile only" restrictions for the Driver role are enforced by queryset filtering in the view (`Trip.objects.filter(driver__user=request.user)`), in addition to the model-level `view_trip`/`change_trip` permission. Document this explicitly in any view that relies on it.

## 4. Business Rule Thresholds and Formulas

### 4.1 License Expiry Reminder Window
```python
LICENSE_EXPIRY_REMINDER_DAYS = 30
```
Drivers with `license_expiry_date` less than `LICENSE_EXPIRY_REMINDER_DAYS` from today trigger an email (Safety Officer) and SMS (Driver) alert via the scheduled notification command.

### 4.2 Predictive Maintenance Threshold
```python
MAINTENANCE_DUE_KM_THRESHOLD = 15000  # km since last recorded maintenance
```
If `vehicle.current_odometer_km - vehicle.last_maintenance_odometer_km >= MAINTENANCE_DUE_KM_THRESHOLD`, the vehicle is flagged "Maintenance Due" on the Fleet Manager dashboard.

### 4.3 Engine Hours to Mileage Conversion
```python
ENGINE_HOURS_TO_MILEAGE_FACTOR = 60
approximate_mileage_km = engine_hours * ENGINE_HOURS_TO_MILEAGE_FACTOR
```
Used to normalize wear-and-tear tracking for vehicles that idle frequently (e.g. urban delivery vans), where raw odometer mileage understates usage.

### 4.4 Fleet Utilization
```
Utilization (%) = (Total Operating Hours / Total Available Hours) × 100
```
"Operating Hours" = sum of time each vehicle spent in `ON_TRIP` status within the reporting period. "Available Hours" = total elapsed time in the reporting period across all non-`RETIRED` vehicles.

### 4.5 Vehicle ROI
```
ROI = (Revenue − (Maintenance Costs + Fuel Costs)) / Acquisition Cost
```
"Revenue" is either a manually recorded per-trip revenue figure (if the team adds a `revenue` field to `Trip` — see `PHASE_04_ANALYTICS`) or, in the MVP scope, may be treated as a Financial Analyst-entered figure. "Maintenance Costs" and "Fuel Costs" are the summed `MaintenanceLog.total_cost` and `FuelLog.cost` for the vehicle.

### 4.6 Fuel Efficiency
```
Efficiency (km/L) = Distance Traveled (km) / Fuel Consumed (Liters)
```
Calculated per trip and averaged across the vehicle's trip history for the vehicle-level figure.

### 4.7 Operational Cost (per Vehicle)
```
Operational Cost = Sum(MaintenanceLog.total_cost) + Sum(FuelLog.cost) + Sum(ExpenseLog.amount)
```

### 4.8 Maintenance KPIs
```
MTTR (Mean Time to Repair) = Total Time Spent on Repairs / Total Number of Repairs
MTBF (Mean Time Between Failures) = Total Operating Time / Total Number of Failures
```
"Repairs" = closed `MaintenanceLog` records; "Time Spent on Repairs" = `service_date`-to-close duration if tracked, otherwise a fixed estimation documented in `PHASE_04_ANALYTICS`.

## 5. Cargo Weight Validation Rule
```python
if trip.cargo_weight_kg > trip.vehicle.max_load_capacity_kg:
    raise ValidationError(
        f"Cargo weight ({trip.cargo_weight_kg} kg) exceeds vehicle maximum "
        f"load capacity ({trip.vehicle.max_load_capacity_kg} kg)."
    )
```
Enforced inside the `Trip.dispatch()` FSM transition guard — see `PHASE_03_BUSINESS_LOGIC`.

## 6. Dashboard KPI Definitions

| KPI | Definition |
|---|---|
| Active Vehicles | Count of `Vehicle` where `status != RETIRED` |
| Available Vehicles | Count of `Vehicle` where `status == AVAILABLE` |
| Vehicles in Maintenance | Count of `Vehicle` where `status == IN_SHOP` |
| Active Trips | Count of `Trip` where `status == DISPATCHED` |
| Pending Trips | Count of `Trip` where `status == DRAFT` |
| Drivers On Duty | Count of `Driver` where `status in [AVAILABLE, ON_TRIP]` |
| Fleet Utilization (%) | See Section 4.4 |

## 7. External API Configuration Keys (Environment Variables)

| Variable | Purpose |
|---|---|
| `OPENWEATHERMAP_API_KEY` | Real-time weather lookups for trip destinations |
| `OSRM_BASE_URL` | Base URL of the OSRM routing server (public demo server or self-hosted) |
| `TWILIO_ACCOUNT_SID` | Twilio SMS sending |
| `TWILIO_AUTH_TOKEN` | Twilio SMS sending |
| `TWILIO_FROM_NUMBER` | Twilio SMS sending origin number |
| `ANYMAIL_ESP_API_KEY` | Transactional email provider (SendGrid/Mailgun/Postmark) key, exact variable name depends on chosen ESP per Anymail docs |
| `DEFAULT_FROM_EMAIL` | Sender address for license expiry and system emails |

All are read via environment variables per `DEVELOPMENT_RULES.md` Section 2.9 — never hardcoded.

## 8. Naming Constants for HTMX Targets

To keep HTMX `hx-target` IDs consistent across templates:

| Region | DOM ID |
|---|---|
| Dashboard KPI row | `#kpi-row` |
| Dashboard chart panel | `#chart-panel` |
| Vehicle list table body | `#vehicle-table-body` |
| Driver list table body | `#driver-table-body` |
| Trip list table body | `#trip-table-body` |
| Active trip map container | `#trip-map` |
| Generic form modal | `#modal-container` |
