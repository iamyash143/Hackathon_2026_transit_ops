# Status Automation (Finite State Machine)

## Goal

Enforce all mandatory status transitions for `Vehicle`, `Driver`, and `Trip` models
using a Finite State Machine (FSM). Status fields must **never** be set directly in views.
All transitions run through decorated FSM methods that validate preconditions and
apply side effects atomically.

---

## Scope

- FSM transition methods on `Vehicle`, `Driver`, and `Trip` models.
- Side-effect hooks that cascade status changes across related models.
- Guard functions that enforce business rule preconditions.
- No new models, no new URLs, no template changes.

---

## Responsibilities

| Model | Valid States | Transitions |
|---|---|---|
| `Vehicle` | `available` → `on_trip` → `available` | dispatch, return, send_to_shop, close_maintenance, retire |
| `Driver` | `available` → `on_trip` → `available` | dispatch, return, suspend, reinstate |
| `Trip` | `draft` → `dispatched` → `completed` / `cancelled` | dispatch, complete, cancel |

---

## Django App

`trips/`, `vehicles/`, `drivers/`
FSM methods live on the respective models in each app.

---

## Files to Create / Modify

```
# Install dependency first:
# pip install django-fsm-2

vehicles/models.py       # MODIFY — add FSM transitions to Vehicle
drivers/models.py        # MODIFY — add FSM transitions to Driver
trips/models.py          # MODIFY — add FSM transitions to Trip + orchestration logic
trips/signals.py         # CREATE — post-transition signals for cost sync
core/exceptions.py       # CREATE — custom FSM exception classes
```

---

## Dependencies

- `django-fsm-2` package installed and added to `INSTALLED_APPS` as `django_fsm`.
- All three models (`Vehicle`, `Driver`, `Trip`) must already exist with their `status` fields.
- `COST_CALCULATIONS.md` depends on the `post_save` signal fired when a trip completes.
- `NOTIFICATIONS.md` depends on the maintenance flag set during `send_to_shop` transition.

---

## Business Rules

1. `Retired` and `In Shop` vehicles never appear in dispatch selection pools.
2. Drivers with `Suspended` status or an expired `license_expiry` date cannot be dispatched.
3. A `Vehicle` or `Driver` already `On Trip` cannot be assigned to a second concurrent trip.
4. `Cargo Weight` must not exceed the vehicle's `max_load_capacity` — enforced as an FSM guard.
5. Dispatching a trip atomically sets both `Vehicle.status` and `Driver.status` to `on_trip`.
6. Completing a trip atomically sets both back to `available` and updates `Vehicle.odometer`.
7. Cancelling a `dispatched` trip immediately restores both `Vehicle` and `Driver` to `available`.
8. Creating a `MaintenanceLog` (active) automatically sets `Vehicle.status` to `in_shop`.
9. Closing a `MaintenanceLog` restores `Vehicle.status` to `available` unless it is `retired`.

---

## Implementation Steps

### Step 1 — Install and Configure django-fsm-2

```python
# settings.py
INSTALLED_APPS = [
    ...
    "django_fsm",
]
```

---

### Step 2 — Vehicle FSM Transitions

```python
# vehicles/models.py
from django_fsm import FSMField, transition

class Vehicle(models.Model):
    STATUS_AVAILABLE  = "available"
    STATUS_ON_TRIP    = "on_trip"
    STATUS_IN_SHOP    = "in_shop"
    STATUS_RETIRED    = "retired"

    STATUS_CHOICES = [
        (STATUS_AVAILABLE, "Available"),
        (STATUS_ON_TRIP,   "On Trip"),
        (STATUS_IN_SHOP,   "In Shop"),
        (STATUS_RETIRED,   "Retired"),
    ]

    status = FSMField(default=STATUS_AVAILABLE, choices=STATUS_CHOICES, protected=True)

    @transition(field=status, source=STATUS_AVAILABLE, target=STATUS_ON_TRIP)
    def dispatch(self):
        """Called atomically when a trip is dispatched."""
        pass

    @transition(field=status, source=STATUS_ON_TRIP, target=STATUS_AVAILABLE)
    def return_from_trip(self):
        """Called atomically when a trip completes or is cancelled."""
        pass

    @transition(field=status, source=STATUS_AVAILABLE, target=STATUS_IN_SHOP)
    def send_to_shop(self):
        """Called when an active MaintenanceLog is created for this vehicle."""
        pass

    @transition(field=status, source=STATUS_IN_SHOP, target=STATUS_AVAILABLE)
    def close_maintenance(self):
        """Called when a MaintenanceLog is closed and vehicle is not retired."""
        pass

    @transition(field=status, source="*", target=STATUS_RETIRED)
    def retire(self):
        """Irreversible. Can be called from any state by Fleet Manager."""
        pass
```

