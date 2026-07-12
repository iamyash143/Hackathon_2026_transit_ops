# Trip Management

## Goal

Implement the core dispatch workflow — creating, validating, dispatching, completing, and cancelling trips — with full FSM enforcement of all mandatory business rules. This is the most complex module and the integration point for Vehicle and Driver status.

## Scope

- `Trip` model with UUID identifier and FSM lifecycle: `Draft → Dispatched → Completed | Cancelled`
- Trip creation form: selects only `Available` vehicles and `eligible()` drivers
- FSM dispatch: validates cargo weight, locks vehicle and driver to `On Trip`
- FSM completion: updates vehicle odometer, generates `FuelLog`, restores both statuses to `Available`
- FSM cancellation: restores both statuses to `Available`
- List view with role-based filtering (Fleet Manager sees all; Driver sees own trips)
- Django Admin with trip lifecycle visibility

## Responsibilities

**Owner:** Dev E  
Consumes: `fleet.Vehicle`, `fleet.VehicleStatus`, `drivers.Driver`, `drivers.DriverStatus`  
Produces: writes to `finance.FuelLog` on trip completion (coordinate field names with Dev D)

## Django App

`trips`

```bash
python manage.py startapp trips
```

Register in `INSTALLED_APPS`: `'trips'`

## Files to Create / Modify

```
trips/
├── __init__.py
├── apps.py
├── models.py           # Trip model + FSM transitions + conditions
├── forms.py            # TripCreateForm, TripCompleteForm
├── views.py            # List, Detail, Create, Dispatch, Complete, Cancel
├── urls.py             # namespaced: app_name = 'trips'
├── admin.py
└── templates/
    └── trips/
        ├── trip_list.html
        ├── trip_detail.html
        ├── trip_form.html
        └── trip_complete_form.html

transitops/urls.py      # path('trips/', include('trips.urls', namespace='trips'))
```

## Dependencies

- `fleet` app: `Vehicle`, `VehicleStatus`, `Vehicle.dispatchable()` — **must be migrated**
- `drivers` app: `Driver`, `DriverStatus`, `Driver.eligible()` — **must be migrated**
- `finance` app: `FuelLog` — import only at trip completion to avoid circular import; use lazy import or `apps.get_model`
- Phase 1 complete

## Business Rules

- `Cargo Weight ≤ Vehicle.max_load_capacity` — validated in the FSM condition before dispatch
- Vehicle must be `Available` at the moment of dispatch
- Driver must be `Available` AND `license_expiry >= today` at the moment of dispatch
- `On Trip` vehicles and drivers are excluded from the creation form dropdowns
- Dispatching atomically sets both Vehicle and Driver to `On Trip`
- Completing requires: final odometer reading > vehicle's current odometer, and fuel consumed > 0
- Completing atomically: updates vehicle odometer, creates a `FuelLog`, restores both to `Available`
- Cancelling a `Dispatched` trip restores both Vehicle and Driver to `Available`
- A `Draft` trip can be deleted; `Dispatched` trips can only be Cancelled; `Completed` trips are immutable
- Trip status flows strictly forward — no reverting a completed trip

## Implementation Steps

### 1. Model

`trips/models.py`:

```python
import uuid
from django.db import models
from django.utils import timezone
from django_fsm import FSMField, transition, can_proceed
from fleet.models import Vehicle
from drivers.models import Driver

class TripStatus(models.TextChoices):
    DRAFT      = 'Draft',      'Draft'
    DISPATCHED = 'Dispatched', 'Dispatched'
    COMPLETED  = 'Completed',  'Completed'
    CANCELLED  = 'Cancelled',  'Cancelled'

class Trip(models.Model):
    trip_id         = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    vehicle         = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name='trips')
    driver          = models.ForeignKey(Driver,  on_delete=models.PROTECT, related_name='trips')
    source          = models.CharField(max_length=200)
    destination     = models.CharField(max_length=200)
    cargo_weight    = models.DecimalField(max_digits=8, decimal_places=2)     # kg
    planned_distance = models.DecimalField(max_digits=8, decimal_places=2)    # km
    start_time      = models.DateTimeField(null=True, blank=True)
    end_time        = models.DateTimeField(null=True, blank=True)
    final_odometer  = models.PositiveIntegerField(null=True, blank=True)      # km; set on completion
    fuel_consumed   = models.DecimalField(max_digits=8, decimal_places=2,
                                          null=True, blank=True)              # litres; set on completion
    status          = FSMField(default=TripStatus.DRAFT, protected=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Trip {str(self.trip_id)[:8]} — {self.source} → {self.destination}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('trips:trip_detail', kwargs={'pk': self.pk})

    # ── FSM conditions ───────────────────────────────────────────────────────

    def _cargo_within_capacity(self):
        return self.cargo_weight <= self.vehicle.max_load_capacity

    def _vehicle_available(self):
        from fleet.models import VehicleStatus
        return self.vehicle.status == VehicleStatus.AVAILABLE

    def _driver_eligible(self):
        from drivers.models import DriverStatus
        return (
            self.driver.status == DriverStatus.AVAILABLE
            and not self.driver.license_is_expired
        )

    # ── FSM transitions ──────────────────────────────────────────────────────

    @transition(
        field=status,
        source=TripStatus.DRAFT,
        target=TripStatus.DISPATCHED,
        conditions=[_cargo_within_capacity, _vehicle_available, _driver_eligible],
    )
    def dispatch(self):
        self.start_time = timezone.now()
        self.vehicle.dispatch()
        self.vehicle.save()
        self.driver.dispatch()
        self.driver.save()

    @transition(
        field=status,
        source=TripStatus.DISPATCHED,
        target=TripStatus.COMPLETED,
    )
    def complete(self):
        """
        Caller must set self.final_odometer and self.fuel_consumed before calling.
        Validation of those values happens in the view / form, not here.
        """
        from django.apps import apps
        self.end_time = timezone.now()

        # Update vehicle odometer
        self.vehicle.odometer = self.final_odometer
        self.vehicle.return_from_trip()
        self.vehicle.save()

        # Restore driver
        self.driver.return_from_trip()
        self.driver.save()

        # Create fuel log
        FuelLog = apps.get_model('finance', 'FuelLog')
        FuelLog.objects.create(
            vehicle=self.vehicle,
            trip=self,
            liters=self.fuel_consumed,
            cost=0,       # cost per litre can be added later or set in the form
            date=timezone.now().date(),
        )

    @transition(
        field=status,
        source=TripStatus.DISPATCHED,
        target=TripStatus.CANCELLED,
    )
    def cancel(self):
        self.vehicle.return_from_trip()
        self.vehicle.save()
        self.driver.return_from_trip()
        self.driver.save()
```

> **Atomic guarantee:** wrap `dispatch()`, `complete()`, and `cancel()` calls in `transaction.atomic()` in the view.

### 2. Forms

`trips/forms.py`:

```python
from django import forms
from django.utils import timezone
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit
from fleet.models import Vehicle
from drivers.models import Driver
from .models import Trip

class TripCreateForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = ['vehicle', 'driver', 'source', 'destination',
                  'cargo_weight', 'planned_distance']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show eligible assets in dropdowns
        self.fields['vehicle'].queryset = Vehicle.dispatchable()
        self.fields['driver'].queryset  = Driver.eligible()
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('vehicle', css_class='w-full md:w-1/2'),
                Column('driver',  css_class='w-full md:w-1/2'),
            ),
            Row(
                Column('source',      css_class='w-full md:w-1/2'),
                Column('destination', css_class='w-full md:w-1/2'),
            ),
            Row(
                Column('cargo_weight',    css_class='w-full md:w-1/2'),
                Column('planned_distance', css_class='w-full md:w-1/2'),
            ),
            Submit('submit', 'Save Draft',
                   css_class='text-white bg-blue-600 hover:bg-blue-700 font-medium rounded-lg text-sm px-5 py-2.5 mt-4'),
        )

class TripCompleteForm(forms.Form):
    final_odometer = forms.IntegerField(min_value=0, label='Final Odometer (km)')
    fuel_consumed  = forms.DecimalField(max_digits=8, decimal_places=2,
                                        min_value=0.1, label='Fuel Consumed (litres)')
    fuel_cost      = forms.DecimalField(max_digits=10, decimal_places=2,
                                        min_value=0, label='Fuel Cost (₹)')

    def __init__(self, *args, trip=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.trip = trip

    def clean_final_odometer(self):
        odometer = self.cleaned_data['final_odometer']
        if self.trip and odometer <= self.trip.vehicle.odometer:
            raise forms.ValidationError(
                f'Final odometer must be greater than current reading '
                f'({self.trip.vehicle.odometer} km).'
            )
        return odometer
```

