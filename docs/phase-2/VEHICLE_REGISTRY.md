# Vehicle Registry

## Goal

Provide a fully managed vehicle master list with status lifecycle enforcement. Vehicles are the central asset — their status gates dispatch, maintenance, and financial reporting across the entire platform.

## Scope

- `Vehicle` model with all required fields and FSM-managed status
- Full CRUD: list, detail, create, edit (no hard delete — use Retired status)
- Status transitions: `Available ↔ On Trip`, `Available ↔ In Shop`, `Available / In Shop → Retired`
- Django Admin with list filters and search
- RBAC: Fleet Manager has full CRUD; Driver and Safety Officer have read-only; Financial Analyst has read-only

## Responsibilities

**Owner:** Dev A  
Exposes: `Vehicle` model, `VehicleStatus` choices, status transition methods  
Consumed by: `trips` (dispatch), `maintenance` (In Shop lock), `finance` (cost aggregation)

## Django App

`fleet`

```bash
python manage.py startapp fleet
```

Register in `INSTALLED_APPS`: `'fleet'`

## Files to Create / Modify

```
fleet/
├── __init__.py
├── apps.py
├── models.py           # Vehicle model + FSM transitions
├── forms.py            # VehicleForm (crispy-tailwind)
├── views.py            # List, Detail, Create, Update views
├── urls.py             # namespaced: app_name = 'fleet'
├── admin.py
└── templates/
    └── fleet/
        ├── vehicle_list.html
        ├── vehicle_detail.html
        └── vehicle_form.html

transitops/urls.py      # path('vehicles/', include('fleet.urls', namespace='fleet'))
```

## Dependencies

- Phase 1 complete (`accounts.mixins`, `base.html`, Tailwind built)
- No other Phase 2 app

## Business Rules

- `registration_number` is unique across the entire system — enforce at DB and form level
- Status values are strictly: `Available`, `On Trip`, `In Shop`, `Retired`
- `Retired` and `In Shop` vehicles must never appear in dispatch querysets
- A vehicle `On Trip` cannot be dispatched again or sent to maintenance
- No hard deletes — retiring a vehicle is the terminal state
- `max_load_capacity` and `acquisition_cost` are `DecimalField` — never `FloatField`
- `odometer` is a `PositiveIntegerField`; it only ever increases

## Implementation Steps

### 1. Model

`fleet/models.py`:

```python
from django.db import models
from django_fsm import FSMField, transition

class VehicleStatus(models.TextChoices):
    AVAILABLE = 'Available', 'Available'
    ON_TRIP   = 'On Trip',   'On Trip'
    IN_SHOP   = 'In Shop',   'In Shop'
    RETIRED   = 'Retired',   'Retired'

class Vehicle(models.Model):
    registration_number = models.CharField(max_length=20, unique=True, db_index=True)
    name                = models.CharField(max_length=100)
    vehicle_type        = models.CharField(max_length=50)
    max_load_capacity   = models.DecimalField(max_digits=8, decimal_places=2)  # kg
    odometer            = models.PositiveIntegerField(default=0)               # km
    acquisition_cost    = models.DecimalField(max_digits=12, decimal_places=2)
    status              = FSMField(default=VehicleStatus.AVAILABLE, protected=True)
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.registration_number} — {self.name}"

    # ── FSM transitions ──────────────────────────────────────────────────────

    @transition(field=status,
                source=VehicleStatus.AVAILABLE,
                target=VehicleStatus.ON_TRIP)
    def dispatch(self):
        """Called by Trip FSM on dispatch. Do not call directly from views."""
        pass

    @transition(field=status,
                source=VehicleStatus.ON_TRIP,
                target=VehicleStatus.AVAILABLE)
    def return_from_trip(self):
        pass

    @transition(field=status,
                source=VehicleStatus.AVAILABLE,
                target=VehicleStatus.IN_SHOP)
    def send_to_maintenance(self):
        pass

    @transition(field=status,
                source=VehicleStatus.IN_SHOP,
                target=VehicleStatus.AVAILABLE)
    def complete_maintenance(self):
        pass

    @transition(field=status,
                source=[VehicleStatus.AVAILABLE, VehicleStatus.IN_SHOP],
                target=VehicleStatus.RETIRED)
    def retire(self):
        pass

    # ── Querysets ────────────────────────────────────────────────────────────

    @classmethod
    def dispatchable(cls):
        """Vehicles eligible for trip assignment."""
        return cls.objects.filter(status=VehicleStatus.AVAILABLE)
```

### 2. Form

`fleet/forms.py`:

```python
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit
from .models import Vehicle

class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = [
            'registration_number', 'name', 'vehicle_type',
            'max_load_capacity', 'odometer', 'acquisition_cost',
        ]
        # status is excluded — changed only via FSM transitions

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('registration_number', css_class='w-full md:w-1/2'),
                Column('name', css_class='w-full md:w-1/2'),
            ),
            Row(
                Column('vehicle_type', css_class='w-full md:w-1/3'),
                Column('max_load_capacity', css_class='w-full md:w-1/3'),
                Column('acquisition_cost', css_class='w-full md:w-1/3'),
            ),
            'odometer',
            Submit('submit', 'Save Vehicle',
                   css_class='text-white bg-blue-600 hover:bg-blue-700 font-medium rounded-lg text-sm px-5 py-2.5 mt-4'),
        )
```

### 3. Views

`fleet/views.py`:

```python
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from accounts.mixins import FleetManagerMixin, RoleRequiredMixin
from .models import Vehicle, VehicleStatus
from .forms import VehicleForm

class VehicleListView(RoleRequiredMixin, ListView):
    allowed_roles = ['Fleet Manager', 'Driver', 'Safety Officer', 'Financial Analyst']
    model = Vehicle
    template_name = 'fleet/vehicle_list.html'
    context_object_name = 'vehicles'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().order_by('registration_number')
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(registration_number__icontains=q) | \
                 qs.filter(name__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['status_choices'] = VehicleStatus.choices
        return ctx

class VehicleDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = ['Fleet Manager', 'Driver', 'Safety Officer', 'Financial Analyst']
    model = Vehicle
    template_name = 'fleet/vehicle_detail.html'

class VehicleCreateView(FleetManagerMixin, CreateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = 'fleet/vehicle_form.html'

    def get_success_url(self):
        return self.object.get_absolute_url()

class VehicleUpdateView(FleetManagerMixin, UpdateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = 'fleet/vehicle_form.html'

    def get_success_url(self):
        return self.object.get_absolute_url()

from django.urls import reverse_lazy

def vehicle_retire(request, pk):
    """POST-only action. Fleet Manager only."""
    from accounts.decorators import fleet_manager_required
    # applied via url conf — see urls.py
    vehicle = get_object_or_404(Vehicle, pk=pk)
    if request.method == 'POST':
        vehicle.retire()
        vehicle.save()
        messages.success(request, f'{vehicle} has been retired.')
    return redirect('fleet:vehicle_list')
```

Add `get_absolute_url` to the model:

```python
from django.urls import reverse

def get_absolute_url(self):
    return reverse('fleet:vehicle_detail', kwargs={'pk': self.pk})
```

### 4. URLs

`fleet/urls.py`:

```python
from django.urls import path
from accounts.decorators import fleet_manager_required
from . import views

app_name = 'fleet'

urlpatterns = [
    path('', views.VehicleListView.as_view(), name='vehicle_list'),
    path('<int:pk>/', views.VehicleDetailView.as_view(), name='vehicle_detail'),
    path('new/', views.VehicleCreateView.as_view(), name='vehicle_create'),
    path('<int:pk>/edit/', views.VehicleUpdateView.as_view(), name='vehicle_update'),
    path('<int:pk>/retire/', fleet_manager_required(views.vehicle_retire), name='vehicle_retire'),
]
```

Register in `transitops/urls.py`:

```python
path('vehicles/', include('fleet.urls', namespace='fleet')),
```

### 5. Admin

`fleet/admin.py`:

```python
from django.contrib import admin
from .models import Vehicle

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display  = ('registration_number', 'name', 'vehicle_type', 'status', 'odometer', 'acquisition_cost')
    list_filter   = ('status', 'vehicle_type')
    search_fields = ('registration_number', 'name')
    readonly_fields = ('status', 'created_at', 'updated_at')
```

`status` is `readonly` in admin — it must only change via FSM methods.

### 6. Templates (structure)

`vehicle_list.html` — extends `base.html`. Flowbite datatable with status badge pills, search input (HTMX `hx-get` on keyup), status filter dropdown. Fleet Manager sees Create and Edit buttons; other roles see no action buttons.

`vehicle_detail.html` — extends `base.html`. All fields displayed. Fleet Manager sees Edit and Retire buttons. Retire button is a `<form method="post">` pointing to `fleet:vehicle_retire`.

`vehicle_form.html` — extends `base.html`. Renders `{{ form|crispy }}`.

## Success Scenario

1. Fleet Manager creates `Van-05` with max capacity 500 kg → status defaults to `Available`
2. Fleet Manager views the vehicle list filtered by `Available` — `Van-05` appears
3. Fleet Manager cannot manually change the status field from the edit form
4. Retiring `Van-05` via the Retire button changes status to `Retired`
5. Driver visits vehicle list — sees all vehicles but no Create / Edit / Retire buttons

## Definition of Done

- [ ] `Vehicle` model migrated; `registration_number` has a unique DB constraint
- [ ] All five FSM transitions defined and `protected=True` on the status field
- [ ] `Vehicle.dispatchable()` returns only `Available` vehicles
- [ ] Fleet Manager can create and edit vehicles; status field is not in the form
- [ ] Non-Fleet Manager roles can view the list and detail but see no mutation buttons
- [ ] Retire action only accepts `POST`; direct `GET` to the URL redirects safely
- [ ] Django Admin shows status as read-only
- [ ] `get_absolute_url` resolves correctly

## AI Instructions

- `status` must use `FSMField` with `protected=True`. This prevents any code from assigning `vehicle.status = 'On Trip'` directly — it will raise `TransitionNotAllowed`. Only decorated `@transition` methods may change it.
- Never expose status in `VehicleForm.fields` — status changes are side effects of FSM transitions triggered by other modules.
- `Vehicle.dispatchable()` is the single source of truth for trip dispatch filtering. The `trips` app must call this queryset, not filter by status string directly.
- `max_load_capacity` and `acquisition_cost` must be `DecimalField` — `FloatField` causes rounding errors in financial calculations.
- Do not implement hard delete. The retire transition is the permanent end state.
- The `dispatch()` and `return_from_trip()` FSM methods are called by the `trips` app's Trip FSM — not by Fleet Manager UI actions. Do not wire them to any button in the vehicle views.
- `send_to_maintenance()` is called by the `maintenance` app's signal — not by the vehicle views either.