---

### Step 3 — Driver FSM Transitions

```python
# drivers/models.py
from django_fsm import FSMField, transition

class Driver(models.Model):
    STATUS_AVAILABLE  = "available"
    STATUS_ON_TRIP    = "on_trip"
    STATUS_OFF_DUTY   = "off_duty"
    STATUS_SUSPENDED  = "suspended"

    STATUS_CHOICES = [
        (STATUS_AVAILABLE,  "Available"),
        (STATUS_ON_TRIP,    "On Trip"),
        (STATUS_OFF_DUTY,   "Off Duty"),
        (STATUS_SUSPENDED,  "Suspended"),
    ]

    status = FSMField(default=STATUS_AVAILABLE, choices=STATUS_CHOICES, protected=True)

    @transition(field=status, source=STATUS_AVAILABLE, target=STATUS_ON_TRIP)
    def dispatch(self):
        pass

    @transition(field=status, source=STATUS_ON_TRIP, target=STATUS_AVAILABLE)
    def return_from_trip(self):
        pass

    @transition(field=status, source=[STATUS_AVAILABLE, STATUS_OFF_DUTY],
                target=STATUS_SUSPENDED)
    def suspend(self):
        pass

    @transition(field=status, source=STATUS_SUSPENDED, target=STATUS_AVAILABLE)
    def reinstate(self):
        pass
```

---

### Step 4 — Trip FSM Transitions with Guards and Side Effects

```python
# trips/models.py
from django.utils import timezone
from django_fsm import FSMField, transition, TransitionNotAllowed
from core.exceptions import (
    CargoOverloadError, DriverUnavailableError,
    VehicleUnavailableError, LicenseExpiredError,
)

class Trip(models.Model):
    STATUS_DRAFT      = "draft"
    STATUS_DISPATCHED = "dispatched"
    STATUS_COMPLETED  = "completed"
    STATUS_CANCELLED  = "cancelled"

    STATUS_CHOICES = [
        (STATUS_DRAFT,      "Draft"),
        (STATUS_DISPATCHED, "Dispatched"),
        (STATUS_COMPLETED,  "Completed"),
        (STATUS_CANCELLED,  "Cancelled"),
    ]

    status = FSMField(default=STATUS_DRAFT, choices=STATUS_CHOICES, protected=True)

    # ── Guards ────────────────────────────────────────────────────────────────

    def _guard_dispatch(self):
        errors = []

        if self.cargo_weight > self.vehicle.max_load_capacity:
            errors.append(CargoOverloadError(
                f"Cargo {self.cargo_weight}kg exceeds vehicle capacity "
                f"{self.vehicle.max_load_capacity}kg."
            ))
        if self.vehicle.status != "available":
            errors.append(VehicleUnavailableError(
                f"Vehicle {self.vehicle.registration_number} is {self.vehicle.status}."
            ))
        if self.driver.status != "available":
            errors.append(DriverUnavailableError(
                f"Driver {self.driver} is {self.driver.status}."
            ))
        if self.driver.license_expiry < timezone.now().date():
            errors.append(LicenseExpiredError(
                f"Driver {self.driver} has an expired license."
            ))
        if errors:
            raise errors[0]   # Raise the first blocking error

    # ── Transitions ───────────────────────────────────────────────────────────

    @transition(
        field=status,
        source=STATUS_DRAFT,
        target=STATUS_DISPATCHED,
        conditions=[lambda self: self._guard_dispatch() or True],
    )
    def dispatch(self):
        """
        Atomically transitions trip to Dispatched and updates Vehicle + Driver.
        Call _guard_dispatch() explicitly in the view before calling this method
        to surface validation errors with user-friendly messages.
        """
        self._guard_dispatch()           # raises on failure
        self.start_time = timezone.now()
        self.vehicle.dispatch()
        self.vehicle.save(update_fields=["status"])
        self.driver.dispatch()
        self.driver.save(update_fields=["status"])

    @transition(field=status, source=STATUS_DISPATCHED, target=STATUS_COMPLETED)
    def complete(self, final_odometer: int, fuel_consumed: float):
        """
        Marks trip completed.
        Caller must pass final_odometer and fuel_consumed from the form.
        """
        from expenses.models import FuelLog   # avoid circular import

        self.end_time = timezone.now()
        self.final_odometer = final_odometer

        # Update vehicle odometer
        self.vehicle.odometer = final_odometer
        self.vehicle.return_from_trip()
        self.vehicle.save(update_fields=["status", "odometer"])

        self.driver.return_from_trip()
        self.driver.save(update_fields=["status"])

        # Auto-create fuel log
        FuelLog.objects.create(
            vehicle=self.vehicle,
            trip=self,
            liters=fuel_consumed,
            cost=0,           # Financial Analyst updates cost separately
            date=timezone.now().date(),
        )

    @transition(field=status, source=STATUS_DISPATCHED, target=STATUS_CANCELLED)
    def cancel(self):
        """Cancels a dispatched trip and releases Vehicle + Driver."""
        self.vehicle.return_from_trip()
        self.vehicle.save(update_fields=["status"])
        self.driver.return_from_trip()
        self.driver.save(update_fields=["status"])
```

