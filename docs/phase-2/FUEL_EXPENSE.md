# Fuel & Expense Management

## Goal

Track all variable operational costs — fuel consumption and ancillary expenses — per vehicle and per trip. Provide aggregated cost totals that power the Financial Analyst's ROI and efficiency reports.

## Scope

- `FuelLog` model: per-vehicle, optionally per-trip fuel records
- `ExpenseLog` model: tolls, fines, parking, and other ancillary costs
- Manual create views for both (Trip completion auto-creates FuelLog via the `trips` app)
- Per-vehicle cost aggregation properties used by dashboard and reports
- Django Admin with inline editing
- RBAC: Financial Analyst has full CRUD on both models; Fleet Manager has read access; Driver has create access for expenses on their active trip; Safety Officer has read access

## Responsibilities

**Owner:** Dev D  
Consumes: `fleet.Vehicle`, `trips.Trip`  
Produces: `FuelLog` (auto-created by `trips.Trip.complete()`), `ExpenseLog`; cost aggregates consumed by Phase 3 dashboard and Phase 5 reports  
**Coordinate with Dev E (trips):** confirm `FuelLog` field names before Trip completion is implemented

## Django App

`finance`

```bash
python manage.py startapp finance
```

Register in `INSTALLED_APPS`: `'finance'`

## Files to Create / Modify

```
finance/
├── __init__.py
├── apps.py
├── models.py           # FuelLog, ExpenseLog models + cost aggregation helpers
├── forms.py            # FuelLogForm, ExpenseLogForm
├── views.py            # List and Create views for both models
├── urls.py             # namespaced: app_name = 'finance'
├── admin.py
└── templates/
    └── finance/
        ├── fuel_log_list.html
        ├── fuel_log_form.html
        ├── expense_log_list.html
        └── expense_log_form.html

transitops/urls.py      # path('finance/', include('finance.urls', namespace='finance'))
```

## Dependencies

- `fleet` app: `Vehicle` — must be migrated
- `trips` app: `Trip` — must be migrated (FuelLog has an optional FK to Trip)
- Phase 1 complete
- `trips.Trip.complete()` will call `FuelLog.objects.create(...)` — field names here must be finalised before Dev E implements trip completion

## Business Rules

- `FuelLog` is created automatically by `Trip.complete()` — manual creation is also permitted for fuel-ups outside of trips
- `FuelLog.trip` is optional (`null=True`, `blank=True`) — fuel logs may exist without a trip
- `ExpenseLog` always links to both a `Vehicle` and optionally a `Trip`
- All cost fields are `DecimalField` — never `FloatField`
- Aggregated `total_operational_cost` per vehicle = sum of all `FuelLog.cost` + sum of all `MaintenanceLog.cost`
- `MaintenanceLog` cost is read from the `maintenance` app via ORM — no data duplication
- `fuel_efficiency` per trip = `planned_distance / fuel_consumed` (km/L); averaged across all completed trips for fleet-level metric
- Financial Analyst has full CRUD; Drivers can create expense logs only on their active trip

## Implementation Steps

### 1. Models

`finance/models.py`:

```python
from django.db import models
from fleet.models import Vehicle

class ExpenseType(models.TextChoices):
    TOLL        = 'Toll',        'Toll'
    FINE        = 'Fine',        'Fine'
    PARKING     = 'Parking',     'Parking'
    REPAIR      = 'Repair',      'Repair'
    OTHER       = 'Other',       'Other'

class FuelLog(models.Model):
    vehicle    = models.ForeignKey(Vehicle, on_delete=models.PROTECT,
                                   related_name='fuel_logs')
    trip       = models.ForeignKey('trips.Trip', on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name='fuel_logs')
    liters     = models.DecimalField(max_digits=8, decimal_places=2)
    cost       = models.DecimalField(max_digits=10, decimal_places=2)
    date       = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Fuel {self.liters}L — {self.vehicle} — {self.date}"

class ExpenseLog(models.Model):
    vehicle      = models.ForeignKey(Vehicle, on_delete=models.PROTECT,
                                     related_name='expense_logs')
    trip         = models.ForeignKey('trips.Trip', on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='expense_logs')
    expense_type = models.CharField(max_length=20, choices=ExpenseType.choices)
    amount       = models.DecimalField(max_digits=10, decimal_places=2)
    date         = models.DateField()
    notes        = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.expense_type} ₹{self.amount} — {self.vehicle} — {self.date}"
```

### 2. Cost Aggregation Helpers

Add these as model managers or standalone functions in `finance/models.py`. They are called by the Phase 3 dashboard and Phase 5 reports.

