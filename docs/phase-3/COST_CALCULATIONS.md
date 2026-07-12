# Cost Calculations

## Goal

Compute and expose operational cost metrics — fuel efficiency, total operational cost per
vehicle, and Vehicle ROI — using Django ORM aggregation at query time.
No cost figures are stored as denormalized fields. All metrics are derived from
`FuelLog` and `MaintenanceLog` records linked to each `Vehicle`.

---

## Scope

- ORM-level aggregation functions for all financial metrics.
- A `metrics.py` module per app to keep calculations out of views and models.
- Property methods on `Vehicle` that delegate to the metrics module.
- A single dashboard context builder that assembles all KPIs in one place.
- No new models. No new URLs. No template work.

---

## Responsibilities

| Metric | Formula | Source Data |
|---|---|---|
| Total Fuel Cost | `SUM(FuelLog.cost)` per vehicle | `FuelLog` |
| Total Maintenance Cost | `SUM(MaintenanceLog.cost)` per vehicle | `MaintenanceLog` |
| Total Operational Cost | Fuel Cost + Maintenance Cost | Both logs |
| Fuel Efficiency | `Distance Traveled / Fuel Consumed (liters)` | `Trip` + `FuelLog` |
| Fleet Utilization | `(Total Operating Hours / Total Available Hours) × 100` | `Trip` start/end times |
| Vehicle ROI | `(Revenue − (Maintenance + Fuel)) / Acquisition Cost` | All three sources |

---

## Django App

`reports/` (create this app if it does not exist, or add `metrics.py` to `vehicles/`)
Recommended: `reports/metrics.py` as a standalone calculation module.

---

## Files to Create / Modify

```
reports/
  __init__.py
  metrics.py          # CREATE — all aggregation functions
  views.py            # MODIFY — call metrics functions to build context
  urls.py             # No changes needed in this phase

vehicles/models.py    # MODIFY — add @property shortcuts that call metrics.py
trips/signals.py      # MODIFY — trigger cost recalculation on trip completion
```

---

## Dependencies

- `STATUS_AUTOMATION.md` must be complete: costs are triggered by `Trip.complete()` signal.
- `FuelLog` and `MaintenanceLog` models must already exist with `cost`, `liters`, and date fields.
- `Trip` model must have `start_time`, `end_time`, `planned_distance`, and `final_odometer` fields.
- `Vehicle` model must have `acquisition_cost` field.

---

## Business Rules

1. Operational cost = `FuelLog.cost` + `MaintenanceLog.cost` for a given vehicle. No other cost categories are included in this figure.
2. Fuel efficiency is calculated **per trip** (`trip.planned_distance / fuellog.liters`) and averaged across the vehicle's lifespan.
3. Fleet utilization is calculated across **all vehicles**, not per vehicle: `(total dispatched hours across fleet) / (total available hours across fleet) × 100`.
4. ROI uses `acquisition_cost` from the Vehicle model. If `acquisition_cost` is zero, ROI is undefined — return `None`, not a division error.
5. Revenue is not captured in Phase 03 scope — ROI denominator calculation is implemented but numerator (`Revenue`) defaults to `0` until a revenue field is added.
6. All monetary aggregation uses `DecimalField` arithmetic — never cast to `float` mid-calculation.

---

## Implementation Steps

### Step 1 — Build the Metrics Module

