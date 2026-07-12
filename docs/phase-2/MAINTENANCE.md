# Maintenance

## Goal

Allow Fleet Managers to log maintenance work against vehicles. Creating an active maintenance record automatically locks the vehicle out of dispatch. Closing the record restores it to Available (unless retired).

## Scope

- `MaintenanceLog` model linked to `Vehicle`
- Create and close maintenance records
- `post_save` signal on `MaintenanceLog` that calls `vehicle.send_to_maintenance()` on creation
- Closing a log calls `vehicle.complete_maintenance()` or marks it retired
- List view filtered by vehicle and open/closed status
- Dashboard-visible predictive alerts: threshold-based "Maintenance Due" warnings
- Django Admin integration

## Responsibilities

**Owner:** Dev C  
Consumes: `fleet.Vehicle`, `fleet.VehicleStatus`  
Produces: vehicle status side effects via FSM; operational cost data consumed by `finance`

## Django App

`maintenance`

```bash
python manage.py startapp maintenance
```

Register in `INSTALLED_APPS`: `'maintenance'`

## Files to Create / Modify

```
maintenance/
├── __init__.py
├── apps.py
├── models.py           # MaintenanceLog model + signals
├── forms.py            # MaintenanceCreateForm, MaintenanceCloseForm
├── views.py            # List, Detail, Create, Close action
├── urls.py             # namespaced: app_name = 'maintenance'
├── admin.py
└── templates/
    └── maintenance/
        ├── maintenance_list.html
        ├── maintenance_detail.html
        └── maintenance_form.html

transitops/urls.py      # path('maintenance/', include('maintenance.urls', namespace='maintenance'))
```

## Dependencies

- `fleet` app: `Vehicle`, `VehicleStatus` — must be migrated
- No dependency on `trips`, `drivers`, or `finance`
- Phase 1 complete

## Business Rules

- Creating a `MaintenanceLog` with `status='Open'` immediately sets the linked vehicle to `In Shop`
- A vehicle `On Trip` cannot have a maintenance record opened against it — validate at form level
- Closing a log (`status='Closed'`) calls `vehicle.complete_maintenance()` → vehicle returns to `Available`
- If the Fleet Manager also checks "Retire vehicle on close", call `vehicle.retire()` instead
- A vehicle can only have one `Open` maintenance log at a time
- Maintenance cost is captured as a `DecimalField` on the log itself
- `MaintenanceLog` records are never deleted — they form the operational cost history

## Implementation Steps

### 1. Model

`maintenance/models.py`:

```python
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from fleet.models import Vehicle, VehicleStatus

class MaintenanceStatus(models.TextChoices):
    OPEN   = 'Open',   'Open'
    CLOSED = 'Closed', 'Closed'

class MaintenanceLog(models.Model):
    vehicle     = models.ForeignKey(Vehicle, on_delete=models.PROTECT,
                                    related_name='maintenance_logs')
    date        = models.DateField()
    description = models.TextField()
    cost        = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status      = models.CharField(max_length=10,
                                   choices=MaintenanceStatus.choices,
                                   default=MaintenanceStatus.OPEN)
    retire_on_close = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Maintenance [{self.status}] — {self.vehicle} — {self.date}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('maintenance:maintenance_detail', kwargs={'pk': self.pk})

# ── Signals ──────────────────────────────────────────────────────────────────

@receiver(post_save, sender=MaintenanceLog)
def handle_maintenance_status_change(sender, instance, created, **kwargs):
    vehicle = instance.vehicle

    if created and instance.status == MaintenanceStatus.OPEN:
        # New open log → lock vehicle
        if vehicle.status == VehicleStatus.AVAILABLE:
            vehicle.send_to_maintenance()
            vehicle.save()

    elif not created and instance.status == MaintenanceStatus.CLOSED:
        # Log closed → restore or retire vehicle
        if vehicle.status == VehicleStatus.IN_SHOP:
            if instance.retire_on_close:
                vehicle.retire()
            else:
                vehicle.complete_maintenance()
            vehicle.save()
```

Connect the signal in `maintenance/apps.py`:

```python
from django.apps import AppConfig

class MaintenanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'maintenance'

    def ready(self):
        import maintenance.models  # registers @receiver decorators
```

### 2. Forms

`maintenance/forms.py`:

```python
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit
from fleet.models import Vehicle, VehicleStatus
from .models import MaintenanceLog

class MaintenanceCreateForm(forms.ModelForm):
    class Meta:
        model = MaintenanceLog
        fields = ['vehicle', 'date', 'description', 'cost']
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only available vehicles can be sent to maintenance
        self.fields['vehicle'].queryset = Vehicle.objects.filter(
            status=VehicleStatus.AVAILABLE
        )
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('vehicle', css_class='w-full md:w-1/2'),
                Column('date',    css_class='w-full md:w-1/2'),
            ),
            'description',
            'cost',
            Submit('submit', 'Open Maintenance Record',
                   css_class='text-white bg-yellow-500 hover:bg-yellow-600 font-medium rounded-lg text-sm px-5 py-2.5 mt-4'),
        )

    def clean_vehicle(self):
        vehicle = self.cleaned_data['vehicle']
        open_log_exists = MaintenanceLog.objects.filter(
            vehicle=vehicle, status='Open'
        ).exists()
        if open_log_exists:
            raise forms.ValidationError(
                f'{vehicle} already has an open maintenance record.'
            )
        return vehicle

class MaintenanceCloseForm(forms.Form):
    final_cost      = forms.DecimalField(max_digits=10, decimal_places=2,
                                         min_value=0, label='Final Cost (₹)')
    retire_on_close = forms.BooleanField(required=False, label='Retire vehicle after closing')
```

### 3. Views

`maintenance/views.py`:

```python
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, DetailView, CreateView
from accounts.mixins import FleetManagerMixin, RoleRequiredMixin
from accounts.decorators import fleet_manager_required
from .models import MaintenanceLog, MaintenanceStatus
from .forms import MaintenanceCreateForm, MaintenanceCloseForm

class MaintenanceListView(RoleRequiredMixin, ListView):
    allowed_roles = ['Fleet Manager', 'Safety Officer', 'Financial Analyst']
    model = MaintenanceLog
    template_name = 'maintenance/maintenance_list.html'
    context_object_name = 'logs'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('vehicle').order_by('-created_at')
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        vehicle_id = self.request.GET.get('vehicle')
        if vehicle_id:
            qs = qs.filter(vehicle_id=vehicle_id)
        return qs

class MaintenanceDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = ['Fleet Manager', 'Safety Officer', 'Financial Analyst']
    model = MaintenanceLog
    template_name = 'maintenance/maintenance_detail.html'

class MaintenanceCreateView(FleetManagerMixin, CreateView):
    model = MaintenanceLog
    form_class = MaintenanceCreateForm
    template_name = 'maintenance/maintenance_form.html'

@fleet_manager_required
def maintenance_close(request, pk):
    log = get_object_or_404(MaintenanceLog, pk=pk)
    if log.status == MaintenanceStatus.CLOSED:
        messages.warning(request, 'This maintenance record is already closed.')
        return redirect('maintenance:maintenance_detail', pk=pk)

    form = MaintenanceCloseForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            log.cost           = form.cleaned_data['final_cost']
            log.retire_on_close = form.cleaned_data['retire_on_close']
            log.status         = MaintenanceStatus.CLOSED
            log.save()          # post_save signal handles vehicle FSM
        messages.success(request, 'Maintenance record closed.')
        return redirect('maintenance:maintenance_detail', pk=pk)

    return render(request, 'maintenance/maintenance_close_form.html',
                  {'log': log, 'form': form})
```

### 4. Predictive Maintenance Alert (post_save on Trip)

Add a `post_save` signal on `Trip` completion to check odometer thresholds. Place this in `maintenance/models.py` to keep the logic in the maintenance app:

```python
from django.db.models.signals import post_save
from django.dispatch import receiver

ODOMETER_SERVICE_INTERVAL = 15000  # km between oil changes

@receiver(post_save, sender='trips.Trip')
def check_maintenance_threshold(sender, instance, **kwargs):
    """Flag vehicles that have exceeded the service interval since last maintenance."""
    from trips.models import TripStatus
    if instance.status != TripStatus.COMPLETED:
        return

    vehicle = instance.vehicle
    last_closed = MaintenanceLog.objects.filter(
        vehicle=vehicle, status=MaintenanceStatus.CLOSED
    ).order_by('-updated_at').first()

    last_service_odometer = last_closed.vehicle.odometer if last_closed else 0
    if vehicle.odometer - last_service_odometer >= ODOMETER_SERVICE_INTERVAL:
        vehicle.maintenance_due = True   # requires a BooleanField on Vehicle — coordinate with Dev A
        vehicle.save(update_fields=['maintenance_due'])
```