```python
from django.db.models import Sum, Avg, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal

def vehicle_fuel_cost(vehicle):
    return FuelLog.objects.filter(vehicle=vehicle).aggregate(
        total=Coalesce(Sum('cost'), Decimal('0'), output_field=DecimalField())
    )['total']

def vehicle_maintenance_cost(vehicle):
    from maintenance.models import MaintenanceLog, MaintenanceStatus
    return MaintenanceLog.objects.filter(
        vehicle=vehicle, status=MaintenanceStatus.CLOSED
    ).aggregate(
        total=Coalesce(Sum('cost'), Decimal('0'), output_field=DecimalField())
    )['total']

def vehicle_total_operational_cost(vehicle):
    return vehicle_fuel_cost(vehicle) + vehicle_maintenance_cost(vehicle)

def vehicle_roi(vehicle, revenue=Decimal('0')):
    """
    ROI = (Revenue - (Maintenance Costs + Fuel Costs)) / Acquisition Cost
    Revenue is passed in — not stored in the system yet (Phase 5 extension).
    """
    if vehicle.acquisition_cost == 0:
        return Decimal('0')
    total_cost = vehicle_total_operational_cost(vehicle)
    return (revenue - total_cost) / vehicle.acquisition_cost

def fleet_fuel_efficiency():
    """
    Average fuel efficiency across all completed trips (km/L).
    Returns queryset of dicts with trip_id and efficiency.
    """
    from trips.models import Trip, TripStatus
    from django.db.models import F, ExpressionWrapper
    return (
        Trip.objects
        .filter(status=TripStatus.COMPLETED, fuel_consumed__gt=0)
        .annotate(efficiency=ExpressionWrapper(
            F('planned_distance') / F('fuel_consumed'),
            output_field=DecimalField(max_digits=8, decimal_places=2)
        ))
        .values('id', 'vehicle__registration_number', 'efficiency')
    )
```

### 3. Forms

`finance/forms.py`:

```python
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit
from fleet.models import Vehicle
from .models import FuelLog, ExpenseLog

class FuelLogForm(forms.ModelForm):
    class Meta:
        model = FuelLog
        fields = ['vehicle', 'trip', 'liters', 'cost', 'date']
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['trip'].required = False
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('vehicle', css_class='w-full md:w-1/2'),
                Column('trip',    css_class='w-full md:w-1/2'),
            ),
            Row(
                Column('liters', css_class='w-full md:w-1/3'),
                Column('cost',   css_class='w-full md:w-1/3'),
                Column('date',   css_class='w-full md:w-1/3'),
            ),
            Submit('submit', 'Add Fuel Log',
                   css_class='text-white bg-blue-600 hover:bg-blue-700 font-medium rounded-lg text-sm px-5 py-2.5 mt-4'),
        )

class ExpenseLogForm(forms.ModelForm):
    class Meta:
        model = ExpenseLog
        fields = ['vehicle', 'trip', 'expense_type', 'amount', 'date', 'notes']
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['trip'].required = False
        self.fields['notes'].required = False
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('vehicle',      css_class='w-full md:w-1/2'),
                Column('trip',         css_class='w-full md:w-1/2'),
            ),
            Row(
                Column('expense_type', css_class='w-full md:w-1/3'),
                Column('amount',       css_class='w-full md:w-1/3'),
                Column('date',         css_class='w-full md:w-1/3'),
            ),
            'notes',
            Submit('submit', 'Add Expense',
                   css_class='text-white bg-blue-600 hover:bg-blue-700 font-medium rounded-lg text-sm px-5 py-2.5 mt-4'),
        )
```

### 4. Views

`finance/views.py`:

```python
from django.views.generic import ListView, CreateView
from accounts.mixins import RoleRequiredMixin, FinancialAnalystMixin
from .models import FuelLog, ExpenseLog
from .forms import FuelLogForm, ExpenseLogForm

class FuelLogListView(RoleRequiredMixin, ListView):
    allowed_roles = ['Fleet Manager', 'Financial Analyst', 'Safety Officer']
    model = FuelLog
    template_name = 'finance/fuel_log_list.html'
    context_object_name = 'fuel_logs'
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related('vehicle', 'trip').order_by('-date')
        vehicle_id = self.request.GET.get('vehicle')
        if vehicle_id:
            qs = qs.filter(vehicle_id=vehicle_id)
        return qs

class FuelLogCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = ['Fleet Manager', 'Financial Analyst']
    model = FuelLog
    form_class = FuelLogForm
    template_name = 'finance/fuel_log_form.html'

    def get_success_url(self):
        from django.urls import reverse
        return reverse('finance:fuel_log_list')

class ExpenseLogListView(RoleRequiredMixin, ListView):
    allowed_roles = ['Fleet Manager', 'Financial Analyst', 'Safety Officer']
    model = ExpenseLog
    template_name = 'finance/expense_log_list.html'
    context_object_name = 'expense_logs'
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related('vehicle', 'trip').order_by('-date')
        vehicle_id = self.request.GET.get('vehicle')
        if vehicle_id:
            qs = qs.filter(vehicle_id=vehicle_id)
        expense_type = self.request.GET.get('expense_type')
        if expense_type:
            qs = qs.filter(expense_type=expense_type)
        return qs

class ExpenseLogCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = ['Fleet Manager', 'Financial Analyst', 'Driver']
    model = ExpenseLog
    form_class = ExpenseLogForm
    template_name = 'finance/expense_log_form.html'

    def get_success_url(self):
        from django.urls import reverse
        return reverse('finance:expense_log_list')
```