### 3. Views

`trips/views.py`:

```python
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, DetailView, CreateView
from django_fsm import can_proceed, TransitionNotAllowed
from accounts.mixins import RoleRequiredMixin, OperationalMixin
from accounts.decorators import role_required
from .models import Trip, TripStatus
from .forms import TripCreateForm, TripCompleteForm

class TripListView(RoleRequiredMixin, ListView):
    allowed_roles = ['Fleet Manager', 'Driver', 'Safety Officer', 'Financial Analyst']
    model = Trip
    template_name = 'trips/trip_list.html'
    context_object_name = 'trips'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('vehicle', 'driver').order_by('-created_at')
        if self.request.user.role == 'Driver':
            # Drivers see only their own trips — match by linked driver record
            qs = qs.filter(driver__contact_number=self.request.user.email)
            # Note: if Driver.user OneToOne is added later, use driver__user
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs

class TripDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = ['Fleet Manager', 'Driver', 'Safety Officer', 'Financial Analyst']
    model = Trip
    template_name = 'trips/trip_detail.html'

class TripCreateView(OperationalMixin, CreateView):
    model = Trip
    form_class = TripCreateForm
    template_name = 'trips/trip_form.html'

@role_required('Fleet Manager', 'Driver')
def trip_dispatch(request, pk):
    trip = get_object_or_404(Trip, pk=pk)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                trip.dispatch()
                trip.save()
            messages.success(request, f'Trip dispatched — vehicle and driver are now On Trip.')
        except TransitionNotAllowed:
            messages.error(request, 'Dispatch failed: check cargo weight, vehicle, and driver availability.')
    return redirect('trips:trip_detail', pk=pk)

@role_required('Fleet Manager', 'Driver')
def trip_complete(request, pk):
    trip = get_object_or_404(Trip, pk=pk)
    form = TripCompleteForm(request.POST or None, trip=trip)
    if request.method == 'POST' and form.is_valid():
        trip.final_odometer = form.cleaned_data['final_odometer']
        trip.fuel_consumed  = form.cleaned_data['fuel_consumed']
        try:
            with transaction.atomic():
                trip.complete()
                trip.save()
            messages.success(request, 'Trip completed. Vehicle and driver are Available.')
            return redirect('trips:trip_detail', pk=pk)
        except TransitionNotAllowed:
            messages.error(request, 'Could not complete trip.')
    return render(request, 'trips/trip_complete_form.html', {'trip': trip, 'form': form})

@role_required('Fleet Manager')
def trip_cancel(request, pk):
    trip = get_object_or_404(Trip, pk=pk)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                trip.cancel()
                trip.save()
            messages.warning(request, 'Trip cancelled. Vehicle and driver restored to Available.')
        except TransitionNotAllowed:
            messages.error(request, 'Only dispatched trips can be cancelled.')
    return redirect('trips:trip_detail', pk=pk)
```

### 4. URLs

`trips/urls.py`:

```python
from django.urls import path
from . import views

app_name = 'trips'

urlpatterns = [
    path('', views.TripListView.as_view(), name='trip_list'),
    path('<int:pk>/', views.TripDetailView.as_view(), name='trip_detail'),
    path('new/', views.TripCreateView.as_view(), name='trip_create'),
    path('<int:pk>/dispatch/', views.trip_dispatch, name='trip_dispatch'),
    path('<int:pk>/complete/', views.trip_complete, name='trip_complete'),
    path('<int:pk>/cancel/', views.trip_cancel, name='trip_cancel'),
]
```