```python
# reports/metrics.py
from decimal import Decimal
from django.db.models import Sum, Avg, F, ExpressionWrapper, DurationField
from django.utils import timezone


def get_vehicle_fuel_cost(vehicle) -> Decimal:
    from expenses.models import FuelLog
    result = FuelLog.objects.filter(vehicle=vehicle).aggregate(
        total=Sum("cost")
    )
    return result["total"] or Decimal("0.00")


def get_vehicle_maintenance_cost(vehicle) -> Decimal:
    from maintenance.models import MaintenanceLog
    result = MaintenanceLog.objects.filter(vehicle=vehicle).aggregate(
        total=Sum("cost")
    )
    return result["total"] or Decimal("0.00")


def get_vehicle_operational_cost(vehicle) -> Decimal:
    return get_vehicle_fuel_cost(vehicle) + get_vehicle_maintenance_cost(vehicle)


def get_vehicle_fuel_efficiency(vehicle) -> Decimal | None:
    """
    Returns km per liter averaged across all completed trips.
    Returns None if no fuel data exists.
    """
    from expenses.models import FuelLog
    from trips.models import Trip

    trips = Trip.objects.filter(
        vehicle=vehicle,
        status="completed",
        final_odometer__isnull=False,
    )

    total_distance = Decimal("0.00")
    total_liters   = Decimal("0.00")

    for trip in trips:
        try:
            log = FuelLog.objects.get(trip=trip)
            if log.liters and log.liters > 0:
                distance = Decimal(str(trip.planned_distance))
                total_distance += distance
                total_liters   += log.liters
        except FuelLog.DoesNotExist:
            continue

    if total_liters == 0:
        return None
    return round(total_distance / total_liters, 2)


def get_vehicle_roi(vehicle, revenue: Decimal = Decimal("0.00")) -> Decimal | None:
    """
    ROI = (Revenue - (Maintenance + Fuel)) / Acquisition Cost
    Returns None if acquisition_cost is zero to prevent ZeroDivisionError.
    """
    if not vehicle.acquisition_cost or vehicle.acquisition_cost == 0:
        return None

    op_cost = get_vehicle_operational_cost(vehicle)
    roi = (revenue - op_cost) / vehicle.acquisition_cost
    return round(roi, 4)


def get_fleet_utilization() -> Decimal:
    """
    Fleet utilization = (total dispatched hours / total available window hours) * 100
    Computed across ALL vehicles for completed trips in the current month.
    """
    from trips.models import Trip

    now = timezone.now()
    trips = Trip.objects.filter(
        status="completed",
        start_time__month=now.month,
        start_time__year=now.year,
        end_time__isnull=False,
    )

    total_trip_seconds = sum(
        (t.end_time - t.start_time).total_seconds()
        for t in trips
        if t.start_time and t.end_time
    )

    from vehicles.models import Vehicle
    vehicle_count = Vehicle.objects.exclude(status="retired").count()

    if vehicle_count == 0:
        return Decimal("0.00")

    # Available hours = vehicle_count * hours in month
    import calendar
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    total_available_seconds = vehicle_count * days_in_month * 24 * 3600

    utilization = (Decimal(str(total_trip_seconds)) /
                   Decimal(str(total_available_seconds))) * 100
    return round(utilization, 2)


def get_dashboard_kpis() -> dict:
    """
    Assembles all dashboard KPIs into a single dict for the context.
    Called once per dashboard request — not cached in this phase.
    """
    from vehicles.models import Vehicle
    from drivers.models import Driver
    from trips.models import Trip

    vehicles = Vehicle.objects.all()

    return {
        "active_vehicles":      vehicles.filter(status="on_trip").count(),
        "available_vehicles":   vehicles.filter(status="available").count(),
        "in_maintenance":       vehicles.filter(status="in_shop").count(),
        "active_trips":         Trip.objects.filter(status="dispatched").count(),
        "pending_trips":        Trip.objects.filter(status="draft").count(),
        "drivers_on_duty":      Driver.objects.filter(status="on_trip").count(),
        "fleet_utilization":    get_fleet_utilization(),
    }
```

---

### Step 2 — Add Property Shortcuts on Vehicle

```python
# vehicles/models.py
from reports.metrics import (
    get_vehicle_fuel_cost,
    get_vehicle_maintenance_cost,
    get_vehicle_operational_cost,
    get_vehicle_fuel_efficiency,
    get_vehicle_roi,
)

class Vehicle(models.Model):
    # ... existing fields ...

    @property
    def fuel_cost(self):
        return get_vehicle_fuel_cost(self)

    @property
    def maintenance_cost(self):
        return get_vehicle_maintenance_cost(self)

    @property
    def operational_cost(self):
        return get_vehicle_operational_cost(self)

    @property
    def fuel_efficiency(self):
        return get_vehicle_fuel_efficiency(self)

    @property
    def roi(self):
        return get_vehicle_roi(self)
```