### 5. URLs

`finance/urls.py`:

```python
from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('fuel/',          views.FuelLogListView.as_view(),    name='fuel_log_list'),
    path('fuel/new/',      views.FuelLogCreateView.as_view(),  name='fuel_log_create'),
    path('expenses/',      views.ExpenseLogListView.as_view(), name='expense_log_list'),
    path('expenses/new/',  views.ExpenseLogCreateView.as_view(), name='expense_log_create'),
]
```

Register in `transitops/urls.py`:

```python
path('finance/', include('finance.urls', namespace='finance')),
```

### 6. Admin

`finance/admin.py`:

```python
from django.contrib import admin
from .models import FuelLog, ExpenseLog

@admin.register(FuelLog)
class FuelLogAdmin(admin.ModelAdmin):
    list_display  = ('vehicle', 'trip', 'liters', 'cost', 'date')
    list_filter   = ('vehicle', 'date')
    search_fields = ('vehicle__registration_number',)
    readonly_fields = ('created_at',)

@admin.register(ExpenseLog)
class ExpenseLogAdmin(admin.ModelAdmin):
    list_display  = ('vehicle', 'trip', 'expense_type', 'amount', 'date')
    list_filter   = ('expense_type', 'vehicle')
    search_fields = ('vehicle__registration_number', 'notes')
    readonly_fields = ('created_at',)
```

### 7. Templates (structure)

`fuel_log_list.html` — Table: Vehicle, Trip ID (short UUID or "—"), Litres, Cost, Date. Vehicle filter dropdown. Total cost summed below the table using Django template `{% for %}` + manual sum, or pass it from the view via `get_context_data`.

`expense_log_list.html` — Table: Vehicle, Trip, Type badge, Amount, Date, Notes. Expense type filter. Financial Analyst sees Create button; Drivers see Create button on their trip's detail page only.

`fuel_log_form.html` and `expense_log_form.html` — `{{ form|crispy }}`.

## Success Scenario

1. Fleet Manager manually adds a fuel log: Van-05, 40L, ₹3,200 → appears in fuel log list
2. Trip completion auto-creates a FuelLog via `Trip.complete()` — same list, linked to trip
3. Driver adds a toll expense of ₹150 against Van-05
4. Financial Analyst views fuel log list filtered by Van-05 — sees both manual and auto logs
5. `vehicle_total_operational_cost(van05)` returns sum of all fuel + maintenance costs
6. Phase 3 dashboard reads this function and displays it in the KPI panel

## Definition of Done

- [ ] `FuelLog` and `ExpenseLog` models migrated with correct FK references
- [ ] All cost fields are `DecimalField`
- [ ] `FuelLog.trip` is nullable — manual fuel logs without a trip are valid
- [ ] `vehicle_fuel_cost()`, `vehicle_maintenance_cost()`, `vehicle_total_operational_cost()`, `vehicle_roi()` functions exist and return `Decimal` values
- [ ] `fleet_fuel_efficiency()` returns a queryset of completed trips annotated with efficiency
- [ ] Financial Analyst has full CRUD; Fleet Manager has list + create access; Driver has create access for expenses only
- [ ] Django Admin shows both models with correct filters
- [ ] Field names (`liters`, `cost`, `date`, `trip`, `vehicle`) confirmed with Dev E before Trip completion is implemented

## AI Instructions

- Import `maintenance.models.MaintenanceLog` inside `vehicle_maintenance_cost()` at call time, not at module top level — otherwise a circular import occurs at Django startup if `maintenance` imports `finance`.
- `FuelLog.trip` uses `on_delete=models.SET_NULL` — if a trip is deleted (admin action), fuel logs persist with `trip=None`. Never use `CASCADE` here.
- `vehicle_roi()` accepts `revenue` as a parameter because the system has no Revenue model yet. Pass `Decimal('0')` as default. Phase 5 may add a Revenue model — update the signature then.
- The `fleet_fuel_efficiency()` function uses `planned_distance` as the numerator, not `final_odometer - start_odometer`. This matches the spec formula. If actual distance (odometer delta) is preferred, add it as a separate annotation.
- All aggregation helpers return `Decimal('0')` on empty querysets via `Coalesce` — never `None`. The Phase 3 dashboard will break on template arithmetic with `None`.
- `ExpenseLogCreateView` allows Drivers — but restrict via template to show the create button only on an active trip's detail page. The view-level permission allows the role; the UX constraint is in the template.
- `FuelLog` records created by `Trip.complete()` will have `cost=0` if Dev E doesn't pass a fuel cost. Confirm with Dev E that `TripCompleteForm` collects `fuel_cost` and passes it to `FuelLog.objects.create(cost=fuel_cost, ...)`.