Register in `transitops/urls.py`:

```python
path('trips/', include('trips.urls', namespace='trips')),
```

### 5. Admin

`trips/admin.py`:

```python
from django.contrib import admin
from .models import Trip

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display  = ('trip_id', 'vehicle', 'driver', 'source', 'destination',
                     'cargo_weight', 'status', 'start_time', 'end_time')
    list_filter   = ('status',)
    search_fields = ('vehicle__registration_number', 'driver__name', 'source', 'destination')
    readonly_fields = ('trip_id', 'status', 'start_time', 'end_time', 'created_at', 'updated_at')
```

### 6. Templates (structure)

`trip_list.html` — Table with columns: Trip ID (short UUID), Source → Destination, Vehicle, Driver, Cargo, Status badge. Fleet Manager sees all; Driver sees own. Create button visible to Fleet Manager and Driver. Status filter with HTMX `hx-get`.

`trip_detail.html` — All trip fields. Action buttons rendered conditionally by status:
- `Draft`: Dispatch button (POST form), Delete button (Fleet Manager only)
- `Dispatched`: Complete button, Cancel button (Fleet Manager only)
- `Completed / Cancelled`: No action buttons — view only

`trip_form.html` — Create form. Note under vehicle/driver dropdowns: "Only available assets are shown."

`trip_complete_form.html` — Two fields: Final Odometer, Fuel Consumed. Current odometer shown as reference.

## Success Scenario

1. Fleet Manager creates trip: Van-05 + Alex, cargo 450 kg (capacity 500 kg) → saved as `Draft`
2. Fleet Manager clicks Dispatch → cargo check passes, Van-05 and Alex flip to `On Trip`
3. Trip list shows `Dispatched` — neither Van-05 nor Alex appear in a new trip's dropdowns
4. Driver enters final odometer and 40L fuel consumed → clicks Complete
5. Van-05 odometer updates; a `FuelLog` record is created; both flip to `Available`
6. Cancelling a dispatched trip restores both to `Available` immediately

## Definition of Done

- [ ] `Trip` model migrated with UUID `trip_id`, FKs to Vehicle and Driver, and FSM `status`
- [ ] FSM conditions block dispatch if cargo exceeds capacity, vehicle is unavailable, or driver is ineligible
- [ ] `dispatch()` sets both Vehicle and Driver to `On Trip` atomically
- [ ] `complete()` updates vehicle odometer, creates `FuelLog`, restores both to `Available` atomically
- [ ] `cancel()` restores both to `Available` atomically
- [ ] `TripCreateForm` dropdowns show only `Available` vehicles and eligible drivers
- [ ] `TripCompleteForm` rejects final odometer ≤ current vehicle odometer
- [ ] All state-changing views use `transaction.atomic()`
- [ ] `TransitionNotAllowed` is caught in every action view and shown as a user-facing error

## AI Instructions

- All three action views (`dispatch`, `complete`, `cancel`) must wrap the FSM call and `.save()` in `transaction.atomic()`. If the vehicle or driver `.save()` fails inside the FSM method, the trip status change must also roll back.
- Import `FuelLog` inside the `complete()` method body using `apps.get_model('finance', 'FuelLog')` to avoid a circular import at module load time.
- The `TripCreateForm` sets `queryset` in `__init__`, not as a class attribute — querysets set as class attributes are evaluated once at startup and become stale.
- The Driver filtering for the Driver role (`qs.filter(driver__contact_number=...)`) is a Phase 1 stub. If `Driver.user` (OneToOne to `accounts.User`) is added later, update to `driver__user=request.user`.
- `TransitionNotAllowed` is raised by `django-fsm` when a condition fails or the source state is wrong. Always catch it and show a meaningful error — never let it bubble up as a 500.
- `final_odometer` and `fuel_consumed` must be set on the `trip` instance **before** calling `trip.complete()` — the FSM method reads them from `self`.
- Do not add a `fuel_cost` field to `FuelLog` with a default of 0 permanently — the `TripCompleteForm` collects it and the `complete()` method should pass it through. Coordinate the exact `FuelLog` field names with Dev D before implementation.