---

### Step 5 — Maintenance Signal (Vehicle → In Shop)

```python
# maintenance/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from maintenance.models import MaintenanceLog

@receiver(post_save, sender=MaintenanceLog)
def handle_maintenance_status(sender, instance, created, **kwargs):
    vehicle = instance.vehicle

    if created and instance.status == "open":
        # New active maintenance → lock vehicle
        if vehicle.status == "available":
            vehicle.send_to_shop()
            vehicle.save(update_fields=["status"])

    elif not created and instance.status == "closed":
        # Maintenance closed → release vehicle (unless retired)
        if vehicle.status == "in_shop":
            vehicle.close_maintenance()
            vehicle.save(update_fields=["status"])
```

Connect the signal in `maintenance/apps.py`:
```python
class MaintenanceConfig(AppConfig):
    def ready(self):
        import maintenance.signals  # noqa
```

---

### Step 6 — Custom Exceptions

```python
# core/exceptions.py

class TransitOpsError(Exception):
    """Base exception for all TransitOps business logic errors."""

class CargoOverloadError(TransitOpsError):
    pass

class VehicleUnavailableError(TransitOpsError):
    pass

class DriverUnavailableError(TransitOpsError):
    pass

class LicenseExpiredError(TransitOpsError):
    pass
```

---

### Step 7 — View Integration Pattern

Views must call the guard, then the FSM method, then save — all inside a transaction:

```python
# trips/views.py
from django.db import transaction
from django_fsm import TransitionNotAllowed
from core.exceptions import TransitOpsError

@role_required(ROLE_FLEET_MANAGER, ROLE_DRIVER)
def dispatch_trip(request, pk):
    trip = get_object_or_404(Trip, pk=pk)
    try:
        with transaction.atomic():
            trip.dispatch()
            trip.save()
        messages.success(request, "Trip dispatched successfully.")
    except TransitOpsError as e:
        messages.error(request, str(e))
    except TransitionNotAllowed:
        messages.error(request, "This trip cannot be dispatched in its current state.")
    return redirect("trips:detail", pk=pk)
```

---

## Success Scenario

1. Fleet Manager dispatches a trip with cargo within limits → Vehicle and Driver both flip to `on_trip`.
2. Fleet Manager tries to dispatch the same vehicle again → `VehicleUnavailableError` raised, 0 status changes.
3. Driver completes the trip, inputs odometer and fuel → both flip to `available`, FuelLog auto-created.
4. Fleet Manager cancels a dispatched trip → both immediately flip to `available`.
5. Fleet Manager creates a MaintenanceLog for a vehicle → vehicle automatically flips to `in_shop`, hidden from dispatch.
6. Fleet Manager closes the MaintenanceLog → vehicle flips back to `available`.

---

## Definition of Done

- [ ] `status` fields on all three models use `FSMField` with `protected=True`.
- [ ] `Vehicle.send_to_shop()` is called by the maintenance signal — never directly from a view.
- [ ] `Trip.dispatch()` raises a typed `TransitOpsError` subclass for every guard failure.
- [ ] All dispatch, complete, and cancel transitions are wrapped in `transaction.atomic()` in views.
- [ ] `Retired` and `In Shop` vehicles are excluded from dispatch dropdowns via queryset filter, not FSM alone.
- [ ] End-to-end test: create trip → dispatch → complete → verify statuses and FuelLog record.

---

## AI Instructions

- Always call `vehicle.save(update_fields=["status"])` after an FSM transition — do not call `.save()` without specifying fields, as it overwrites the entire record.
- Never set `trip.status = "dispatched"` directly — always call the FSM method (`trip.dispatch()`).
- The `dispatch()` method on `Trip` must call `_guard_dispatch()` at the top — do not rely solely on the `conditions` kwarg in `@transition` for raising user-facing errors.
- Keep FSM side effects (updating related models) **inside** the transition method, not in the view — the view only calls the method and saves.
- Use `transaction.atomic()` in every view that calls an FSM transition to prevent partial state writes.
- Dispatch queryset filters for the UI: `Vehicle.objects.filter(status="available")` and `Driver.objects.filter(status="available", license_expiry__gte=date.today())`.