> **Coordinate with Dev A:** add `maintenance_due = models.BooleanField(default=False)` to `Vehicle` and include it in the migration. The dashboard (Phase 3) reads this flag.

### 5. URLs

`maintenance/urls.py`:

```python
from django.urls import path
from . import views

app_name = 'maintenance'

urlpatterns = [
    path('', views.MaintenanceListView.as_view(), name='maintenance_list'),
    path('<int:pk>/', views.MaintenanceDetailView.as_view(), name='maintenance_detail'),
    path('new/', views.MaintenanceCreateView.as_view(), name='maintenance_create'),
    path('<int:pk>/close/', views.maintenance_close, name='maintenance_close'),
]
```

Register in `transitops/urls.py`:

```python
path('maintenance/', include('maintenance.urls', namespace='maintenance')),
```

### 6. Admin

`maintenance/admin.py`:

```python
from django.contrib import admin
from .models import MaintenanceLog

@admin.register(MaintenanceLog)
class MaintenanceLogAdmin(admin.ModelAdmin):
    list_display  = ('vehicle', 'date', 'description', 'cost', 'status', 'retire_on_close')
    list_filter   = ('status',)
    search_fields = ('vehicle__registration_number', 'description')
    readonly_fields = ('created_at', 'updated_at')
```

### 7. Templates (structure)

`maintenance_list.html` — Table: Vehicle, Date, Description, Cost, Status badge. Filter by vehicle and status. Fleet Manager sees Create button.

`maintenance_detail.html` — All fields. If status is `Open`, Fleet Manager sees Close button (POST form). If status is `Closed`, show final cost and retired flag read-only.

`maintenance_close_form.html` — Two fields: Final Cost, Retire Vehicle checkbox. Warn the user that closing will change the vehicle status.

## Success Scenario

1. Fleet Manager creates a maintenance record for Van-05 → Van-05 status flips to `In Shop`
2. Van-05 disappears from `Vehicle.dispatchable()` — cannot be selected in trip creation
3. Fleet Manager closes the record with final cost ₹5,000 → Van-05 flips back to `Available`
4. Fleet Manager closes with "Retire vehicle" checked → Van-05 flips to `Retired`
5. After trip completion, if Van-05 odometer crosses 15,000 km since last service, `maintenance_due` is flagged

## Definition of Done

- [ ] `MaintenanceLog` model migrated with FK to `Vehicle`
- [ ] `post_save` signal automatically calls `vehicle.send_to_maintenance()` on new Open log
- [ ] `post_save` signal calls `vehicle.complete_maintenance()` or `vehicle.retire()` on Close
- [ ] Form prevents opening a second log on a vehicle that already has an Open record
- [ ] Form only shows `Available` vehicles in the vehicle dropdown
- [ ] Closing a log correctly handles the `retire_on_close` flag
- [ ] `check_maintenance_threshold` signal fires after trip completion and sets `maintenance_due`
- [ ] Fleet Manager can perform all actions; Safety Officer and Financial Analyst have read-only access

## AI Instructions

- The `post_save` signal must check `created` to distinguish between a new record (lock vehicle) and an update (unlock vehicle). Without this check, every save — including intermediate cost updates — will attempt to call FSM methods in the wrong state.
- Use `transaction.atomic()` in the close view. The log save triggers the post_save signal, which saves the vehicle. Both must succeed or both must roll back.
- The predictive maintenance signal imports `trips.Trip` lazily inside the function body to avoid circular imports at module load time. The `sender='trips.Trip'` string form registers the signal without importing the model at the top level.
- `MaintenanceLog.cost` defaults to `0` on creation and is finalised on close. Do not make it required on the create form — the fleet manager may not know the final cost yet.
- `maintenance_due` on `Vehicle` is a cross-app field. Coordinate its addition with Dev A before writing the signal. If Dev A's migration hasn't landed yet, stub the signal with a `hasattr(vehicle, 'maintenance_due')` guard.