> **Note:** These properties execute DB queries each time they are accessed.
> In list views displaying many vehicles, use the bulk aggregation approach below
> instead of iterating `.roi` per object.

---

### Step 3 — Bulk Aggregation for Vehicle List Views

For the reports page listing all vehicles with metrics, avoid N+1 queries:

```python
# reports/views.py
from django.db.models import Sum, OuterRef, Subquery
from vehicles.models import Vehicle
from expenses.models import FuelLog
from maintenance.models import MaintenanceLog
from reports.metrics import get_dashboard_kpis

def reports_view(request):
    fuel_subquery = FuelLog.objects.filter(
        vehicle=OuterRef("pk")
    ).values("vehicle").annotate(total=Sum("cost")).values("total")

    maint_subquery = MaintenanceLog.objects.filter(
        vehicle=OuterRef("pk")
    ).values("vehicle").annotate(total=Sum("cost")).values("total")

    vehicles = Vehicle.objects.annotate(
        total_fuel_cost=Subquery(fuel_subquery),
        total_maint_cost=Subquery(maint_subquery),
    )

    context = {
        "vehicles": vehicles,
        "kpis": get_dashboard_kpis(),
    }
    return render(request, "reports/overview.html", context)
```

In the template:
```django
{{ vehicle.total_fuel_cost|default:"—" }}
{{ vehicle.total_maint_cost|default:"—" }}
```

---

### Step 4 — Trigger on Trip Completion

Wire a signal so the dashboard data stays current after each trip:

```python
# trips/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from trips.models import Trip

@receiver(post_save, sender=Trip)
def on_trip_status_change(sender, instance, **kwargs):
    """
    After a trip is saved in 'completed' state, the FuelLog is already
    created by Trip.complete(). No additional action is needed here in Phase 03.
    Dashboard queries are live — no cache to invalidate.
    Extend this signal in Phase 04 if caching or async chart refresh is added.
    """
    if instance.status == "completed":
        pass  # Hook point for future cache invalidation
```

Connect in `trips/apps.py`:
```python
class TripsConfig(AppConfig):
    def ready(self):
        import trips.signals  # noqa
```

---

## Success Scenario

1. A trip is completed with `planned_distance=450`, `fuel_consumed=50` liters.
2. `get_vehicle_fuel_efficiency(vehicle)` returns `9.00` km/liter.
3. The MaintenanceLog for an oil change costs ₹2,500. `get_vehicle_operational_cost()` returns `FuelCost + 2500`.
4. Dashboard loads and displays correct counts for Active Vehicles, In Shop, and Fleet Utilization %.
5. Reports page loads all vehicles with annotated fuel and maintenance costs in a single query (no N+1).

---

## Definition of Done

- [ ] `reports/metrics.py` contains all six metric functions with correct formulas.
- [ ] `get_dashboard_kpis()` returns accurate counts matching the database state.
- [ ] `Vehicle` model has `fuel_cost`, `maintenance_cost`, `operational_cost`, `fuel_efficiency`, and `roi` properties.
- [ ] Reports list view uses `Subquery` annotation — no per-object property calls in loops.
- [ ] Division by zero handled in `get_vehicle_roi()` (returns `None`) and `get_vehicle_fuel_efficiency()` (returns `None`).
- [ ] All monetary values remain `Decimal` throughout — no `float()` conversions.

---

## AI Instructions

- Never store aggregated costs as model fields — always compute via ORM aggregation from `FuelLog` and `MaintenanceLog`.
- Import `metrics.py` functions lazily inside model properties if there are circular import risks.
- For bulk list views, always use `Subquery` + `annotate()` — never call `vehicle.operational_cost` inside a template loop.
- `get_fleet_utilization()` counts only non-retired vehicles in the denominator — enforce this with `.exclude(status="retired")`.
- ROI revenue field defaults to `Decimal("0.00")` until Phase 05 adds a revenue tracking model. Document this assumption in any comment near the ROI call.
- `get_dashboard_kpis()` must be called **once** per request, assigned to `context["kpis"]`, and unpacked in the template — do not call individual count queries separately in the view.
